import os,socket,struct,time,tempfile,subprocess,pathlib,signal,select,json,html,sys,xml.etree.ElementTree as ET
BIN=sys.argv[1] if len(sys.argv)>1 else os.environ.get('PHP_FPM_BIN', './sapi/fpm/php-fpm')
if not pathlib.Path(BIN).is_file():
    sys.exit('Usage: python3 test-fpm-rc6-runtime.py /path/to/patched/php-fpm')

def rec(typ,content=b'',request_id=1):
    assert len(content)<=65535
    padding=(8-len(content)%8)%8
    return struct.pack('!BBHHBB',1,typ,request_id,len(content),padding,0)+content+b'\0'*padding

def netlen(n):return bytes([n]) if n<128 else struct.pack('!I',n|0x80000000)
def arg(n,v):
    n=n.encode();v=v.encode();return netlen(len(n))+netlen(len(v))+n+v

def fcgi_req(sock_path,uri,query='',req_method='GET'):
    vars={
        'GATEWAY_INTERFACE':'CGI/1.1','SERVER_SOFTWARE':'unit','SERVER_NAME':'localhost','SERVER_PROTOCOL':'HTTP/1.1',
        'SERVER_PORT':'80','REMOTE_ADDR':'127.0.0.1','REQUEST_METHOD':req_method,
        'DOCUMENT_ROOT':'/tmp','SCRIPT_FILENAME':'/tmp/nonexistent.php','SCRIPT_NAME':'/status',
        'QUERY_STRING':query,'REQUEST_URI':uri,'CONTENT_LENGTH':'0','CONTENT_TYPE':'',
    }
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(10);s.connect(sock_path)
        payload=rec(1,struct.pack('!HB5s',1,0,b'\0'*5))
        params=b''.join(arg(k,v) for k,v in vars.items())
        payload+=rec(4,params)+rec(4)+rec(5)
        s.sendall(payload)
        out=bytearray();err=bytearray();done=False
        while not done:
            h=b''
            while len(h)<8:
                c=s.recv(8-len(h))
                if not c: raise RuntimeError('closed early')
                h+=c
            ver,typ,rid,l,pad,_=struct.unpack('!BBHHBB',h)
            content=b''
            while len(content)<l+pad:
                c=s.recv(l+pad-len(content))
                if not c:raise RuntimeError('short read')
                content+=c
            content=content[:l]
            if typ==6:out+=content
            if typ==7:err+=content
            if typ==3:done=True
        return out.decode('utf8','replace'),err.decode('utf8','replace')

with tempfile.TemporaryDirectory(prefix='php54_rc6_fpm_') as d:
    os.chmod(d,0o777)
    sock_path=d+'/fpm.sock'
    config=pathlib.Path(d)/'php-fpm.conf'
    config.write_text(f'''[global]
pid = {d}/fpm.pid
error_log = {d}/fpm.log
log_level = notice
daemonize = no
[www]
listen = {sock_path}
listen.mode = 0666
pm = static
pm.max_children = 2
pm.status_path = /status
catch_workers_output = yes
''')
    os.chmod(config,0o644)
    def child_setup():
        # Run service as an unprivileged account in isolated directory.
        if os.geteuid()==0:
            os.setgroups([]);os.setgid(65534);os.setuid(65534)
    proc=subprocess.Popen([BIN,'-F','-y',str(config)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,preexec_fn=child_setup)
    try:
        for i in range(50):
            if os.path.exists(sock_path):break
            if proc.poll() is not None:break
            time.sleep(.05)
        if not os.path.exists(sock_path):
            print('FPM failed to start');print(proc.stdout.read().decode()[:3000]);print((pathlib.Path(d)/'fpm.log').read_text(errors='replace') if os.path.exists(d+'/fpm.log') else 'no log');sys.exit(2)
        n=0
        for query in ['', 'html', 'xml','json','full&html','full&xml','full&json']:
            out,err=fcgi_req(sock_path,'/status',query)
            parts=out.split('\r\n\r\n',1)
            if len(parts)!=2:raise AssertionError(('missing FastCGI headers',out[:200]))
            body=parts[1]
            if err:raise AssertionError(('FastCGI STDERR',err))
            if 'json' in query:
                parsed=json.loads(body)
                assert 'pool' in parsed and 'accepted conn' in parsed
                if 'full' in query:assert 'processes' in parsed
            if 'xml' in query:
                parsed=ET.fromstring(body)
                assert parsed.tag=='status'
                if 'full' in query:assert parsed.find('processes') is not None
            if 'html' in query:
                assert '<html' in body and '<table' in body
            if not any(tag in query for tag in ['html','xml','json']):
                assert 'pool:' in body
            n+=1
        attacks=[
             ('full&json&payload=<img src=x onerror="alert(1)">&x=\\\n', 'json'),
             ('full&xml&payload=<script>alert("attack")</script>&x=\\\n','xml'),
             ('full&html&payload=<script>alert("attack")</script>&x=\\\n','html'),
        ]
        for query,fmt in attacks:
            out,err=fcgi_req(sock_path,'/status',query)
            body=out.split('\r\n\r\n',1)[1]
            if err:raise AssertionError(err)
            if fmt=='json':
                obj=json.loads(body)
                assert 'processes' in obj
                # Some worker fields reflect active status request metadata.
                fields=[item.get('request uri','') for item in obj.get('processes',[])]
                assert all(isinstance(x,str) for x in fields)
                assert '\\"' in body, 'Raw quote not escaped in JSON response'
            elif fmt=='xml':
                doc=ET.fromstring(body)
                assert doc.find('processes') is not None
                assert '<script>alert(' not in body, 'Unescaped attacker script content in XML'
                assert '&lt;script&gt;' in body, 'Attack string was not XML-encoded'
            else:
                assert '<script>' not in body, 'Unescaped script tag in HTML'
                assert '&lt;script&gt;' in body, 'Injected script was not encoded as HTML text'
            n+=1
        print('PASS:',n,'real FastCGI requests, including HTML/XML/JSON parsability and markup injection checks')
    finally:
        proc.terminate()
        try:stdout,_=proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:proc.kill();stdout,_=proc.communicate()
        if proc.returncode not in (0, -15): print('FPM abnormal exit', proc.returncode, stdout.decode(errors='replace')[:800])

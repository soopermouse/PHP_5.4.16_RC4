#!/usr/bin/env python3
"""Unprivileged offline FastCGI regression: FPM application + injected metadata escaping.
No public listener, no external services, no vulnerable baseline execution.
"""
import base64, json, os, pathlib, socket, struct, sys, tempfile, subprocess, time, html, xml.etree.ElementTree as ET
BIN=sys.argv[1] if len(sys.argv)>1 else ''
if not BIN or not pathlib.Path(BIN).is_file(): raise SystemExit('Usage: python3 test-fpm-status-fields.py /path/to/php-fpm')

def rec(typ,content=b'',rid=1):
    if len(content)>65535: raise ValueError('FastCGI record too long')
    padding=(-len(content))%8
    return struct.pack('!BBHHBB',1,typ,rid,len(content),padding,0)+content+b'\0'*padding

def size(n):return bytes([n]) if n<128 else struct.pack('!I',n|0x80000000)
def arg(k,v):
    k=k.encode();v=v.encode();return size(len(k))+size(len(v))+k+v

def fcgi(sock_path,uri,query='',method='GET',auth_user='',script_filename='/tmp/nonexistent.php',script_name='/status'):
    attrs={
        'GATEWAY_INTERFACE':'CGI/1.1','SERVER_SOFTWARE':'local-ci', 'SERVER_NAME':'localhost',
        'SERVER_PROTOCOL':'HTTP/1.1','SERVER_PORT':'80','REMOTE_ADDR':'127.0.0.1',
        'REQUEST_METHOD':method,'DOCUMENT_ROOT':'/tmp','SCRIPT_FILENAME':script_filename,
        'SCRIPT_NAME':script_name,'QUERY_STRING':query,'REQUEST_URI':uri,
        'CONTENT_LENGTH':'0','CONTENT_TYPE':'',
        'HTTP_AUTHORIZATION':'Basic '+base64.b64encode((auth_user+':some-password').encode()).decode(),
    }
    payload=rec(1,struct.pack('!HB5s',1,0,b'\0'*5))+rec(4,b''.join(arg(k,v) for k,v in attrs.items()))+rec(4)+rec(5)
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(15);s.connect(sock_path);s.sendall(payload)
        out=bytearray();err=bytearray()
        while True:
            header=b''
            while len(header)<8:
                b=s.recv(8-len(header))
                if not b:raise RuntimeError('early close')
                header+=b
            version,typ,rid,l,pad,_=struct.unpack('!BBHHBB',header)
            if version!=1 or rid!=1: raise RuntimeError('Invalid FastCGI record')
            body=b''
            while len(body)<l+pad:
                b=s.recv(l+pad-len(body))
                if not b:raise RuntimeError('partial FastCGI record')
                body+=b
            if typ==6:out.extend(body[:l])
            if typ==7:err.extend(body[:l])
            if typ==3:break
        data=out.decode('utf-8','replace')
        if '\r\n\r\n' not in data:raise AssertionError('Missing response headers: '+repr(data[:100]))
        return data.split('\r\n\r\n',1)[1],err.decode('utf-8','replace')

def run():
    with tempfile.TemporaryDirectory(prefix='php54_fpm_fields_') as d:
        os.chmod(d,0o777)
        base=pathlib.Path(d)
        sock=str(base/'fpm.sock')
        config=base/'php-fpm.conf'
        config.write_text('[global]\npid = '+d+'/fpm.pid\nerror_log = '+d+'/fpm.log\ndaemonize = no\n[www]\nlisten = '+sock+'\nlisten.mode = 0666\npm = static\npm.max_children = 3\npm.status_path = /status\ncatch_workers_output = yes\n')
        os.chmod(config,0o644)
        def drop():
            if os.geteuid()==0:os.setgroups([]);os.setgid(65534);os.setuid(65534)
        p=subprocess.Popen([BIN,'-F','-y',str(config)],stderr=subprocess.STDOUT,stdout=subprocess.PIPE,preexec_fn=drop)
        try:
            for _ in range(100):
                if os.path.exists(sock):break
                if p.poll() is not None:break
                time.sleep(.05)
            if not os.path.exists(sock):raise RuntimeError('FPM did not start: '+(base/'fpm.log').read_text(errors='replace') if (base/'fpm.log').exists() else 'FPM no log')
            name='proof-<>&".php'
            app=base/name
            app.write_text('<?php echo "LEGACY_FPM_APP_OK"; ?>')
            os.chmod(app,0o644)
            # Deliberately special request fields: no external HTTP server, no shell commands.
            method='GE<T>&"'
            request_uri='/legacy/<tag>&"'
            query='a=<tag>&b="quoted"'
            user='name<&>"'
            expected_uri='/legacy.php?'+query
            expected_script=str(app)
            checks=0
            for fmt in ('json','xml','html'):
                # Refresh all three workers: status must have at least one past script request to display.
                for _ in range(3):
                    body,err=fcgi(sock,request_uri,query,method,user,expected_script,'/legacy.php')
                    assert 'LEGACY_FPM_APP_OK' in body, ('Application response',body,err)
                    checks+=1
                b,e=fcgi(sock,'/status','full&'+fmt)
                if e: raise AssertionError('FPM STDERR '+e)
                if fmt=='json':
                    rows=json.loads(b)['processes']
                    assert any((x.get('request method')==method and x.get('request uri')==expected_uri and x.get('user')==user and x.get('script')==expected_script) for x in rows), ('JSON fields lost',rows)
                    checks+=4
                    assert '<tag>' in b, 'JSON must preserve content inside string (with quotes escaped)'
                elif fmt=='xml':
                    root=ET.fromstring(b)
                    rows=[(x.findtext('request-method'),x.findtext('request-uri'),x.findtext('user'),x.findtext('script')) for x in root.findall('.//process')]
                    assert (method,expected_uri,user,expected_script) in rows, ('XML fields mismatch',rows)
                    assert '&lt;tag&gt;' in b and '&amp;' in b and '<tag>' not in b, ('unsafe XML markup',b[-500:])
                    checks+=5
                else:
                    assert '<html' in b and '<table' in b
                    assert html.escape(method,quote=True) in b, ('unsafe method',b[-900:])
                    assert html.escape(expected_uri,quote=True) in b, ('unsafe URI',b[-900:])
                    assert html.escape(user,quote=True) in b, ('unsafe user',b[-900:])
                    assert html.escape(expected_script,quote=True) in b, ('unsafe script',b[-900:])
                    assert '<tag>' not in b and 'proof-<>&' not in b
                    checks+=5
                print('PASS full FPM status',fmt,'with method, URI, query, user and script escaping')
            print('PASS:',checks,'FPM application, field-escaping, and status checks')
        finally:
            p.terminate()
            try:p.communicate(timeout=3)
            except subprocess.TimeoutExpired:p.kill();p.communicate()
if __name__=='__main__':run()

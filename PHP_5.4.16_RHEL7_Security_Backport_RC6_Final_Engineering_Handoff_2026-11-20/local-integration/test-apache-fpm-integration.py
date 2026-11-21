#!/usr/bin/env python3
"""HTTP integration smoke test for a patched PHP 5.4 FPM binary behind local Apache 2.4.

Runs only on 127.0.0.1 and in a disposable temporary directory. Tests Apache
mod_proxy_fcgi, NOT mod_php. Does not install or change system services.
"""
import os, pathlib, pwd, socket, subprocess, tempfile, time, urllib.request, urllib.error

APACHE = '/usr/sbin/apache2'
PHP_FPM = os.environ.get('PHP_FPM_BIN', '')
if not (PHP_FPM and pathlib.Path(PHP_FPM).is_file()):
    raise SystemExit('Usage: PHP_FPM_BIN=/absolute/path/php-fpm python3 test-apache-fpm-integration.py')
if not os.path.isfile(APACHE):
    raise SystemExit('SKIP: Apache2 binary not available')

with tempfile.TemporaryDirectory(prefix='php54_http_integration_') as d:
    base = pathlib.Path(d)
    os.chmod(d, 0o777)  # isolated temp dir: unprivileged FPM needs to create Unix socket
    www = base / 'htdocs'
    www.mkdir(mode=0o755)
    app = www / 'application.php'
    app.write_text('<?php header("X-PHP-SAPI: ".PHP_SAPI); echo "PHP54_HTTP_APP_OK\\n", PHP_SAPI, "\\n", PHP_VERSION, "\\n"; echo isset($_POST["name"]) ? $_POST["name"] : "NO_POST"; ?>', encoding='utf-8')
    app.chmod(0o644)
    sock = base / 'fpm.sock'
    fpm_conf = base / 'fpm.conf'
    fpm_conf.write_text(f'''[global]
pid = {base}/fpm.pid
error_log = {base}/fpm.log
daemonize = no
[www]
listen = {sock}
listen.mode = 0666
pm = static
pm.max_children = 2
catch_workers_output = yes
''')
    fpm_conf.chmod(0o644)
    fpm_user = pwd.getpwnam('nobody')

    def drop_fpm():
        if os.geteuid() == 0:
            os.setgroups([])
            os.setgid(fpm_user.pw_gid)
            os.setuid(fpm_user.pw_uid)

    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    apache_conf = base / 'apache.conf'
    modules = '/usr/lib/apache2/modules'
    apache_conf.write_text(f'''ServerRoot "{d}"
ServerName 127.0.0.1
Listen 127.0.0.1:{port}
PidFile "{base}/apache.pid"
ErrorLog "{base}/apache_error.log"
LogLevel warn
LoadModule mpm_event_module "{modules}/mod_mpm_event.so"
LoadModule authz_core_module "{modules}/mod_authz_core.so"
LoadModule proxy_module "{modules}/mod_proxy.so"
LoadModule proxy_fcgi_module "{modules}/mod_proxy_fcgi.so"
LoadModule mime_module "{modules}/mod_mime.so"
TypesConfig /etc/mime.types
LoadModule dir_module "{modules}/mod_dir.so"
User www-data
Group www-data
DocumentRoot "{www}"
DirectoryIndex application.php
<Directory "{www}">
    AllowOverride None
    Options -Indexes +FollowSymLinks
    Require all granted
</Directory>
<FilesMatch "\\.php$">
    SetHandler "proxy:unix:{sock}|fcgi://localhost/"
</FilesMatch>
''')
    check = subprocess.run([APACHE, '-f', str(apache_conf), '-t'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if check.returncode:
        raise AssertionError('Apache config invalid: '+ check.stdout + check.stderr)
    print('PASS Apache configuration syntax:', check.stdout.strip(), check.stderr.strip())
    fpm = subprocess.Popen([PHP_FPM, '-F', '-y', str(fpm_conf)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, preexec_fn=drop_fpm)
    apache = None
    try:
        for _ in range(100):
            if sock.exists():
                break
            if fpm.poll() is not None:
                raise RuntimeError('FPM exited before socket appeared: '+(base / 'fpm.log').read_text(errors='replace') if (base / 'fpm.log').exists() else 'FPM exited without log')
            time.sleep(0.05)
        assert sock.exists(), 'FPM socket missing'
        apache = subprocess.Popen([APACHE, '-f', str(apache_conf), '-DFOREGROUND'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        url = f'http://127.0.0.1:{port}/application.php'
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(80):
            if apache.poll() is not None:
                raise RuntimeError('Apache process terminated early')
            try:
                response = opener.open(url, timeout=2)
                body = response.read().decode()
                break
            except Exception:
                time.sleep(0.05)
        else:
            raise RuntimeError('Could not reach Apache HTTP endpoint')
        assert response.status == 200, response.status
        assert 'PHP54_HTTP_APP_OK\nfpm-fcgi\n5.4.16\nNO_POST' in body, repr(body)
        assert response.headers.get('X-PHP-SAPI') == 'fpm-fcgi', dict(response.headers)
        print('PASS Apache -> FastCGI -> PHP 5.4.16 app HTTP 200')
        post = urllib.request.Request(url, data=b'name=post_works', method='POST', headers={'Content-Type':'application/x-www-form-urlencoded'})
        with opener.open(post, timeout=5) as response:
            body = response.read().decode()
            assert response.status == 200 and 'post_works' in body, body
        print('PASS Apache POST form submission to PHP app')
        with opener.open(url+'?x=%3Ctag%3E', timeout=5) as response:
            assert response.status == 200 and 'PHP54_HTTP_APP_OK' in response.read().decode()
        print('PASS Apache query-string PHP request')
        try:
            opener.open(f'http://127.0.0.1:{port}/missing.php', timeout=5)
        except urllib.error.HTTPError as e:
            assert e.code in (404,403), ('nonexistent PHP script unexpectedly served',e.code)
        else:
            raise AssertionError('Nonexistent PHP script unexpectedly served')
        print('PASS Missing PHP script denied/not served')
        print('PASS 4 HTTP integration cases; this is Apache+FPM, not mod_php, and Debian not RHEL7')
    finally:
        if apache is not None:
            apache.terminate()
            try:
                apache.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                apache.kill(); apache.communicate()
        fpm.terminate()
        try:
            fpm.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            fpm.kill(); fpm.communicate()
        for log in ('apache_error.log','fpm.log'):
            p = base / log
            if p.exists() and p.stat().st_size:
                print('LOG '+log+': '+p.read_text(errors='replace')[-1000:])

#!/usr/bin/env python3
"""Actual, isolated Apache 2.4 + candidate libphp5.so runtime integration test.

REQUIRES: authorized RHEL 7 staging VM, candidate php RPM installed, Python 3.
Starts a loopback-only disposable Apache instance. Does NOT change system Apache
configuration, install packages, or connect to external hosts.

Exit 0 = scripted checks passed ON THIS HOST, not a production approval.
"""
import argparse
import http.cookiejar
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


def execute(cmd, timeout=15):
    return subprocess.run(cmd, universal_newlines=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=timeout, check=False)


def die(msg):
    raise SystemExit('NO-GO: ' + msg)


def require_rhel7():
    release = Path('/etc/redhat-release')
    if not release.exists() or not re.search(r'\brelease\s+7\.', release.read_text()):
        die('Only a verified RHEL7-family staging host is supported')
    if os.geteuid() == 0:
        die('Do not run this test as root')


def get_module_path(arg):
    if arg:
        module = Path(arg).resolve(strict=True)
    else:
        matches = [Path(p) for p in ('/usr/lib64/httpd/modules/libphp5.so',
                   '/etc/httpd/modules/libphp5.so', '/usr/lib/httpd/modules/libphp5.so') if Path(p).is_file()]
        if not matches:
            die('Candidate libphp5.so missing. Install reviewed RPM on isolated staging first.')
        module = matches[0].resolve()
    if module.name != 'libphp5.so':
        die('Expected the actual libphp5.so candidate module')
    rpm = execute(['rpm', '-qf', '--qf', '%{NAME} %{VERSION} %{RELEASE} %{ARCH}\n', str(module)])
    if rpm.returncode != 0 or not re.search(r'\b5\.4\.16\s+48[^\s]*securityrc6', rpm.stdout):
        die('Module not owned by a verified installed RC6 RPM: ' + rpm.stdout.strip())
    print('PASS installed RPM owner:', rpm.stdout.strip())
    return module


def module_lines(httpd, module_dir, name):
    static = execute([httpd, '-l'])
    if static.returncode == 0 and re.search(r'\bmod_' + re.escape(name) + r'\.c\b', static.stdout):
        return ''
    path = module_dir / ('mod_' + name + '.so')
    if not path.is_file():
        die('Apache module missing: ' + str(path))
    return 'LoadModule ' + name + '_module "' + str(path) + '"\n'


def parse(text):
    lines = {}
    for line in text.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            lines[k] = v
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', help='path to installed candidate libphp5.so')
    parser.add_argument('--httpd', default='/usr/sbin/httpd', help='Apache 2.4 binary')
    args = parser.parse_args()
    require_rhel7()
    httpd = Path(args.httpd)
    if not httpd.is_file():
        die('Apache httpd binary absent')
    module = get_module_path(args.module)
    module_dir = module.parent
    for mod in ('mpm_prefork', 'authz_core', 'authz_host', 'unixd'):
        if mod == 'mpm_prefork' and execute([str(httpd), '-l']).stdout.find('prefork.c') >= 0:
            continue
        module_lines(str(httpd), module_dir, mod)  # preflight
    with tempfile.TemporaryDirectory(prefix='php54_rc6_modphp_') as root:
        tmp = Path(root)
        www = tmp / 'www'; www.mkdir()
        session = tmp / 'sessions'; session.mkdir(mode=0o700)
        (www / 'probe.php').write_text(r'''<?php
header('Content-Type: text/plain; charset=UTF-8');
header('Cache-Control: no-store');
header('X-PHP-SAPI: '.php_sapi_name());
if (!isset($_SERVER['REMOTE_ADDR']) || !in_array($_SERVER['REMOTE_ADDR'], array('127.0.0.1', '::1'), true)) {
    header('HTTP/1.1 403 Forbidden'); exit;
}
session_save_path(__DIR__ . '/../sessions');
if (!session_start()) { header('HTTP/1.1 500 Internal Server Error'); echo "session_error=1\n"; exit; }
$_SESSION['hits'] = isset($_SESSION['hits']) ? $_SESSION['hits'] + 1 : 1;
echo 'sapi=', php_sapi_name(), "\n";
echo 'version=', PHP_VERSION, "\n";
echo 'method=', $_SERVER['REQUEST_METHOD'], "\n";
echo 'hits=', $_SESSION['hits'], "\n";
echo 'post=', isset($_POST['sample']) ? $_POST['sample'] : '', "\n";
echo 'upload=', isset($_FILES['samplefile']) ? $_FILES['samplefile']['error'] : 'absent', "\n";
echo 'uploaded=', isset($_FILES['samplefile']) && is_uploaded_file($_FILES['samplefile']['tmp_name']) ? 'yes' : 'no', "\n";
echo 'memory_limit=', ini_get('memory_limit'), "\n";
echo 'upload_progress=', ini_get('session.upload_progress.enabled'), "\n";
echo 'multipart_parts=', ini_get('max_multipart_body_parts'), "\n";
?>''', encoding='utf-8')
        (www / 'probe.php').chmod(0o600)
        (www / 'limit.php').write_text(r'''<?php
header('Content-Type: text/plain; charset=UTF-8');
header('Cache-Control: no-store');
echo 'parts_limit=', ini_get('max_multipart_body_parts'), "\n";
echo 'count=', count($_POST), "\n";
echo 'first=', isset($_POST['first']) ? $_POST['first'] : 'missing', "\n";
echo 'second=', isset($_POST['second']) ? $_POST['second'] : 'missing', "\n";
echo 'third=', isset($_POST['third']) ? $_POST['third'] : 'missing', "\n";
?>''' , encoding='utf-8')
        (www / 'limit.php').chmod(0o600)
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        conf = tmp / 'apache.conf'
        modules = ''.join(module_lines(str(httpd), module_dir, name) for name in
                          ('mpm_prefork', 'authz_core', 'authz_host', 'unixd'))
        conf.write_text('''ServerRoot "/etc/httpd"
ServerName localhost
DefaultRuntimeDir "{runtime}"
Listen 127.0.0.1:{port}
PidFile "{pid}"
ErrorLog "{log}"
LogLevel warn
{modules}LoadModule php5_module "{libphp}"
DocumentRoot "{www}"
<Directory "{www}">
  AllowOverride None
  Options -Indexes -FollowSymLinks
  Require local
  # Candidate Patch202: cap multipart parts using the module's per-dir INI.
  php_admin_value max_multipart_body_parts 2
</Directory>
<FilesMatch "\\.php$">
  SetHandler application/x-httpd-php
</FilesMatch>
'''.format(port=port, pid=tmp / 'httpd.pid', log=tmp / 'httpd-error.log',
           modules=modules, libphp=module, www=www, runtime=tmp))
        tested = execute([str(httpd), '-f', str(conf), '-t'])
        if tested.returncode:
            die('Isolated Apache config failed: ' + tested.stdout[-2500:])
        print('PASS isolated Apache config syntax')
        apache = subprocess.Popen([str(httpd), '-f', str(conf), '-X'],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            url = 'http://127.0.0.1:{}/probe.php'.format(port)
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            for _ in range(60):
                if apache.poll() is not None:
                    die('Apache failed during startup. Check module ABI and dependencies.')
                try:
                    with opener.open(url, timeout=2) as response:
                        first = parse(response.read().decode('utf-8'))
                    break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.1)
            else:
                die('No Apache HTTP response after startup')
            if first.get('sapi') != 'apache2handler' or first.get('version') != '5.4.16':
                die('Actual Apache HTTP request did not execute patched PHP 5.4.16: ' + str(first))
            print('PASS Apache mod_php executes PHP 5.4.16 via HTTP')
            with opener.open(url, timeout=5) as response:
                second = parse(response.read().decode('utf-8'))
            if first.get('hits') != '1' or second.get('hits') != '2':
                die('Session persistence failure: ' + str((first, second)))
            print('PASS file-backed session cookie and persistence')
            req = urllib.request.Request(url, data=b'sample=form_ok', method='POST',
                         headers={'Content-Type': 'application/x-www-form-urlencoded'})
            with opener.open(req, timeout=5) as response:
                posted = parse(response.read().decode('utf-8'))
            if posted.get('post') != 'form_ok':
                die('POST form failed: ' + str(posted))
            print('PASS URL-encoded POST application form')
            boundary = 'RC6ISOLATEDBOUNDARY'
            payload = ('--' + boundary + '\r\nContent-Disposition: form-data; name="samplefile"; filename="test.txt"\r\n'
                       'Content-Type: text/plain\r\n\r\nvalidation-file\r\n--' + boundary + '--\r\n').encode('ascii')
            req = urllib.request.Request(url, data=payload, method='POST',
                      headers={'Content-Type':'multipart/form-data; boundary=' + boundary})
            with opener.open(req, timeout=5) as response:
                uploaded = parse(response.read().decode('utf-8'))
            if uploaded.get('upload') != '0' or uploaded.get('uploaded') != 'yes':
                die('Multipart file upload failed: ' + str(uploaded))
            print('PASS multipart file upload (independent of disabled upload-progress feature)')
            # A normal mod_php 5.4 module without Patch202 does not register
            # max_multipart_body_parts and cannot enforce this limit.
            multipart = []
            for name in ('first', 'second', 'third'):
                multipart.append('--' + boundary + '\r\n'
                    + 'Content-Disposition: form-data; name="' + name + '"\r\n\r\n'
                    + name + '-value\r\n')
            multipart.append('--' + boundary + '--\r\n')
            limited_req = urllib.request.Request(
                'http://127.0.0.1:{}/limit.php'.format(port),
                data=''.join(multipart).encode('ascii'), method='POST',
                headers={'Content-Type':'multipart/form-data; boundary=' + boundary})
            with opener.open(limited_req, timeout=5) as response:
                limited = parse(response.read().decode('utf-8'))
            if limited.get('parts_limit') != '2':
                die('Candidate Patch202 multipart limit not active in Apache: ' + str(limited))
            if (limited.get('first') != 'first-value' or
                    limited.get('second') != 'second-value' or
                    limited.get('third') != 'missing' or limited.get('count') != '2'):
                die('Multipart limit was not enforced at two parsed fields: ' + str(limited))
            print('PASS patch-specific max_multipart_body_parts=2 enforced (third field rejected)')
            for key in ('memory_limit', 'multipart_parts', 'upload_progress'):
                if key not in uploaded:
                    die('Missing expected directive ' + key)
            print('PASS directive inventory recorded', {k: uploaded[k] for k in
                  ('memory_limit','multipart_parts','upload_progress')})
            try:
                opener.open('http://127.0.0.1:{}/missing.php'.format(port), timeout=5)
            except urllib.error.HTTPError as err:
                if err.code != 404:
                    die('Unexpected missing-script status {}'.format(err.code))
            else:
                die('Missing PHP script was served unexpectedly')
            print('PASS missing application returns HTTP 404')
            print('PASS isolated Apache mod_php integration checks (staging host only)')
        finally:
            apache.terminate()
            try:
                apache.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                apache.kill(); apache.communicate()
            logfile = tmp / 'httpd-error.log'
            if logfile.exists():
                print('Apache diagnostic tail:', logfile.read_text(errors='replace')[-1200:])


if __name__ == '__main__':
    main()

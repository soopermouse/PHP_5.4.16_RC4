#!/usr/bin/env python3
"""RC6 source assertion gate — checks extracted, fully patched PHP 5.4.16 tree."""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    sys.exit("Usage: python3 verify-source-rc6.py /path/to/rpmbuild/BUILD/php-5.4.16")
root = Path(sys.argv[1])
checks = {
  'sapi/cgi/cgi_main.c': ('pilen > slen', 'if (path_info && orig_path_info != path_info)'),
  'ext/soap/php_encoding.c': ('return i > 0 ? i : 1;',),
  'sapi/fpm/fpm/fpm_status.c': ('fpm_rc6_status_escape', 'FPM_RC6_JSON', 'FPM_RC6_XML', 'FPM_RC6_HTML',
    'request_method = fpm_rc6_status_escape(', 'request_uri = fpm_rc6_status_escape(',
    'auth_user = fpm_rc6_status_escape(', 'script_filename = fpm_rc6_status_escape('),
  'ext/session/session.c': ('if (!PS(rfc1867_enabled) || 1)',),
}
for rel, markers in checks.items():
    f = root / rel
    if not f.is_file(): sys.exit('FAIL missing source: ' + str(f))
    content = f.read_text(errors='replace')
    for marker in markers:
        if marker not in content: sys.exit('FAIL %s missing %r' % (rel, marker))
    print('PASS %s (%d markers)' % (rel, len(markers)))
print('PASS: source assertions; runtime and RHEL7 evidence still required')

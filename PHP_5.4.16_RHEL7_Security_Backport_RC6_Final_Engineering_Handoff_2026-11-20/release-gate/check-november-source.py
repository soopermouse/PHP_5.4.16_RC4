#!/usr/bin/env python3
"""Read-only source-code assertions. Not a compiled security/penetration test."""
from pathlib import Path
import sys
root = Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
expect = {
    'ext/session/mod_files.c': ['if (ftruncate(data->fd, 0) == -1)', 'data->st_size = 0'],
    'ext/phar/util.c': ['if (sig_type != PHAR_SIG_OPENSSL)', 'VCWD_STAT(pfile, &pubkey_stat)'],
    'ext/standard/http_fopen_wrapper.c': ['!strcasecmp(resource->scheme, "https")'],
    'ext/standard/ftp_fopen_wrapper.c': ['!strcasecmp(resource->scheme, "ftps")', 'FTPS server refused TLS authentication; refusing plaintext fallback'],
    'main/main.c': ['PG(modules_activated) && EG(active)', 'PG(modules_activated) && EG(active) TSRMLS_CC'],
    'ext/session/session.c': ['if (!PS(rfc1867_enabled) || 1)'],
    'ext/soap/php_encoding.c': ['return i > 0 ? i : 1;'],
    'ext/soap/php_xml.c': ['trav->type == XML_DTD_NODE'],
}
for rel, snippets in expect.items():
    try: contents = (root / rel).read_text()
    except OSError as exc: raise SystemExit('FAIL: '+rel+': '+str(exc))
    for phrase in snippets:
        if phrase not in contents: raise SystemExit('FAIL: '+rel+' missing '+phrase)
    print('PASS:', rel)
print('NOTE: source assertions do not replace RPM builds or runtime regression tests')

# RC3 regression check: patch application alone did not catch malformed C string
# literal in RC2. These checks also help prevent the bug returning.
phar = (root / 'ext/phar/util.c').read_text()
if 'spprintf(error, 0, "phar \'%s\' requires an OpenSSL signature because a .pubkey exists", fname);' not in phar:
    raise SystemExit('FAIL: corrected PHAR diagnostic C string missing')
if 'spprintf(error, 0, "phar "%s"' in phar:
    raise SystemExit('FAIL: invalid PHAR diagnostic C string in source')
print('PASS: PHAR diagnostic C-string regression')

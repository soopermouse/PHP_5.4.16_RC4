#!/usr/bin/env python3
"""Targeted source-backed FPM status escaping unit checks, no network or service.

Compiles the exact FPM JSON escaping function extracted from the patched C source.
The HTML/XML encoder call is verified against mocked signatures/flags; use the
real FPM integration gate for complete runtime coverage. This test does NOT
represent a FastCGI request or a RHEL7 build.
"""
from pathlib import Path
import subprocess, tempfile, shutil, sys, json
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]/'patched-source-files'
p = root/'sapi/fpm/fpm/fpm_status.c'
if not p.exists(): sys.exit('FPM C source not found: ' + str(p))
src=p.read_text()
head='static char *fpm_rc6_status_escape('
assert src.count(head)==1
begin=src.index(head)
end=src.index('\n\nint fpm_status_init_child(', begin)
helper=src[begin:end]
expected_markers=[
 'format = FPM_RC6_JSON;', 'format = FPM_RC6_HTML;', 'format = FPM_RC6_XML;',
 'fpm_rc6_status_escape(scoreboard.pool, format',
 'request_method = fpm_rc6_status_escape(', 'request_uri = fpm_rc6_status_escape(',
 'query_string = proc.query_string[0]', 'auth_user = fpm_rc6_status_escape(',
 'script_filename = fpm_rc6_status_escape(',
 'efree(request_method);', 'efree(request_uri);', 'efree(auth_user);', 'efree(script_filename);',
]
for marker in expected_markers:
    if marker not in src: sys.exit('FAIL field or lifetime assertion: ' + marker)
if shutil.which('gcc') is None:
    sys.exit('gcc is needed for source-backed test')
header=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#define TSRMLS_DC
#define TSRMLS_CC
#define ENT_QUOTES 3
#define ENT_SUBSTITUTE 8
#define ENT_DISALLOWED 128
#define ENT_XML1 16
#define ENT_HTML401 0
#define FPM_RC6_TEXT 0
#define FPM_RC6_HTML 1
#define FPM_RC6_XML 2
#define FPM_RC6_JSON 3
static int entity_calls = 0, xml_calls = 0, html_calls = 0;
static void *safe_emalloc(size_t count, size_t bytes, size_t overhead) {
  if (bytes && count > (SIZE_MAX - overhead) / bytes) abort();
  void *p=malloc(count*bytes+overhead);
  if (!p) abort();
  return p;
}
#define estrdup strdup
static char *php_escape_html_entities_ex(unsigned char *old, size_t oldlen, size_t *newlen,
    int all, int flags, char *charset, int double_encode) {
  if (all != 0 || !charset || strcmp(charset,"UTF-8") != 0 || !double_encode) abort();
  if ((flags & (ENT_QUOTES | ENT_SUBSTITUTE | ENT_DISALLOWED)) !=
        (ENT_QUOTES | ENT_SUBSTITUTE | ENT_DISALLOWED)) abort();
  entity_calls++;
  if (flags & ENT_XML1) xml_calls++; else html_calls++;
  char *p=malloc(oldlen+1); if (!p) abort();
  memcpy(p,old,oldlen); p[oldlen]=0; *newlen=oldlen;
  return p; /* Mock only verifies API and flags, not real HTML entity encoding. */
}
'''
main=r'''
static void check(const char *raw, int fmt, const char *expected) {
  char *actual=fpm_rc6_status_escape(raw,fmt);
  if (strcmp(actual,expected)!=0) {
    fprintf(stderr,"FAIL fmt %d expected [%s], got [%s]\n",fmt,expected,actual);
    exit(1);
  }
  free(actual);
}
int main(void) {
  check("normal",FPM_RC6_JSON,"normal");
  check("a\\\"b\n\t",FPM_RC6_JSON,"a\\\\\\\"b\\u000a\\u0009");
  check("\x01\x1f",FPM_RC6_JSON,"\\u0001\\u001f");
  check("caf\xc3\xa9",FPM_RC6_JSON,"caf\xc3\xa9");
  check("\x80",FPM_RC6_JSON,"\\uFFFD");
  check("\xc0\xaf",FPM_RC6_JSON,"\\uFFFD\\uFFFD");
  check("\xed\xa0\x80",FPM_RC6_JSON,"\\uFFFD\\uFFFD\\uFFFD");
  check("\xf4\x90\x80\x80",FPM_RC6_JSON,"\\uFFFD\\uFFFD\\uFFFD\\uFFFD");
  check("\xe2\x82",FPM_RC6_JSON,"\\uFFFD\\uFFFD");
  check("<foo>",FPM_RC6_TEXT,"<foo>");
  check("<foo>",FPM_RC6_HTML,"<foo>");
  check("<foo>",FPM_RC6_XML,"<foo>");
  if (entity_calls!=2 || html_calls!=1 || xml_calls!=1) abort();
  puts("PASS: JSON/UTF-8 escape unit cases (9), text (1), HTML/XML API/flag mocks (2)");
  return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='php54_fpm_rc6_') as d:
    d=Path(d); s=d/'unit.c'; binary=d/'unit'
    s.write_text(header+helper+'\n'+main)
    r=subprocess.run(['gcc','-std=c99','-D_GNU_SOURCE','-Wall','-Wextra','-Werror','-O1','-o',str(binary),str(s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    if r.returncode: sys.exit('FAIL compilation:\n'+r.stderr)
    r=subprocess.run([str(binary)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    if r.returncode: sys.exit('FAIL runtime:\n'+r.stdout+'\n'+r.stderr)
    print(r.stdout.strip())
print('PASS: output fields and buffer frees in patched source')
print('NOTE: HTML/XML output requires actual php-fpm integration validation; the test mocks their encoder API')

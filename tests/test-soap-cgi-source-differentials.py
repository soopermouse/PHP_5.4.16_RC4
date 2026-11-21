#!/usr/bin/env python3
"""RC6 Patch210/211/214 differential source-and-runtime harness.

Reconstructs pre-patch behavior by *reversing only* three RC6 patches in
scratch copies of the packaged patched sources. Compiles the exact affected
functions with AddressSanitizer and exercises bounded synthetic cases.
This is source-extracted evidence, NOT a full PHP runtime memory-safety proof.

Usage: python3 tests/test-soap-cgi-source-differentials.py \
   /path/to/php-5.4.16-48.el7-securityrc6-source [--evidence /some/dir]
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

TARGETS = [
    ('ext/soap/php_encoding.c', '11-soap-malformed-array-dimension.patch'),
    ('ext/soap/php_xml.c', '12-soap-dtd-lifetime.patch'),
    ('sapi/cgi/cgi_main.c', '15-cgi-path-info-underflow.patch'),
]


def run(argv, **kw):
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, **kw)


def extract_function(text, pattern):
    match = re.search(pattern, text)
    if not match:
        raise ValueError('Cannot find function ' + pattern)
    at = text.index('{', match.start())
    level = 0
    for i in range(at, len(text)):
        if text[i] == '{':
            level += 1
        elif text[i] == '}':
            level -= 1
            if level == 0:
                return text[match.start():i + 1]
    raise ValueError('Unterminated function ' + pattern)


def make_harness(source_root, dest, state):
    src = (source_root / 'ext/soap/php_encoding.c').read_text(errors='replace')
    fn = extract_function(src, r'static int calc_dimension_12\([^)]*\)')
    array_c = ('#include <stdio.h>\n#include <stdlib.h>\n#define E_ERROR 1\n'
               '#define soap_error0(a,b) abort()\n' + fn +
               '\nint main(void) {\n'
               ' const char *a[]={""," ","not_a_dimension","2","2,3","*"};\n'
               ' for (int i=0;i<6;i++) printf("%d\\n",calc_dimension_12(a[i]));\n'
               ' return 0;\n}\n')
    (dest / ('array_' + state + '.c')).write_text(array_c)

    src = (source_root / 'ext/soap/php_xml.c').read_text(errors='replace')
    fn1 = extract_function(src, r'static int is_blank\([^)]*\)')
    fn2 = extract_function(src, r'static void cleanup_xml_node\([^)]*\)')
    dtd_c = ('#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n'
             '#include <libxml/parser.h>\n#include <libxml/tree.h>\n' + fn1 + '\n' + fn2 +
             '''
int main(void) {
 const char *xml="<!DOCTYPE root [<!ENTITY harmless 'hello'>]><root>&harmless;</root>";
 xmlDocPtr doc=xmlReadMemory(xml,(int)strlen(xml),"case.xml",NULL,XML_PARSE_NONET|XML_PARSE_NOENT);
 if (!doc) return 10;
 if (!xmlGetIntSubset(doc)) return 11;
 cleanup_xml_node((xmlNodePtr)doc);
 if (!xmlGetIntSubset(doc)) { xmlFreeDoc(doc); return 12; }
 xmlFreeDoc(doc);
 xmlCleanupParser();
 puts("DTD attached until document cleanup");
 return 0;
}
''')
    (dest / ('dtd_' + state + '.c')).write_text(dtd_c)

    src = (source_root / 'sapi/cgi/cgi_main.c').read_text(errors='replace')
    matched = re.search(r'char \*path_info = [^;]*;', src)
    if not matched:
        raise ValueError('No CGI PATH_INFO implementation found')
    statement = matched.group(0)
    # Form pointer only; never dereference a synthetic out-of-bounds address.
    cgi_c = ('#include <stdio.h>\n#include <stddef.h>\n#include <stdint.h>\n'
             'static void check(int pilen, int slen){\n'
             ' char env_path_info[]="abcd";\n'
             ' char *orig_path_info=NULL;\n'
             ' (void)orig_path_info;\n' + statement + '\n'
             ' if(!path_info) puts("null");\n'
             ' else printf("%ld\\n",(long)((intptr_t)path_info-(intptr_t)env_path_info));\n'
             '}\nint main(void){check(1,3);check(3,3);check(4,2);return 0;}\n')
    (dest / ('cgi_' + state + '.c')).write_text(cgi_c)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', help='extracted, fully patched RC6 source tree')
    parser.add_argument('--evidence', help='keep sanitized harness output and source copies')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    kit = root / 'rpm-kit'
    source = Path(args.source).resolve()
    if not (source / 'ext/soap/php_encoding.c').exists():
        parser.error('Not an extracted PHP 5.4 patched source tree: ' + str(source))
    if args.evidence:
        tmp = Path(args.evidence).resolve()
        tmp.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        tmp = Path(tempfile.mkdtemp(prefix='php54_diff_'))
        cleanup = True
    result = {'test': 'source-extracted bounded differential; not full PHP memory-safety proof',
              'compiler': None, 'cases': {}, 'source_code_changed': False}
    try:
        baseline = tmp / 'baseline'
        for rel, patch in TARGETS:
            dest = baseline / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(source / rel), str(dest))
            command = ['patch', '-R', '--fuzz=0', '-p1', '-d', str(baseline), '-i', str(kit / patch), '--batch']
            r = run(command, timeout=15)
            if r.returncode:
                raise RuntimeError('Cannot reconstruct baseline (' + patch + '): ' + r.stdout + r.stderr)
        patched = tmp / 'patched'
        for rel, _ in TARGETS:
            dest = patched / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(source / rel), str(dest))
        for state, src in [('baseline', baseline), ('patched', patched)]:
            make_harness(src, tmp, state)
        cc = os.environ.get('CC', 'cc')
        result['compiler'] = run([cc, '--version'], timeout=5).stdout.splitlines()[0]
        xml_cflags = run(['xml2-config', '--cflags'], timeout=5)
        xml_libs = run(['xml2-config', '--libs'], timeout=5)
        if xml_cflags.returncode or xml_libs.returncode:
            raise RuntimeError('libxml2 development headers and xml2-config required')
        for state in ('baseline', 'patched'):
            for subject in ('array', 'dtd', 'cgi'):
                obj = tmp / (subject + '_' + state)
                cmd = [cc, '-std=gnu99', '-O1', '-g', '-fsanitize=address', '-fno-omit-frame-pointer']
                if subject == 'dtd':
                    cmd += xml_cflags.stdout.strip().split()
                cmd += [str(obj) + '.c', '-o', str(obj)]
                if subject == 'dtd':
                    cmd += xml_libs.stdout.strip().split()
                r = run(cmd, timeout=40)
                if r.returncode:
                    raise RuntimeError('ASan compile failed (' + subject + '/' + state + '): ' + r.stderr)
                r = run([str(obj)], timeout=10, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1'))
                result['cases'][subject + '/' + state] = {'exit': r.returncode,
                     'stdout': r.stdout.strip(), 'stderr': r.stderr[-1500:]}
        cases = result['cases']
        assert cases['array/baseline']['stdout'].splitlines() == ['0','0','0','1','2','1']
        assert cases['array/patched']['stdout'].splitlines() == ['1','1','1','1','2','1']
        assert cases['dtd/baseline']['exit'] == 12, cases['dtd/baseline']
        assert cases['dtd/patched']['exit'] == 0, cases['dtd/patched']
        assert cases['cgi/baseline']['stdout'].splitlines() == ['-2','0','2']
        assert cases['cgi/patched']['stdout'].splitlines() == ['null','null','2']
        assert all(cases[name]['exit'] == 0 for name in ('array/baseline','array/patched','cgi/baseline','cgi/patched'))
        result['status'] = 'PASS: extracted-code before/after structural demonstrations'
        for subject in ('array','dtd','cgi'):
            print('PASS ' + subject + ': baseline=' +
                  repr(cases[subject + '/baseline']['stdout']) + ' exit=' +
                  str(cases[subject + '/baseline']['exit']) + '; patched=' +
                  repr(cases[subject + '/patched']['stdout']) + ' exit=' +
                  str(cases[subject + '/patched']['exit']))
        print('LIMITATION: sanitized source-extracted harnesses are not full PHP/SOAP/CGI runtime memory-safety proof')
        return 0
    except (Exception, AssertionError) as err:
        result['status'] = 'FAIL: ' + str(err)
        print('FAIL: ' + str(err), file=sys.stderr)
        return 1
    finally:
        (tmp / 'differential-results.json').write_text(json.dumps(result, indent=2) + '\n')
        if cleanup:
            shutil.rmtree(str(tmp), ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())

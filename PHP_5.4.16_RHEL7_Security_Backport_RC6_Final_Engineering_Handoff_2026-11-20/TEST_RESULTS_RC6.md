## Final 20 November local evidence (this handoff)

- **Patch210:** source-extracted C harness, before=0 dimensions for malformed empty/invalid values, after=1; AddressSanitizer instrumented.
- **Patch211:** source-extracted libxml2 C harness, before=Dtd detached during node cleanup (harness exit 12), after=DTD retained until document cleanup (exit 0); AddressSanitizer instrumented; not full SOAP memory-safety certification.
- **Patch214:** source-extracted C harness, before=pointer formed 2 bytes before buffer for short input, after=NULL; AddressSanitizer instrumented; no out-of-bounds pointer dereference performed.
- **Patched PHP CGI:** valid/short/empty `PATH_INFO` test cases passed on a previously built Debian PHP 5.4.16 RC6 CGI executable.
- **Compatibility assessment gate:** pending review fails closed; incorrect test count or manifest hash fails closed; a complete synthetic review passes schema validation (NOT real approval).
- **Patch sources:** all 17 included changed source files byte-for-byte matched the full patched RC6 source tree.
- **Constraints:** No RHEL7, RPM, target Apache, signing, full PHP memory-sanitizer run or independent production approval was performed in this handoff.

# RC6 test evidence — 19–20 November 2026

## External full-suite evidence received 20 November 2026

External full-suite retest on 20 November 2026: 12,315 tests, 13 patch-only behavioral divergences (five memory-limit cases including `ext/standard/tests/streams/bug61115-1.phpt`, eight disabled RFC1867 upload-progress cases). The earlier 12 count was correct only for the 4,186-test selection. This full-suite result is user-supplied and has not been independently rerun in this packaging session.

- Both baseline and candidate compiled successfully in **debug**, **optimized/non-debug** and **thread-safe (ZTS)** configurations, without new candidate compiler warnings.
- Fresh kit source RPM and Patch200–215 applied with zero fuzz; full source archive and 17 modified source files matched.
- Encrypted FTPS **upload and download** worked in both builds; FTPS directory listing failed in both baseline and candidate.
- php-cgi in FastCGI mode returned the same output as in CGI mode for the tested cases.
- Apache `mod_php` handled **33,000** requests without failures in both builds; this is not proof of RHEL7 or RPM testing.
- Patch210, Patch211 and Patch214 still lack before/after security-behavior proof and memory-checker evidence.
- No RHEL7 RPM toolchain, RPM signatures, or RHEL7 Apache mod_php tests were performed.

**Provenance:** These are user-reported external test results. The named `RC6_TEST_REPORT.md` and `PHP54_RC6_TEST_RESULTS_2026-11-19.zip` were not accessible in this session; this document is not presented as an independent reproduction.


## Additional local tooling validation, 20 November 2026 (no PHP source change)

- `python3 tests/test-release-tooling.py`: **PASS**; checks four code fixes, Py3.6 grammar, unsupported subprocess arguments, upload-progress values (`0`, `Off`, `1`, `On`, etc.), and invalid-value rejection.
- `python3 tests/test-fpm-rc6-source.py patched-source-files`: **PASS** (9 JSON/UTF-8, 1 text and 2 HTML/XML API mocks, source buffer/free checks).
- `bash -n` (runner, staging checks): **PASS**.
- Apache 2.4 `-t` of equivalent isolated config with `mod_authz_host`, `Require local`, `php_admin_value max_multipart_body_parts 2`: **PASS** locally with PHP 8.4, **not** PHP 5.4 / RHEL7 validation.
- External tester reports all eight RC6 `mod_php` checks passed on **Ubuntu 24.04** with Apache 2.4.68 compiled from source, with Python 3.6.8 also tested there. **No run took place on RHEL7**; native target testing remains open.
- **NOT RUN HERE:** native RHEL7 full RPM toolchain, Python 3.6.8 interpreter (externally tested on Ubuntu 24.04), Apache RC6 mod_php on RHEL7, signed RPM verification, independent SOAP before/after/ASan evidence and FTPS encrypted transfer on RHEL7. Thirteen patch-only differences in the complete external suite still require acceptance or redesign.


## RC6 release-gate correction v2 (20 November 2026)

- **PASS (local):** `sha256sum -c SHA256SUMS` at archive root and in `rpm-kit/`, including all 16 original security patch files.
- **PASS (local):** `tests/test-release-tooling.py` runs the same two checksum gates as the RHEL7 runner; accepts empty upload-progress value if and only if the probe has the explicit directive key; rejects missing keys and invalid values. Shell syntax and Python 3.6 grammar also checked.
- **EXTERNAL USER REPORT, not independently reproduced here:** Python 3.6.8 and eight Apache `mod_php` checks ran on **Ubuntu 24.04 / Apache 2.4.68 built from source**, not RHEL7.
- **STILL NOT RUN:** RPM builds on RHEL7, installed Apache mod_php on RHEL7, RHEL7 runtime gates, signed RPM verification.

## Independently executed locally on Debian (NOT RHEL7)

| Check | Result | Scope |
|---|---|---|
| Patch215 `patch --dry-run --fuzz=0 -p1` against RC5 working source | PASS | Clean application of modified FPM C source |
| FPM C syntax check | PASS | `gcc -fsyntax-only` with PHP 5.4 headers and `HAVE_TIMES` |
| FPM configure and complete `make -j8` build | PASS | PHP 5.4.16 CLI/CGI/FPM; Debian toolchain |
| Live `php-fpm` FastCGI status requests | **10/10 PASS** | Text, HTML, XML, JSON short/full output; markup/quote injection cases; XML and JSON parseable |
| FPM escape helper C unit checks | PASS | 9 JSON/UTF-8 cases, 1 plain-text case, 2 HTML/XML encoding-call signature/flag mocks |
| Source assertions | PASS | Fields and freeing after format-specific FPM escaping |
| PHP 5.4 HTML/XML entity flags | PASS | Built PHP 5.4.16 CLI `htmlspecialchars` with `ENT_QUOTES|ENT_SUBSTITUTE|ENT_DISALLOWED|ENT_XML1` produced escaped markup |
| Build script Bash syntax | PASS | Does not execute RHEL7 RPM build |
| RPM source spec integration | PASS | Exactly 16 declared patches (Patch200–215) with ordered `%patch` entries |
| Manifest and ZIP integrity | PASS | Recomputed at release packaging |

**Important distinction:** the FPM source helper unit test uses a mock for the PHP HTML/XML encoding-call API; it proves the correct flags and output allocation contract, not real service behavior. The separate **10-request actual Debian FPM** test exercises the real encoder via an isolated, unprivileged FastCGI service.

## Previous evidence (unchanged code)

- RC5 patched CGI normal/short/empty PATH_INFO smoke cases and PHPT: previously reported as PASS, not rerun as a RHEL7 CGI binary.
- User-supplied RC4 report: 4,173 selected tests, 12 patch-only divergences (four `memory_limit`, eight disabled RFC1867 upload progress), no new SOAP test differences.
- SOAP 210/211 patched-only regression tests: passing according to user report; no unpatched reproducer or memory-safety proof.
- FTPS 212: eight wrapper operations refused cleartext fallback in the earlier user test. A later external user report confirms successful TLS upload/download in both builds; directory listing fails in both.
- Error logging 213: startup UTC and script-local timestamps observed in earlier tests; end-of-request behavior source-reviewed only.

## BLOCKED / NOT CLAIMED

**RHEL7 toolchain build/RPM packaging and signatures; Apache mod_php and RHEL7 PHP-FPM integration; RHEL7 FTPS TLS transfer; independent SOAP/CGI before/after memory-safety validation; end-of-request logging; 13 inherited legacy PHPT divergences; formal release approval.**

The candidate remains **NO-GO for production**. Do not represent a Debian FastCGI smoke pass as RHEL7 or Apache certification.

## New reproducible functional regression (RC6 verification update)

On Debian 13 using the **compiled patched PHP 5.4.16 php-fpm**, the new `tests/test-fpm-status-fields.py` ran 23 checks successfully. It starts FPM locally as an unprivileged account with a private Unix socket, executes an actual PHP script, then checks **method, URI, query, Basic-auth username and script filename** in JSON, XML and HTML representations. Invalid output or missing fields fails the test. The output is recorded under `evidence/RC6_DEBIAN_FPM_FIELDS_APPLICATION_TEST.txt`.

This test **does not** cover Apache mod_php, the RHEL7 toolchain, signed RPMs, or a production-style web server. PHP patch files are unchanged.


## Final handoff: environment-specific gates

- Added isolated RHEL7 `libphp5.so` testing code (Apache application GET/POST/file upload/session/404) — **NOT RUN: RHEL7 target unavailable here**.
- Added RHEL7 RPM build, NEVRA/module and signature validation runner — **NOT RUN: RHEL7 toolchain and signing key unavailable here**.
- Existing recorded Debian Apache → FPM HTTP integration: four scenarios passed; Apache `mod_php` not represented by that result.
- Full-suite external report identifies 13 patch-only incompatibilities (5 memory-limit + 8 upload-progress). SOAP/CGI differential evidence gaps remain **NOT CLOSED**. The older selection of 4,186 tests identified 12.
- No other PHP C source or RPM patches were changed in this verification handoff.

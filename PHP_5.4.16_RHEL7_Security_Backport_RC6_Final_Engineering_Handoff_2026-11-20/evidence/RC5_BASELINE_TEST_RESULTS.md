# RC5 evidence record — 19 November 2026

## Tests actually executed locally (Debian 13, GCC 14.2; NOT RHEL7)

- `Patch214` source application: **PASS** with `patch --dry-run --fuzz=0 -p1` against the fully RC4-patched PHP 5.4.16 source.
- Compiling `sapi/cgi/cgi_main.c` into `sapi/cgi/cgi_main.lo`: **PASS** (no added compiler warnings observed).
- Linking `sapi/cgi/php-cgi`: **PASS**, isolated Debian build with existing compiled RC4 objects and regenerated test-only static-extension table. This is **not** a clean RPM/SRPM build and does not validate RHEL7 dependencies.
- Targeted `cgi-path-info-smoke.sh`: **3 PASS / 0 FAIL** (valid, too-short, empty PATH_INFO).
- Bundled PHP 5.4-compatible `cgi-path-info-underflow-php54.phpt`: **1 PASS / 0 FAIL**, executed against patched `php-cgi`.
- Shell script parsing `bash -n`, patch/spec checks, source checks, checksum checks and archive ZIP test: **PASS**.
- Old Patch200–213: source retained byte-for-byte from RC4; **not rerun** in this release except inherited CGI runtime context.

## Not validated (mandatory gates)

- An actual RHEL7/GCC4.8 `rpmbuild -ba` and installation of binary RPMs.
- Apache `mod_php` staging smoke/regression tests and real application traffic.
- Comprehensive CGI and SOAP regressions / before-after SOAP security proof.
- Full encrypted FTPS transfer, end-of-request logging, 12 inherited patch-only regressions, FPM status endpoint security review, signing/approval.

**NO-GO for production.** Do not interpret checks supplied in scripts as tests already run.

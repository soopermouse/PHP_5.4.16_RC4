# RC6 release-gate checklist (fail closed)

## 20 November 2026 test-script corrections

- Conditional `mod_authz_host` loading for Apache `Require local`.
- Python 3.6 subprocess compatibility and `PYTHON3_BIN` selection.
- CGI/FPM runner looks in spec-generated `build-cgi/` and `build-fpm/`.
- `session.upload_progress.enabled` accepts default `On` and PHP 5.4 `Off` returning empty (only if the directive appears in probe output), without falsely certifying upload-progress functionality.
- New candidate-only Apache multipart body-part-limit test (Patch202). Earlier generic smoke cases also pass unpatched binaries, so treat the new case plus installed RPM ownership as stronger evidence.

Tests/lint and both checksum gates performed on Debian. The external Apache and Python 3.6.8 tests were performed on Ubuntu 24.04, not RHEL7; rerun the native release gate on authorized RHEL7 staging. Still **NO-GO** without native evidence, independent compatibility assessment, and signing.


- [ ] Integrity: `sha256sum -c SHA256SUMS` in release root, and `cd rpm-kit && sha256sum -c SHA256SUMS`.
- [ ] Target host: isolated, authorized RHEL7 x86_64 build VM, non-root account, trusted dependency repository.
- [ ] Vendor patches: all 95 apply cleanly, then Patch200–215 apply with zero fuzz and no reject.
- [ ] `rpmbuild -bp`, `-bs`, `-ba` all succeed; record build logs, source and binary NEVRA, compiler/toolchain, package checksums.
- [ ] `python3 release-gate/verify-source-rc6.py /path/to/BUILD/php-5.4.16` succeeds.
- [ ] `bash release-gate/verify-build.sh` succeeds, plus signed-RPM policy as appropriate.
- [ ] PHP CLI, CGI, FPM and Apache mod_php runtime tests each performed separately where deployed.
- [ ] Run `python3 tests/test-fpm-status-fields.py /path/to/patched/php-fpm` in a disposable, unprivileged host setup. Verify actual PHP application response and escaping for method, request URI, query, Basic-auth username and script name; repeat on RHEL7.
- [ ] RHEL7 FPM status page: HTML/XML/JSON (short/full) safely encode quotes, ampersands, markup, invalid UTF-8, control characters; restrict status path to loopback/admin ACL.
- [ ] SOAP Patch210/211 security behavior independently reviewed; RC4 patched-only PHPT is not a before/after vulnerability proof.
- [ ] External Ubuntu-host encrypted FTPS upload/download passed in the user report; repeat no-cleartext-fallback and authenticated encrypted transfer on RHEL7 and inventory incompatible integrations. Directory listing fails in both baseline and candidate.
- [ ] Full suite: memory-limit abort (**5** PHPT differences, including `ext/standard/tests/streams/bug61115-1.phpt`) and disabled upload progress (**8** differences) explicitly assessed and accepted **or replaced by separately reviewed and tested mitigations**. Earlier selected subset had 4+8. Do not silently waive.
- [ ] Apache staging: `httpd -t`, module check (`php5_module`), mod_php-specific endpoint, application/session/upload flows and error lifecycle; temp probe removed.
- [ ] `php-cgi` and FPM issues validated with real request-level tests on deployment-like staging hosts.
- [ ] Independent security, owner and operational rollback approval recorded; signed target RPMs.

A successful source build, CLI run or unsigned candidate RPM **does not** clear production release. Current status: NO-GO.

**Applicability note (CVE-2026-129291):** the upstream specific deferred worker-cleanup flaw was introduced after PHP 5.4; see `docs/CVE-2026-129291_PHP54_APPLICABILITY.md`. No speculative 5.4 patch is present.

## Final gate additions (20 November)

- [x] Structural before/after source-extracted AddressSanitizer tests for Patch210/211/214 locally passed; [ ] full PHP differential memory instrumentation remains mandatory for security certification.
- [x] `13`-difference risk-review validator installed; [ ] owner/integrations/evidence/ticket and *independent* authorized acceptance to be supplied (pending template is deliberately rejected).
- [ ] RHEL7 native RPM build, signatures, installed Apache application, signed/approved change ticket and rollback exercise remain target-host checks.

## 20 November final engineering update

**Implemented and locally verified:** three pre/post patch source-extracted AddressSanitizer differential demonstrations (Patch210/211/214), patched CGI smoke tests, all 17 modified sources equal the complete patched tree, improved 13-difference independent acceptance gate (fails closed on pending review), both SHA-256 manifests, and single-command local qualification. **No source security patch changed.**

**Production NOT APPROVED:** Full PHP memory-safety instrumentation, genuine RHEL7 native RPM/toolchain, installed/signed RPM and Apache mod_php execution, actual application impact assessment, and human authorization remain target-dependent. No fake approvals or synthetic production results are included.

> **20 November 2026 correction v2 (followed by full-suite evidence update):** Restored `rpm-kit/SHA256SUMS`, fixed the PHP `Off`→empty `ini_get()` case without accepting a missing directive, and corrected the external Ubuntu 24.04 evidence attribution and archive paths. Source patches/spec/SRPM unchanged. **NO-GO pending RHEL7.**

# RC6 patch release status — 19 November 2026

## Release-gate tooling hotfix, 20 November 2026

**DONE (scripts and documentation):** four RHEL7 test defects corrected: `authz_host` loading; Python 3.6 subprocess API; correct `build-cgi`/`build-fpm` runtime paths; and correct handling of upload-progress INI defaults, including empty `ini_get()` for `Off`. Added an Apache Patch202-specific multipart limit probe and local `tests/test-release-tooling.py`.

**TESTED LOCALLY:** both checksum manifests, an explicit empty-vs-missing upload-progress test, Python syntax and 3.6 grammar, shell syntax, self-test for all four fixes, FPM source-backed C test, and Apache config syntax on Debian with local PHP 8.4 module (only a syntactic check, not RC6 runtime). All original source patches, 17 modified C/header files, the spec, and SRPM remain unchanged.

**NEEDS TESTING:** native Python 3.6 execution on RHEL7 (the external Python 3.6.8 test was on Ubuntu 24.04), RPM toolchain/build on RHEL7, Apache libphp5/Patch202 integration, staged CLI/CGI/FPM, signed RPMs and all inherited security/release gates. The full 12,315-test external suite found thirteen patch-only divergences (five memory-limit and eight upload-progress); the smaller selection had twelve, and no production deployment was performed.


**Candidate label:** PHP 5.4.16 for RHEL 7 — Security Backport Patchset (RC6)

**DONE / implemented in source:** Patch200–215; FPM HTML/XML/JSON status escaping (Patch215) added to RC5 CGI fix and unchanged RC4 security series; spec and shell build gates updated; README and exact patch inventory corrected.

**TESTED LOCALLY (Debian, not RHEL7):** FPM translation-unit syntax, full PHP 5.4 CLI/CGI/FPM build, ten real FastCGI text/HTML/XML/JSON request tests including injected markup, targeted C escape tests, and clean Patch215 application. RC5 CGI smoke/PHPT prior results remain historical evidence.

**OPEN:** thirteen externally reported patch-only regression differences (five allocator fatal-exit and eight RFC1867 session upload-progress); memory-checker/differential proof for SOAP/CGI, end-of-request logger, compiled FPM service response on RHEL7, actual RHEL7 RPM build/signature and Apache mod_php staging tests, security/ops approval.

**NEXT:** Run `release-gate/RELEASE_GATE_RC6.md` in a RHEL7 x86_64 staging/build environment; review compatibility and approve or redesign with security testing.

**DEPLOYMENT: NO-GO.** A complete local source archive is not a production-qualified RPM release.

## RC6 verification update (test/documentation only)

**Added and locally passed:** real PHP application over unprivileged FastCGI and 23 FPM status-field/encoding checks across JSON/XML/HTML, including Basic-auth username and script name. Details in `docs/EVIDENCE_AND_RELEASE_DECISIONS.md`.

**CVE-2026-129291:** upstream advisory dates the specific delayed FPM child-cleanup path to PHP 8.1.20/8.2.7. PHP 5.4.16 does not contain that path. No unverified source backport added; see `docs/CVE-2026-129291_PHP54_APPLICABILITY.md`.

**Remaining mandatory:** SOAP/CGI memory-safety differential proof, 13 externally reported, unaccepted incompatibility divergences; repeat encrypted FTPS on RHEL7 (external non-RHEL7 upload/download reported as passed); actual RHEL7 build/Apache mod_php and signatures, formal approval. **NO-GO**.


## Final source-and-target-gates handoff

**DONE (code):** Packaged complete patched source archive, retained all Patch200–215, added `target-host-tests/test-modphp-isolated.py` to exercise installed candidate `libphp5.so` without changing the machine's normal Apache configuration; added `target-host-tests/run-rhel7-release-gates.sh` to build, verify and collect runtime evidence.

**TESTED:** Debian Apache2 + PHP 5.4 FPM HTTP GET, POST, query and missing-script checks; Debian target regressions as in `evidence/local-debian13/`. Python source compiled and shell script linted.

**NEEDS TESTING ON REAL RHEL7/Apache:** actual RPM compilation/signatures; installed `libphp5.so` under RHEL7 Apache; CGI/FPM on RHEL7; full application, session, multipart, SOAP memory safety, authenticated FTPS transfer on RHEL7 (external non-RHEL7 upload/download reportedly passed); 13 inherited PHPT compatibility divergences must be assessed. No attempt made to present Debian as RHEL7.

**FINAL STATUS:** source candidate and target-host tests DELIVERED; release stays **NO-GO** until target-specific evidence and independent sign-off.

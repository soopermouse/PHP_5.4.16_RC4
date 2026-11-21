# RC6 tooling-fix manifest — 20 November 2026

## REPLACE (same relative paths in existing RC6 repository)

- `README.md`
- `RELEASE_STATUS.md`
- `TEST_RESULTS_RC6.md`
- `target-host-tests/README.md`
- `target-host-tests/test-modphp-isolated.py` — load `authz_host`, patch-specific multipart limit test, Python 3.6 subprocess API
- `target-host-tests/run-rhel7-release-gates.sh` — Python version selection, corrected build paths, C test in gate
- `tests/test-fpm-rc6-source.py` — Python 3.6 subprocess API
- `release-gate/staging-checks.sh` — accept legitimate On/Off INI values
- `release-gate/README_APACHE_STAGING.md`
- `release-gate/RELEASE_GATE_RC6.md`
- `local-integration/test-apache-fpm-integration.py` — subprocess API normalization
- `SHA256SUMS` — regenerated checksum manifest

## ADD

- `tests/test-release-tooling.py` — reproducible local script checks
- `TOOLING_FIX_MANIFEST.md` — this file

## DELETE

- None. Keep all 16 original candidate C patches and the unchanged spec, 17 reference source files, full source archive, and original source RPM.

## Scope and release gate

This is a **test-script/documentation hotfix**, not a new security code release. No native RHEL7 RPM build, mod_php RC6 run, or Python 3.6 interpreter is available in the local environment. Until those tests are executed and reviewed, **NO-GO for production**. The 12 existing behavioral differences and prior SOAP/CGI/FTPS evidence gaps are not claimed resolved.

## Second correction, 20 November 2026 — ADD/REPLACE

- **ADD:** `rpm-kit/SHA256SUMS`, previously missing. Includes all 16 security patches, spec, build script, status and spec diff.
- **REPLACE:** `release-gate/staging-checks.sh`, `tests/test-release-tooling.py`, `README.md`, `RELEASE_STATUS.md`, `TEST_RESULTS_RC6.md`, `target-host-tests/README.md`, `TOOLING_FIX_MANIFEST.md`, and top-level `SHA256SUMS`.
- **KEEP UNCHANGED:** Patch200–215, original source RPM, modified source-file references, full patched source archive, `rpm-kit/php.spec`, `rpm-kit/build-rc.sh`, existing Apache runtime test and RHEL7 release runner.
- **DELETE:** none. This is a tooling correction only; no new PHP CVE fix was added.

**Correction to evidence provenance:** the external mod_php and Python 3.6.8 tests were performed on Ubuntu 24.04, not RHEL7. RHEL7 native RPM and Apache tests remain unexecuted.

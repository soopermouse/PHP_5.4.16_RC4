# RHEL7 and Apache mod_php test tools

## Script-fix update (20 November 2026)

**RHEL7 test compatibility**: Python **3.6+** supported at source/API level (`subprocess.run(..., universal_newlines=True)`); use `PYTHON3_BIN=/path/to/python3.6` for the gate runner if the system default `python3` is absent. An external tester reports exercising these scripts under Python 3.6.8 compiled on Ubuntu 24.04; native RHEL7 validation is still outstanding.

**Apache**: `test-modphp-isolated.py` loads `mod_authz_host` when dynamic; `Require local` now has its required provider. It tests a candidate-only setting `max_multipart_body_parts=2` through an actual three-field multipart request. A basic GET/POST pass on an unpatched module is not enough; this new test must reject the third field.

**RPM build paths**: look for `build-cgi/sapi/cgi/php-cgi` and `build-fpm/sapi/fpm/php-fpm` under `$RPM_TOPDIR/BUILD/php-5.4.16/`, not directly under `sapi/`. `rpmbuild -ba` must retain that build tree, or runtime tests cannot proceed even when the RPM files were produced. See `rpm-kit/php.spec` for the source-of-truth SAPI build layout.

**Two-stage procedure**: (1) run `BUILD_RC6=1 MODPHP_RC6=0 bash target-host-tests/run-rhel7-release-gates.sh` on a disposable RHEL7 builder with RPM build dependencies; (2) after installing the reviewed/signed candidate on an isolated Apache staging VM and making the build/artifact tree available under the same `RPM_TOPDIR`, run `BUILD_RC6=0 MODPHP_RC6=1 REQUIRE_RPM_SIGNATURES=1 bash target-host-tests/run-rhel7-release-gates.sh`. You may also invoke `python3 target-host-tests/test-modphp-isolated.py` independently for the installed module test.

**Session upload-progress**: an `Off` setting can yield an empty string from PHP 5.4 `ini_get()`; `staging-checks.sh` accepts it only when the probe emits that directive. The `php.ini` default is commonly `On` even though RC6 Patch200 forces the upload-progress callback to return early. `staging-checks.sh` no longer mistakes `On` for an active callback. A suitable runtime security test is still needed for authoritative feature behavior.

**Status:** tooling and checksum gate corrections locally linted/tested, but **RHEL7 native execution remains NEEDS TESTING**. This is not automatic production approval.


These are runnable **tests**, not logs of completed RHEL7 execution. Do not run on production.

`run-rhel7-release-gates.sh`: checks RHEL7, validates manifests, optionally builds RPMs (BUILD_RC6=1), asserts candidate identity, runs CGI/FPM tests, and optionally runs isolated installed mod_php (MODPHP_RC6=1). Logs go to `rc6-target-evidence/`.

`test-modphp-isolated.py`: demands RHEL7 and an installed candidate RPM owning `libphp5.so`. Uses a temporary, loopback-only Apache instance, PHP script, and session directory; performs GET, session persistence, form POST, multipart upload, directive inventory, missing-file handling. It never edits production Apache config. Requires Python 3 on the target.

Complete signed RPM and production-like target evidence must be reviewed separately; a local test pass is not authorization to deploy.

## Final test controls

The runner additionally executes `tests/test-soap-cgi-source-differentials.py` under GCC AddressSanitizer against reconstructed pre/post patch source, requiring `xml2-config` and ASan toolchain support. This is *source-extracted* proof, not full PHP memory-safety certification.

In `REQUIRE_RPM_SIGNATURES=1` mode, it also requires `MODPHP_RC6=1`, an explicitly provided `MODPHP_PROBE_URL`, and a real externally authorized `RC6_COMPAT_REVIEW_FILE` passing `release-gate/verify-compatibility-assessment.py`. See the new README section.

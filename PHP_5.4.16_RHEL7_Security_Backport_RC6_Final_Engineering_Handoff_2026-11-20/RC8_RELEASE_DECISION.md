# RC8 engineering completion and independent target-host handoff

Date: 2026-11-20. This is a corrected qualification/packaging revision of RC7, **not a new PHP source patch**.

## Implemented
- Preserved original PHP source archive, RPM source package, and Patch200–215 unmodified.
- Changed target-host gate to require **independent external evidence files** for RHEL7 authenticated FTPS, a full PHP memory-safety review, and production change approval when production-gate mode is selected.
- Added regression test for this release-gate contract; integrated into local qualification.
- No blanket claim of CVE coverage or production readiness.

## Claude / independent tester execution
On an isolated, authorized RHEL7 x86_64 builder with Python 3.6+ and the archived trusted build toolchain:

```bash
sha256sum -c SHA256SUMS
(cd rpm-kit && sha256sum -c SHA256SUMS)
python3 tests/test-production-gate-contract.py
bash tests/run-local-qualification.sh
BUILD_RC6=1 MODPHP_RC6=0 bash target-host-tests/run-rhel7-release-gates.sh
```

On a **separate authorized RHEL7 Apache staging VM** with independently signed, reviewed candidate RPMs and controlled probes, preserve the same RPM build tree and set all paths to genuine external evidence:

```bash
export MODPHP_PROBE_URL='https://staging.example.invalid/private/php54-probe'
export RC6_COMPAT_REVIEW_FILE='/secure-review/compatibility-approved.json'
export FTPS_RHEL7_EVIDENCE_FILE='/secure-review/ftps-rhel7-test-results.txt'
export FULL_MEMORY_SAFETY_REVIEW_FILE='/secure-review/full-php-memory-review.txt'
export PRODUCTION_CHANGE_APPROVAL_FILE='/secure-review/change-approval.txt'
BUILD_RC6=0 MODPHP_RC6=1 REQUIRE_RPM_SIGNATURES=1 bash target-host-tests/run-rhel7-release-gates.sh
```

The URL and paths above are **placeholders**, not test evidence. The runner checks that external files exist, but **does not authenticate** their content: human reviewers must confirm independent results, credentials, candidate provenance, and actual staging configuration. Do not bypass required review with dummy files.

## Required observations for sign-off
- Native RHEL7 binary/SRPM build and signature validity; installed Apache module, CGI, and FPM exercised under correct host configs.
- RHEL7 authenticated FTPS upload/download, downgrade/refusal behavior; genuine PHP-application session, upload, PHAR, SOAP, CGI and FPM checks.
- Full memory sanitizer/instrumented PHP-path analysis (not just extracted mini-harnesses).
- Independent disposition of **13 observed differing PHPT tests** (five `memory_limit`, eight session upload progress), and 17 pre-existing failures observed on both builds.
- Approved compensating controls and rollback with named operations/security sign-off.

## Release decision
**Engineering patchset complete; production deployment NO-GO pending independent target and security evidence.** This package may be handed to Claude for independent execution and results review. A locally passing check cannot establish security certification on an untested RHEL7/Apache host.

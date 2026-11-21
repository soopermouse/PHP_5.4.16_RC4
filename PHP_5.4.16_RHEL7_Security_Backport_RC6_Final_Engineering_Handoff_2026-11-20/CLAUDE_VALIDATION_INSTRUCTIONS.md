# Independent test instructions — PHP 5.4.16 RHEL7 RC6

This package contains **actual PHP C source and RPM build files**. Source revision remains RC6, with 16 unchanged security patches. Do not replace source with stubs or reapply the patches to the already patched source archive.

## 1. Confirm release integrity and code identity

Extract the **final engineering handoff** ZIP. From its top-level directory:

```bash
sha256sum -c SHA256SUMS
(cd rpm-kit && sha256sum -c SHA256SUMS)
python3 tests/test-release-tooling.py
bash tests/run-local-qualification.sh
```

The local qualification script requires GCC with AddressSanitizer, libxml2 headers / `xml2-config`, `patch` and Python 3.6+. It extracts the included fully patched PHP source and runs before/after *source-extracted* tests for Patch210, Patch211 and Patch214. These are **not full PHP memory-safety proofs**.

## 2. Native RPM build, isolated RHEL7 x86_64 VM

Use an authorized clean RHEL7-compatible virtual machine with the organization's trusted archived repositories and build dependencies. Run as an ordinary user:

```bash
BUILD_RC6=1 MODPHP_RC6=0 bash target-host-tests/run-rhel7-release-gates.sh
```

Capture `rc6-target-evidence/GATE_SUMMARY.txt`, logs, `%check` output, SRPM/binary RPM list, RPM NEVRA, compiler warnings, and modified module hashes. The gate must refuse missing dependencies and source/checksum mismatches; **do not fake OS identity or skip failures**. RHEL7 `libasan`/`libxml2-devel` must be installed from approved sources for the differential harnesses.

## 3. Actual PHP runtime and Apache integration, isolated staging

On a separately authorized staging VM, install *reviewed and signed candidate RPMs* using the organization's normal deployment process. Preserve or transfer the matching RPM build tree for source-based checks. Run the standalone isolated test:

```bash
python3 target-host-tests/test-modphp-isolated.py
```

Check real Apache application execution, sessions, form POST, actual multipart uploads, Patch202 multipart-limit enforcement and missing-file handling. Configure a short-lived loopback-only staging probe as described in `release-gate/README_APACHE_STAGING.md` and remove it after verification. Capture SELinux denials, Apache module ownership, installed `rpm -q`, request logs, TLS-protected FTPS upload/download and rollback exercise. Do not assume Apache→FPM testing is equivalent to mod_php.

## 4. Full-suite and differential memory-safety evidence

The externally reported complete comparison was 12,315 PHPT tests and **13 patch-only differences: five memory-limit and eight session-upload-progress**. Verify that list and paths against the actual raw outputs; the external report ZIP was not available to this build session. Do not misreport those intentional differences as passing PHPT tests.

The new isolated C sanitizer tests provide bounded before/after *algorithm* evidence for Patch210, Patch211 and Patch214. For full PHP memory-safety evidence, arrange independent review and controlled ASan/Valgrind builds and tests for SOAP array dimensions, DTD cleanup and CGI PATH_INFO, with timeouts, resource limits and sandbox isolation. Record sanitized logs without bypassing previous test-safety restrictions. These are still outstanding until performed.

## 5. Human release control

The PENDING `release-gate/compatibility-assessment.template.json` is **not** a release authorization. Complete a genuine impact review covering every affected application, all 13 PHPT differences, a separate approver, ticket and rollback; authenticate approver identity outside this script. The schema validator rejects unreviewed and wrong-kit assessments:

```bash
python3 release-gate/verify-compatibility-assessment.py \
  /path/to/approved/compatibility-assessment.json
```

Only once signed artifacts, a candidate-owned Apache module, the staging probe, compatibility acceptance and other target controls are actually available:

```bash
RC6_COMPAT_REVIEW_FILE=/path/to/approved/compatibility-assessment.json \
MODPHP_PROBE_URL=http://127.0.0.1/path/modphp-runtime-probe.php \
BUILD_RC6=0 MODPHP_RC6=1 REQUIRE_RPM_SIGNATURES=1 \
 bash target-host-tests/run-rhel7-release-gates.sh
```

This checker validates review completeness, **not approver cryptographic identity**. Passing it alone does not make a PHP 5.4/RHEL7 legacy deployment generally secure. The release remains *NO-GO* until the independent target-host tests and release-authorization steps are completed.

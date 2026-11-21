# PHP 5.4.16 RHEL7 RC6 — Gate kit correction v2 (2026-11-20)

This hotfix fixes the user-reported gate-script packaging defects. It **does not change PHP security code** and remains RC6, not a new RC7 patchset.

## Fixed

1. Restored the missing `rpm-kit/SHA256SUMS`; each entry is SHA-256-verified and the gate runner now passes its initial two-manifest check on extracted archive contents.
2. `staging-checks.sh` accepts an empty `session.upload_progress.enabled` from PHP 5.4's `ini_get()` when configured `Off`, but still rejects a missing directive or unknown nonempty value. No security-control behavior is inferred from this INI setting.
3. Corrected user-reported external test environment: Ubuntu 24.04 / Apache 2.4.68 compiled from source and separately compiled Python 3.6.8. No RHEL7 runtime result is claimed.
4. Fixed ZIP and extraction folder names in `README.md`.
5. Extended `tests/test-release-tooling.py` to execute both checksum verification commands and test missing-vs-empty progress data.

## Unchanged

`rpm-kit/*.patch`, `rpm-kit/php.spec`, `rpm-kit/build-rc.sh`, original SRPM, and patched-source-file references are byte-for-byte unchanged. The runner itself has not been weakened or made to skip any required gate.

## Target requirements

RHEL7 RPM build/signing; installed mod_php and FPM/CGI staging; thirteen full-suite PHPT compatibility differences (5 memory-limit, 8 upload progress; earlier selection: 12); FTPS encrypted transfer; SOAP/CGI differential security testing; independent deployment approval are still open. **NO-GO for production.**

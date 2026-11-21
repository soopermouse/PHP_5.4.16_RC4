# PHP 5.4.16 for RHEL 7 — RC6 verified test-kit update (19 November 2026)

This is a **full actual source kit** with new local regression evidence and documentation. No PHP C source or security patch was modified from RC6.

**Added:** `tests/test-fpm-status-fields.py`; `docs/CVE-2026-129291_PHP54_APPLICABILITY.md`; `docs/EVIDENCE_AND_RELEASE_DECISIONS.md`; `evidence/RC6_DEBIAN_FPM_FIELDS_APPLICATION_TEST.txt`.

**Replaced:** `README.md`, `TEST_RESULTS_RC6.md`, `RELEASE_STATUS.md`, `release-gate/RELEASE_GATE_RC6.md`, `SHA256SUMS`.

**Delete:** none when overlaying a clean RC6. Old obsolete pre-RC6 files still must be deleted as in `DELETE_FROM_RC5.txt`.

**Verification:** 23 live FastCGI application-and-status checks PASS; all 16 patches, 17 patched source files, source RPM, RPM spec and build scripts byte-identical to RC6. RHEL7 and Apache mod_php still **NOT tested**, release **NO-GO**.

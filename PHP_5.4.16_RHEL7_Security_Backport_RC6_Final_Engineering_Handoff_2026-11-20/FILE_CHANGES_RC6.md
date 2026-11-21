# RC6 final engineering handoff — file changes

**PHP source/security patches and RPM build spec are unchanged.** No files are deleted by this update. Existing repository users must copy the changed files explicitly; do not assume an overlay deletes old files.

## REPLACE

- `README.md`
- `RELEASE_STATUS.md`
- `SHA256SUMS`
- `TEST_RESULTS_RC6.md`
- `release-gate/RELEASE_GATE_RC6.md`
- `target-host-tests/README.md`
- `target-host-tests/run-rhel7-release-gates.sh`

## ADD

- `FILE_CHANGES_RC6.md` (this manifest; omitted in the previous list)

- `CLAUDE_VALIDATION_INSTRUCTIONS.md`
- `FINAL_ENGINEERING_HANDOFF.md`
- `evidence/source-differential-local-2026-11-20/array_baseline.c`
- `evidence/source-differential-local-2026-11-20/array_patched.c`
- `evidence/source-differential-local-2026-11-20/cgi_baseline.c`
- `evidence/source-differential-local-2026-11-20/cgi_patched.c`
- `evidence/source-differential-local-2026-11-20/differential-results.json`
- `evidence/source-differential-local-2026-11-20/dtd_baseline.c`
- `evidence/source-differential-local-2026-11-20/dtd_patched.c`
- `release-gate/compatibility-assessment.template.json`
- `release-gate/verify-compatibility-assessment.py`
- `tests/run-local-qualification.sh`
- `tests/test-compatibility-gate.py`
- `tests/test-soap-cgi-source-differentials.py`

## DELETE

- None.

## KEEP unchanged

- All Patch200–215 security patch files; `rpm-kit/php.spec`, `rpm-kit/build-rc.sh`, `rpm-kit/SHA256SUMS`; 17 modified C/header files; complete PHP source archive and original source RPM.

The updated top-level SHA256SUMS is the authoritative manifest.

## Verification of completeness

The REPLACE/ADD classification above is based on the comparison with the immediately preceding `RC6_Full_Suite_Evidence_Update` full kit. Files already present in that preceding kit are not newly added merely because they are in this full ZIP. The complete file inventory is in `FILE_INVENTORY_RC7.txt`; the exact baseline-to-handoff comparison is in `RC6_HANDOFF_DIFF_FROM_FULL_SUITE.txt`.

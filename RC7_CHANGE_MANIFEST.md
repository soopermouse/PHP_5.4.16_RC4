# RC7 release-tooling correction — compared with final RC6 handoff

## REPLACE
- `tests/test-release-tooling.py` — explicit UTF-8 reads; Python 3.6.8 under C/non-UTF-8 locales
- `FILE_CHANGES_RC6.md` — corrected historical handoff list and comparison baseline
- `SHA256SUMS` — recalculated SHA256 hashes for the delivered package

## ADD
- `RC7_CHANGE_MANIFEST.md` — this delta
- `FILE_INVENTORY_RC7.txt` — exhaustive archive inventory
- `RC6_HANDOFF_DIFF_FROM_FULL_SUITE.txt` — historical comparison against previous full kit
- `RC7_LOCAL_VALIDATION.md` — what ran and what remains open

## DELETE
- None

## UNCHANGED
- All PHP source, sixteen security patches, patched PHP source archive, RPM spec and all existing security and runtime tests (except the explicitly listed release-tooling test).

## RELEASE STATUS
- This remains **NO-GO** pending target-host authorization, independent assessment, and complete evidence.
- Bounded before/after source ASan harnesses are not full PHP ASan proof.
- Python 3.6.8 verification must be separately executed on that interpreter and locale; Python 3.6 syntax scans are not a substitute.

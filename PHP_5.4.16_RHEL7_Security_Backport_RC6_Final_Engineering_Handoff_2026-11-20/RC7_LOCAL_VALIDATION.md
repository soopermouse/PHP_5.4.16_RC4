# RC7 local validation (20 November 2026)

- `python3 tests/test-release-tooling.py`: PASS in current Python environment.
- `bash tests/run-local-qualification.sh`: PASS with both SHA manifests, compatibility schema, FPM source, and bounded source-extracted ASan differential harnesses for Patch210/211/214.
- `python3.6` binary: NOT AVAILABLE here. The exact Python 3.6.8 + unset UTF-8 locale test has NOT been executed in this environment. Code now uses explicit UTF-8 reads.
- Complete 12,315-test PHP regression suite: NOT RERUN here; previous independent result (13 differing tests, 17 failures in both builds) reported unchanged by user.
- Six fresh PHP builds, RHEL7 RPM staging, Apache mod_php, and production-like rollout: NOT RERUN here.
- Source, RPM patch files, and PHP source tarball: UNCHANGED in RC7.
- Release decision: NO-GO pending full independent compatibility review and deployment-specific gates.

Local harness outputs are supplied separately as `RC7_LOCAL_QUALIFICATION_EVIDENCE.zip`.

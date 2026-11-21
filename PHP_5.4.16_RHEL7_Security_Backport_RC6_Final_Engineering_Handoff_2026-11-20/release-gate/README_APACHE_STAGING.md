# Apache mod_php — RHEL7 staging release gate

## RC6 tooling correction (20 November 2026)

The isolated Apache test now loads `mod_authz_host` dynamically if needed by `Require local`. It also tests Patch202-specific multipart part limiting, not just PHP module health. Run `python3 target-host-tests/test-modphp-isolated.py` on a disposable RHEL7 host with the candidate-owned `libphp5.so`. The test accepts a Python 3.6 interpreter.

`staging-checks.sh` now allows `session.upload_progress.enabled` to be either `On`/`1` (the normal PHP 5.4 INI default) or `Off`/`0`, because Patch200 disables the actual callback in C. The INI value is not runtime proof; use source/behavioral checks and review the installed package.


**Only on an isolated, backed-up staging instance. Do not apply this procedure to production without separate approval.**

1. Install matching candidate RPMs into the staging VM using an authorized internal repository/transaction. Do **not** run `rpm -Uvh` directly on production.
2. Check `rpm -q php`, `rpm -ql php | grep libphp5.so`, `httpd -V`, and `httpd -t`.
3. Confirm `httpd -M` lists **php5_module** and **mpm_prefork_module**. Both must match your deployment architecture. Verify no duplicate php module or incompatible MPM.
4. Restrict the temporary probe to loopback using Apache `Require local` inside an isolated Directory/Location configuration. The in-script IP guard is defense in depth, not a replacement for server access control.
5. Temporarily copy `modphp-runtime-probe.php` to a known, loopback-accessible staging document root. Never publish publicly. Run:

```bash
MODPHP_PROBE_URL=http://127.0.0.1:80/modphp-runtime-probe.php bash release-gate/staging-checks.sh
```

6. Remove the probe after testing, verify 404, inspect logs for leaks. Run *actual application* GET/POST, sessions, file uploads, multipart limits, TLS clients, SOAP and error-log smoke tests.
7. Record before/after Apache startup warnings, module `php5_module`, package NEVRAs and any functional differences. Obtain independent sign-off, retain rollback snapshots.

The script only verifies a small number of runtime properties. A successful probe is **not** production approval.

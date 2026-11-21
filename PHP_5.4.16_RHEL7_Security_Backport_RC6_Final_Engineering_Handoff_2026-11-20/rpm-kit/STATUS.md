# RC6 RPM-kit status

All **16** candidate security/backport patch files are included as `Patch200` through `Patch215` and applied sequentially in `php.spec` after the 95 retained vendor patches. `Patch215` fixes FPM status output escaping in HTML, XML and JSON, including fields beyond the query string. `Patch214` fixes CGI `PATH_INFO` underflow.

Patch200 deliberately terminates on allocator failure and disables session upload-progress callbacks. **Patch206 only handles session-file truncation**; it does not disable upload progress. These incompatibilities remain unresolved and cannot be called green regressions.

`build-rc.sh` only runs on isolated, dedicated non-root RHEL7-compatible hosts. Debian syntax/functional tests do **not** establish a successful RHEL7 RPM build or Apache validation. Check `../README.md` and `../RELEASE_STATUS.md` before installing anything.

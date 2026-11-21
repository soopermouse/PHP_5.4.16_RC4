# What is closed and what is not — PHP 5.4.16 RC6

**Completed in this verification update**

- Confirmed CVE-2026-129291 is about the delayed FPM child-cleanup path introduced after PHP 5.4. Investigated the legacy `fpm_child_close()` code and documented why no speculative 5.4 patch was added.
- Added a real compiled PHP 5.4 FastCGI application smoke test **and** FPM status escaping checks for request **method, URI, query string, Basic-auth username and script filename** in HTML/XML/JSON. All 23 assertions/checks passed locally on Debian 13. Code is in `tests/test-fpm-status-fields.py`; recorded output in `evidence/RC6_DEBIAN_FPM_FIELDS_APPLICATION_TEST.txt`.
- Kept every C/header file, Patch200–Patch215, PHP RPM spec and build script **byte-identical** to the RC6 source kit. This is a **test/documentation update**, not RC7 and not a new security patch.

**NOT closed by this update**

- No independent unpatched-versus-patched memory-safety proof for SOAP 210/211 or CGI 214. The reported regression tests ran only on patched builds. The source diff/upstream equivalence is useful but not substitute evidence. The previous safety gate that prevented baseline memory testing has **not** been bypassed.
- No controlled RHEL7 RPM build, signed binary RPM, RHEL7 Apache `mod_php`, or production-like staging result in this environment. The local host is Debian 13. Run the provided release gates on a real RHEL7-compatible staging VM.
- An external user report now confirms encrypted FTPS upload/download against a test endpoint in both baseline and candidate builds; a directory listing failure is common to both. RHEL7-specific FTPS transfer and independent evidence review remain open.
- The **full 12,315-test suite** externally reports **five** `memory_limit` and **eight** disabled upload-progress PHPT divergences; the earlier selection found only four memory-limit failures. These are still the *designed security-behavior policy*, not green passes. Risk acceptance and application impact assessment remain mandatory. Do not restore unsafe old behavior or falsify the suite.
- No full audit proving the patchset covers every 2026 PHP advisory or application-specific vulnerability. PHP 5.4 and RHEL7 remain EOL.

**Release decision: NO-GO for production.** Complete the above gates or migrate to supported PHP. A green local source or FastCGI test result is not a deployment approval.

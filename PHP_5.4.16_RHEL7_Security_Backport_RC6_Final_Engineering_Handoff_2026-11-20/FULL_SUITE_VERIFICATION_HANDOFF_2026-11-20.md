# RC6 full-suite verification — external test findings

**Product:** PHP 5.4.16 for RHEL 7 — Security Backport Patchset (RC6)

**Date received:** 20 November 2026. **Source code:** unchanged from RC6.

This record summarizes results supplied in conversation by the external tester. The underlying external log ZIP and report were not available for independent inspection during this packaging operation. It is not a new test run or a release approval.

## Tested externally on non-RHEL7 host

- Fresh baseline and RC6 builds: debug, optimized without debug, thread-safe; no new warnings in RC6.
- All sixteen patches applied with zero fuzz and the 17 modified source files matched packaged source.
- Complete suite: 12,315 tests; 13 candidate-only differences versus unpatched: 5 allocator/memory-limit and 8 disabled RFC1867 upload progress. Earlier 4,186-test selection had 12 because `ext/standard/tests/streams/bug61115-1.phpt` was not included.
- FTPS encrypted upload and download succeeded in both builds; FTPS directory listing failed in both.
- CGI FastCGI behavior matched CGI-mode behavior for tested cases.
- Apache `mod_php`: 33,000 requests without failures in both builds.
- Previous targeted tests and kit gates were reportedly unchanged.

## Unresolved requirements

1. Independent differential memory-safety evidence for Patch210 (SOAP), Patch211 (SOAP), Patch214 (CGI). Do not bypass unsafe-test restrictions to obtain it.
2. RHEL7 native source/binary RPM build and executable/runtime tests; signed RPM verification and installer/repository checks.
3. RHEL7 Apache `mod_php`, CGI/FPM application checks, TLS FTPS transfer and operational rollback.
4. Explicit operator/security decision on all 13 patch-only compatibility divergences, with application impact assessed.
5. Full security coverage cannot be guaranteed on unsupported PHP 5.4 and RHEL7.

**Release decision: NO-GO until the environment-specific gates and approvals are completed.**

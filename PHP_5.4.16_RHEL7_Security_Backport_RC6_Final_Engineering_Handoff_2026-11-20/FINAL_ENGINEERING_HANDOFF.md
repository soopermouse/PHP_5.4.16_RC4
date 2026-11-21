# Final RC6 engineering handoff — 20 November 2026

**Product:** PHP 5.4.16 for RHEL 7 — Security Backport Patchset (RC6)

**Use:** C source, full patched source tar, original source RPM, 16 patch files, RHEL7 RPM spec/build integration and executable test scripts. Not a supported vendor security release.

## Verified in this handoff (Debian host)

- Top-level and `rpm-kit` SHA-256 manifests verified; all 17 patched source files matched the full source archive.
- CLI and CGI were previously built on Debian; the existing candidate `php-cgi` binary passed 3 CGI `PATH_INFO` requests again.
- New bounded, source-extracted differential C harnesses compiled with GCC AddressSanitizer: SOAP dimensions (Patch210) returned `0 -> 1` on malformed input, SOAP DTD (Patch211) remained attached to the document after cleanup only in the candidate, CGI PATH_INFO (Patch214) returned NULL rather than forming an out-of-bounds pointer for short input.
- Positive/negative release-review gate logic tests passed. `PENDING` compatibility reviews are rejected.

## Externally reported — not independently reproduced here

- Unpatched vs RC6 three build variants (debug, optimized, ZTS), complete 12,315 PHPT, 13 patch-only behavior differences (five OOM, eight upload-progress), encrypted FTPS upload/download, CGI FastCGI test, mod_php 33,000 HTTP requests; previous RC6 user-provided report. The underlying external log ZIP/report were not available for this handoff.

## Unresolved and explicitly not claimed as passing

- Actual full PHP (not isolated functions) SOAP/CGI memory-safety differential using controlled instrumented binaries.
- Native RHEL7 RPM build, SELinux interaction, installed mod_php and actual application staging, RPM signatures and signed distribution.
- Actual target FTPS session and operations integration, application session/upload behavior, and rollback rehearsal.
- Approval or redesign for the 13 intentional behavioral divergences. Without signed organizational change control this is a **NO-GO production candidate**.

## Commands

```bash
bash tests/run-local-qualification.sh
BUILD_RC6=1 MODPHP_RC6=0 bash target-host-tests/run-rhel7-release-gates.sh
# Only on isolated, pre-authorized staging after RPM signing and installation:
RC6_COMPAT_REVIEW_FILE=/path/to/real-approved-review.json \
MODPHP_PROBE_URL=http://127.0.0.1/path/modphp-runtime-probe.php \
BUILD_RC6=0 MODPHP_RC6=1 REQUIRE_RPM_SIGNATURES=1 \
 bash target-host-tests/run-rhel7-release-gates.sh
```

**Governance:** The compatibility assessment template is not an approval. Test evidence must be inspected and human identity independently authenticated; don't weaken or restore the known unsafe prior behavior to make tests green.

#!/usr/bin/env bash
# Local source/tooling verification, NOT the RHEL7 RPM/Apache production gate.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON3_BIN="${PYTHON3_BIN:-python3}"
EVIDENCE="${RC6_EVIDENCE_DIR:-$PWD/rc6-local-qualification}"
mkdir -p "$EVIDENCE"
EVIDENCE="$(cd "$EVIDENCE" && pwd)"
for tool in "$PYTHON3_BIN" patch cc xml2-config sha256sum tar; do
  command -v "$tool" >/dev/null || { echo "NO-GO: missing local dependency $tool" >&2; exit 2; }
done
printf 'Local source qualification (NOT RHEL7 RPM certification)\n' | tee "$EVIDENCE/summary.txt"
( cd "$ROOT" && sha256sum -c SHA256SUMS ) > "$EVIDENCE/sha256-main.log"
( cd "$ROOT/rpm-kit" && sha256sum -c SHA256SUMS ) > "$EVIDENCE/sha256-rpm-kit.log"
"$PYTHON3_BIN" "$ROOT/tests/test-release-tooling.py" > "$EVIDENCE/release-tooling.log" 2>&1
"$PYTHON3_BIN" "$ROOT/tests/test-compatibility-gate.py" > "$EVIDENCE/compatibility-gate-schema.log" 2>&1
"$PYTHON3_BIN" "$ROOT/tests/test-production-gate-contract.py" > "$EVIDENCE/production-gate-contract.log" 2>&1
# Only mock/synthetic acceptance data is exercised here; no genuine signoff is created.
TMP="$(mktemp -d -t rc6_qualification_XXXXXXXX)"
trap 'rm -rf "$TMP"' EXIT
SOURCE_DIR="php-5.4.16-48.el7-securityrc6-source"
tar -xzf "$ROOT/php-5.4.16-48.el7-securityrc6-fully-patched-source.tar.gz" \
  --directory "$TMP" --wildcards "$SOURCE_DIR/*"
"$PYTHON3_BIN" "$ROOT/tests/test-fpm-rc6-source.py" "$TMP/$SOURCE_DIR" > "$EVIDENCE/fpm-source.log" 2>&1
"$PYTHON3_BIN" "$ROOT/tests/test-soap-cgi-source-differentials.py" "$TMP/$SOURCE_DIR" \
  --evidence "$EVIDENCE/soap-cgi-source-differentials" > "$EVIDENCE/differential.log" 2>&1
if [[ -n "${PHP54_CGI_BINARY:-}" ]]; then
  bash "$ROOT/tests/cgi-path-info-smoke.sh" "$PHP54_CGI_BINARY" > "$EVIDENCE/cgi-smoke.log" 2>&1
else
  echo 'NOT RUN CGI executable smoke: set PHP54_CGI_BINARY=/path/to/php-cgi' > "$EVIDENCE/cgi-smoke.log"
fi
for f in "$ROOT"/rpm-kit/build-rc.sh "$ROOT"/target-host-tests/run-rhel7-release-gates.sh \
         "$ROOT"/release-gate/staging-checks.sh "$ROOT"/release-gate/verify-build.sh; do
  bash -n "$f"
done
"$PYTHON3_BIN" -m py_compile "$ROOT/tests/test-soap-cgi-source-differentials.py" \
  "$ROOT/release-gate/verify-compatibility-assessment.py" "$ROOT/tests/test-compatibility-gate.py"
echo 'PASS both checksum manifests, release tooling, compatibility gate schema, FPM source,' | tee -a "$EVIDENCE/summary.txt"
echo 'PASS bounded AddressSanitizer SOAP/CGI source deltas, shell/Python syntax.' | tee -a "$EVIDENCE/summary.txt"
echo 'NEEDS RHEL7: actual RPM build/install/signatures, Apache mod_php and deployment policies.' | tee -a "$EVIDENCE/summary.txt"
echo 'NEEDS REVIEW: actual full-PHP memory-safety proof and 13 compatibility differences.' | tee -a "$EVIDENCE/summary.txt"

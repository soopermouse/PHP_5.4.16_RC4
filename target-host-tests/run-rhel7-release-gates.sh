#!/usr/bin/env bash
# RHEL7-only staging validation. Does not install RPMs, sign RPMs or change Apache.
# Usage:
#   BUILD_RC6=1 MODPHP_RC6=0 bash target-host-tests/run-rhel7-release-gates.sh
#   # after installing reviewed candidate RPMs on a disposable staging host:
#   BUILD_RC6=0 MODPHP_RC6=1 REQUIRE_RPM_SIGNATURES=1 bash target-host-tests/run-rhel7-release-gates.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOP="${RPM_TOPDIR:-$HOME/rpmbuild-php54-rc6}"
EVIDENCE="${RC6_EVIDENCE_DIR:-$PWD/rc6-target-evidence}"
mkdir -p "$EVIDENCE"
EVIDENCE="$(cd "$EVIDENCE" && pwd)"
[[ -f /etc/redhat-release ]] || { echo 'NO-GO: only RHEL7-family staging hosts supported' >&2; exit 2; }
grep -Eqi '(Red Hat Enterprise Linux|CentOS|Scientific Linux|Oracle Linux).*release 7\.' /etc/redhat-release || {
  echo 'NO-GO: only RHEL7-family staging hosts supported' >&2; exit 2;
}
[[ "$(id -u)" != 0 ]] || { echo 'NO-GO: run as dedicated non-root build/staging user' >&2; exit 2; }
[[ "$(uname -m)" == x86_64 ]] || { echo 'NO-GO: target architecture must be x86_64' >&2; exit 2; }
PYTHON3_BIN="${PYTHON3_BIN:-python3}"
for cmd in "$PYTHON3_BIN" rpm rpmbuild sha256sum gcc make; do
  command -v "$cmd" >/dev/null || { echo "NO-GO: missing dependency $cmd" >&2; exit 2; }
done
"$PYTHON3_BIN" -c 'import sys; assert sys.version_info >= (3, 6) and sys.version_info < (4, 0), "Python 3.6+ required"' || {
  echo 'NO-GO: Python 3.6 or newer (major 3) required; set PYTHON3_BIN if needed' >&2; exit 2;
}
REPORT="$EVIDENCE/GATE_SUMMARY.txt"
{
  echo 'PHP 5.4.16 / RHEL7 / RC6 target gate execution'
  date -u '+UTC %Y-%m-%dT%H:%M:%SZ'
  uname -a
  cat /etc/redhat-release
  gcc --version | head -1
  rpm --version
  "$PYTHON3_BIN" --version
  command -v httpd >/dev/null && httpd -v || echo "Apache httpd not installed on builder (normal if MODPHP_RC6=0)"
  echo 'Source candidate is not approved without all deployment-specific gates.'
} > "$REPORT"
run() {
  local label="$1"; shift
  echo "EXECUTE $label" | tee -a "$REPORT"
  if "$@" >"$EVIDENCE/$label.log" 2>&1; then
    echo "PASS $label" | tee -a "$REPORT"
  else
    local code=$?
    echo "FAIL $label (exit $code)" | tee -a "$REPORT"
    cat "$EVIDENCE/$label.log" >&2
    return "$code"
  fi
}
run source_checks bash -c 'cd "$1" && sha256sum -c SHA256SUMS && (cd rpm-kit && sha256sum -c SHA256SUMS)' _ "$ROOT"
if [[ "${BUILD_RC6:-0}" == 1 ]]; then
  run candidate_rpm_build bash "$ROOT/rpm-kit/build-rc.sh" "$ROOT/php-5.4.16-48.el7.src.rpm"
fi
[[ -d "$TOP/RPMS" && -d "$TOP/SRPMS" ]] || {
  echo 'NO-GO: missing RPM build outputs; set BUILD_RC6=1 on a clean build host' | tee -a "$REPORT"
  exit 2
}
run rpm_nevra_and_module bash "$ROOT/release-gate/verify-build.sh"
[[ -d "$TOP/BUILD/php-5.4.16" ]] || { echo 'NO-GO: patched source absent in RPM BUILD tree' | tee -a "$REPORT"; exit 2; }
run source_assertions "$PYTHON3_BIN" "$ROOT/release-gate/verify-source-rc6.py" "$TOP/BUILD/php-5.4.16"
# Isolated ASan source-extracted differential checks for Patch210/211/214.
# These do not replace independently reviewed full PHP memory-safety evidence.
command -v xml2-config >/dev/null || { echo 'NO-GO: libxml2-devel/xml2-config required for differential proof' | tee -a "$REPORT"; exit 2; }
run soap_cgi_source_differentials "$PYTHON3_BIN" "$ROOT/tests/test-soap-cgi-source-differentials.py" \
  "$TOP/BUILD/php-5.4.16" --evidence "$EVIDENCE/soap-cgi-differentials"
# The vendor spec configures/builds each SAPI in its own build-* subdirectory.
CGI="$TOP/BUILD/php-5.4.16/build-cgi/sapi/cgi/php-cgi"
FPM="$TOP/BUILD/php-5.4.16/build-fpm/sapi/fpm/php-fpm"
[[ -x "$CGI" ]] || { echo 'NO-GO: patched php-cgi executable absent' | tee -a "$REPORT"; exit 2; }
[[ -x "$FPM" ]] || { echo 'NO-GO: patched php-fpm executable absent' | tee -a "$REPORT"; exit 2; }
run cgi_runtime bash "$ROOT/tests/cgi-path-info-smoke.sh" "$CGI"
run fpm_source_unit "$PYTHON3_BIN" "$ROOT/tests/test-fpm-rc6-source.py" "$TOP/BUILD/php-5.4.16"
run fpm_runtime "$PYTHON3_BIN" "$ROOT/tests/test-fpm-rc6-runtime.py" "$FPM"
run fpm_all_fields "$PYTHON3_BIN" "$ROOT/tests/test-fpm-status-fields.py" "$FPM"
# Production qualification requires both isolated and deployment-configured Apache.
if [[ "${REQUIRE_RPM_SIGNATURES:-0}" == 1 && "${MODPHP_RC6:-0}" != 1 ]]; then
  echo 'NO-GO: production gate must run Apache mod_php (MODPHP_RC6=1)' | tee -a "$REPORT"
  exit 2
fi
if [[ "${MODPHP_RC6:-0}" == 1 ]]; then
  command -v httpd >/dev/null || { echo "NO-GO: Apache httpd missing on staging host" | tee -a "$REPORT"; exit 2; }
  run modphp_isolated_application "$PYTHON3_BIN" "$ROOT/target-host-tests/test-modphp-isolated.py"
  if [[ "${REQUIRE_RPM_SIGNATURES:-0}" == 1 ]]; then
    [[ -n "${MODPHP_PROBE_URL:-}" ]] || {
      echo 'NO-GO: MODPHP_PROBE_URL required for production-like Apache staging gate' | tee -a "$REPORT"
      exit 2
    }
    run modphp_deployed_staging bash "$ROOT/release-gate/staging-checks.sh"
  else
    echo 'NOT RUN deployment Apache probe: requires explicit MODPHP_PROBE_URL and staging authorization' | tee -a "$REPORT"
  fi
else
  echo 'NOT RUN modphp_isolated_application: install candidate RPM on isolated staging and rerun with MODPHP_RC6=1' | tee -a "$REPORT"
fi
# A production-gate invocation needs an independently completed risk review.
# A pre-populated PENDING template must never be interpreted as approval.
if [[ "${REQUIRE_RPM_SIGNATURES:-0}" == 1 ]]; then
  [[ -n "${RC6_COMPAT_REVIEW_FILE:-}" ]] || {
    echo 'NO-GO: RC6_COMPAT_REVIEW_FILE required for production gate (13 patch-only differences)' | tee -a "$REPORT"
    exit 2
  }
  run compatibility_risk_review "$PYTHON3_BIN" "$ROOT/release-gate/verify-compatibility-assessment.py" \
    "$RC6_COMPAT_REVIEW_FILE" --kit-root "$ROOT"
else
  echo 'NOT APPROVED: 13 compatibility differences require a recorded independent risk review.' | tee -a "$REPORT"
fi
if [[ "${REQUIRE_RPM_SIGNATURES:-0}" != 1 ]]; then
  echo 'NOT VERIFIED signatures: REQUIRE_RPM_SIGNATURES=1 is mandatory for production gate' | tee -a "$REPORT"
fi
# Production eligibility needs evidence beyond successful source/CI checks.
# These are external sign-off artifacts, never automatically generated by this kit.
if [[ "${REQUIRE_RPM_SIGNATURES:-0}" == 1 ]]; then
  for pair in \
    "FTPS_RHEL7_EVIDENCE_FILE:authenticated FTPS integration result from RHEL7" \
    "FULL_MEMORY_SAFETY_REVIEW_FILE:full PHP memory-safety review" \
    "PRODUCTION_CHANGE_APPROVAL_FILE:operations/security change approval"; do
    var="${pair%%:*}"
    label="${pair#*:}"
    path="${!var:-}"
    if [[ -z "$path" || ! -s "$path" ]]; then
      echo "NO-GO: missing $label; provide nonempty $var" | tee -a "$REPORT"
      exit 3
    fi
    case "$path" in
      "$ROOT"/*) echo "NO-GO: $var must be independent external evidence, not a kit template" | tee -a "$REPORT"; exit 3;;
    esac
    echo "SUPPLIED FOR INDEPENDENT REVIEW: $label ($path)" | tee -a "$REPORT"
  done
  echo 'ALL AUTOMATED TARGET GATES EXECUTED; external evidence files supplied but NOT independently authenticated by this script.' | tee -a "$REPORT"
else
  echo 'NOT VERIFIED RHEL7 encrypted FTPS, full PHP memory safety, 13 observed PHPT compatibility divergences (5 memory-limit + 8 upload progress), and production change approval.' | tee -a "$REPORT"
  echo 'STAGING/SOURCE CHECKS COMPLETE; NO PRODUCTION APPROVAL.' | tee -a "$REPORT"
fi

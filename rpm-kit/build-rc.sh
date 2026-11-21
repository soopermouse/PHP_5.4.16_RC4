#!/usr/bin/env bash
set -euo pipefail
# Run only inside an isolated RHEL7/x86_64 compatible build VM with trusted repos.
# Invoking this script does NOT install packages on production machines.
HERE="$(cd "$(dirname "$0")" && pwd)"
SRPM="${1:-$HERE/../php-5.4.16-48.el7.src.rpm}"
TOP="${RPM_TOPDIR:-$HOME/rpmbuild-php54-rc6}"
[[ -f "$SRPM" ]] || { echo "ERROR: source RPM not found: $SRPM" >&2; exit 1; }
[[ "$(id -u)" != 0 ]] || { echo 'NO-GO: run under a dedicated unprivileged build user' >&2; exit 2; }
[[ -f /etc/redhat-release ]] || { echo 'NO-GO: not a RHEL7-compatible build host' >&2; exit 2; }
grep -Eqi '(Red Hat Enterprise Linux|CentOS|Scientific Linux|Oracle Linux).*release 7\.' /etc/redhat-release || { echo 'NO-GO: expected RHEL 7 family; inspect /etc/redhat-release' >&2; exit 2; }
for exe in rpm rpmbuild gcc make sha256sum; do command -v "$exe" >/dev/null || { echo "NO-GO: missing $exe" >&2; exit 2; }; done
if [[ -n "${EXPECTED_SRPM_SHA256:-}" ]]; then
  actual="$(sha256sum "$SRPM" | awk '{print $1}')"
  [[ "$actual" == "$EXPECTED_SRPM_SHA256" ]] || { echo 'NO-GO: source RPM digest mismatch' >&2; exit 2; }
fi
for i in $(seq -w 1 16); do
  find "$HERE" -maxdepth 1 -name "${i}-*.patch" | grep -q . || { echo "NO-GO: missing patch $i" >&2; exit 2; }
done
grep -q 'securityrc6' "$HERE/php.spec" || { echo 'NO-GO: wrong candidate spec' >&2; exit 2; }
[[ ! -e "$TOP/SPECS/php.spec" ]] || { echo "NO-GO: existing RPM tree at $TOP; supply a clean RPM_TOPDIR" >&2; exit 2; }
mkdir -p "$TOP"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
LOG="$TOP/build-rc6.log"
{
  echo "Build host: $(uname -a)"
  cat /etc/redhat-release
  gcc --version | head -1
  rpm --version
  sha256sum "$SRPM"
  rpm -ivh --define "_topdir $TOP" "$SRPM"
  cp "$HERE/php.spec" "$TOP/SPECS/php.spec"
  cp "$HERE"/*.patch "$TOP/SOURCES/"
  rpmbuild -bp --define "_topdir $TOP" "$TOP/SPECS/php.spec"
  rpmbuild -bs --define "_topdir $TOP" "$TOP/SPECS/php.spec"
  rpmbuild -ba --define "_topdir $TOP" "$TOP/SPECS/php.spec"
  echo 'BUILD FINISHED: runtime testing and signoff remain mandatory.'
} 2>&1 | tee "$LOG"

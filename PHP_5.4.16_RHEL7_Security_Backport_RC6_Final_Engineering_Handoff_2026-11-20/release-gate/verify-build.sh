#!/usr/bin/env bash
set -euo pipefail
TOP="${RPM_TOPDIR:-$HOME/rpmbuild-php54-rc6}"
[[ -f /etc/redhat-release ]] || { echo 'NO-GO: not a RHEL-compatible host' >&2; exit 2; }
command -v rpm >/dev/null && command -v rpmbuild >/dev/null || { echo 'NO-GO: rpm tooling missing' >&2; exit 2; }
[[ -d "$TOP/RPMS" && -d "$TOP/SRPMS" ]] || { echo 'NO-GO: RPM output not found' >&2; exit 2; }
mapfile -t files < <(find "$TOP/RPMS" "$TOP/SRPMS" -type f -name '*.rpm' | sort)
[[ "${#files[@]}" -gt 1 ]] || { echo 'NO-GO: expected source and binary RPMs' >&2; exit 2; }
printf 'RPM count: %s\n' "${#files[@]}"
found_modphp=0
for f in "${files[@]}"; do
  meta="$(rpm -qp --qf '%{NAME} %{VERSION} %{RELEASE} %{ARCH}' "$f")" || exit 2
  echo "$meta :: $f"
  echo "$meta" | grep -Eq '^php([[:space:]]|-[^[:space:]]+ )' || { echo 'NO-GO: unrelated RPM in artifact tree' >&2; exit 2; }
  echo "$meta" | grep -q '5.4.16 48.*securityrc6' || { echo 'NO-GO: release mismatch' >&2; exit 2; }
  if [[ "$meta" == php\ 5.4.16* ]]; then
    rpm -qpl "$f" | grep -q '/httpd/modules/libphp5.so' && found_modphp=1 || true
  fi
  sha256sum "$f"
done
[[ "$found_modphp" == 1 ]] || { echo 'NO-GO: php RPM lacks mod_php shared library' >&2; exit 2; }
# Unsigned candidate RPMs are permitted for isolated staging ONLY; release requires verified signatures.
if [[ "${REQUIRE_RPM_SIGNATURES:-0}" == 1 ]]; then
  for f in "${files[@]}"; do
    sig="$(rpm -Kv "$f")" || { echo "NO-GO: invalid RPM signature $f" >&2; exit 2; }
    echo "$sig"
    echo "$sig" | grep -q 'pgp.*OK\|rsa.*OK\|RSA.*OK' || { echo "NO-GO: unsigned RPM $f" >&2; exit 2; }
  done
else
  echo 'STAGING ONLY: RPM signatures NOT approved. Set REQUIRE_RPM_SIGNATURES=1 for production gate.'
fi

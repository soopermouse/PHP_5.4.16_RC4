#!/usr/bin/env bash
set -euo pipefail
# Inventory plus explicit Apache-served PHP runtime verification.
# No configuration changes; the operator must manually deploy/remove the temporary probe.
echo '== Host =='; uname -a
[[ -f /etc/redhat-release ]] || { echo 'NO-GO: not a RHEL7 host' >&2; exit 2; }
grep -Eqi '(Red Hat Enterprise Linux|CentOS|Scientific Linux|Oracle Linux).*release 7\.' /etc/redhat-release || { echo 'NO-GO: expected a RHEL 7-family staging host' >&2; exit 2; }
command -v httpd >/dev/null || { echo 'NO-GO: Apache httpd is absent' >&2; exit 2; }
command -v rpm >/dev/null || { echo 'NO-GO: rpm is absent' >&2; exit 2; }
installed_candidate=$(rpm -q php --qf '%{NAME} %{VERSION} %{RELEASE}\n' 2>/dev/null) || {
  echo 'NO-GO: expected php RPM not installed' >&2; exit 2;
}
if ! printf '%s\n' "$installed_candidate" | grep -Eq '^php 5\.4\.16 48.*securityrc6'; then
  echo 'NO-GO: Apache server must have reviewed RC6 php RPM installed (not just PHP 5.4.16)' >&2; exit 2
fi
printf 'Installed candidate: %s\n' "$installed_candidate"

# The script must run on the actual staging server serving the PHP probe.
if ! httpd -M 2>&1 | grep -qi 'php5_module'; then
  echo 'NO-GO: mod_php module missing from Apache' >&2; exit 2
fi
if ! httpd -M 2>&1 | grep -qi 'mpm_prefork_module'; then
  echo 'NO-GO: expected prefork MPM for non-ZTS mod_php build' >&2; exit 2
fi
httpd -t

printf '\n== Installed PHP packages ==\n'; rpm -qa | grep -E '^php([^-]|-)' | sort || true
printf '\n== PHP CLI (NOT Apache) ==\n'; php -v || true
printf '\n== Apache build and modules ==\n'; httpd -V || true
httpd -M 2>&1 | grep -E '(mpm_|php|proxy_fcgi)' || true
printf '\n== Apache configuration syntax ==\n'; httpd -t
printf '\n== Service status ==\n'; systemctl status httpd --no-pager -l || true
printf '\n== CLI modules ==\n'; php -m || true
printf '\n== CLI settings (NOT Apache) ==\n'; php -i | grep -E '^(Server API|memory_limit|session.upload_progress.enabled|max_multipart_body_parts)' || true

# Do not accept CLI configuration as evidence of mod_php settings.
# Operator-provided URL must target loopback. Probe must be deployed under Apache,
# protected with Require local, and removed immediately after verification.
if [[ -z "${MODPHP_PROBE_URL:-}" ]]; then
  echo 'NO-GO: MODPHP_PROBE_URL not set; Apache PHP runtime not verified.' >&2
  echo 'Set MODPHP_PROBE_URL=http://127.0.0.1:PORT/path/modphp-runtime-probe.php (or localhost).' >&2
  exit 2
fi
if [[ ! "$MODPHP_PROBE_URL" =~ ^http://(127\.0\.0\.1|localhost|\[::1\])(:[0-9]{1,5})?/[A-Za-z0-9_./-]+\.php$ ]]; then
  echo 'NO-GO: probe URL must be plain HTTP, loopback-only, with a .php path and no query string.' >&2
  exit 2
fi
command -v curl >/dev/null || { echo 'NO-GO: curl not installed' >&2; exit 2; }
probe=$(curl --fail --silent --show-error --noproxy '*' --max-time 8 "$MODPHP_PROBE_URL") || {
  echo 'NO-GO: Apache probe request failed.' >&2; exit 2;
}
printf '\n== Apache-served PHP runtime (verified endpoint) ==\n%s\n' "$probe"
get_value() { printf '%s\n' "$probe" | sed -n "s/^$1=//p" | head -n 1; }
sapi=$(get_value sapi)
version=$(get_value php_version)
mem=$(get_value memory_limit)
parts=$(get_value max_multipart_body_parts)
progress=$(get_value 'session\.upload_progress\.enabled')
if [[ "$sapi" != 'apache2handler' ]]; then
  echo "NO-GO: Apache endpoint reports SAPI '$sapi', expected apache2handler." >&2; exit 2
fi
if [[ "$version" != 5.4.16* ]]; then
  echo "NO-GO: unexpected PHP version '$version' (expected 5.4.16-based RHEL package)." >&2; exit 2
fi
# An explicit Off setting returns an empty string from PHP 5.4 ini_get().
# Distinguish that legitimate empty value from an absent/malformed probe key.
if [[ -z "$mem" || -z "$parts" ]]; then
  echo 'NO-GO: Apache endpoint did not expose required memory/part directives.' >&2; exit 2
fi
if ! printf '%s\n' "$probe" | grep -q '^session[.]upload_progress[.]enabled='; then
  echo 'NO-GO: Apache endpoint omitted session.upload_progress.enabled.' >&2; exit 2
fi
if ! [[ "$parts" =~ ^-?[0-9]+$ ]]; then
  echo 'NO-GO: max_multipart_body_parts is not an integer.' >&2; exit 2
fi
# Patch200 deliberately disables the RFC1867 callback even when php.ini still
# reports its stock "On" / 1. Reject unknown values, but do not treat "On"
# as evidence that the callback was re-enabled. Runtime/source proof is separate.
case "${progress,,}" in
  ''|0|off|no|false|1|on|yes|true) ;;
  *) echo "NO-GO: unrecognized session.upload_progress.enabled value '$progress'" >&2; exit 2 ;;
esac
if [[ "${progress,,}" == 1 || "${progress,,}" == on || "${progress,,}" == yes || "${progress,,}" == true ]]; then
  echo 'NOTICE: Apache php.ini reports upload progress enabled by configuration; Patch200 overrides the callback in the patched source.'
  echo 'NOTICE: ini_get() alone cannot prove the feature is disabled; verify the installed patched module and optional runtime differential test.'
elif [[ -z "$progress" ]]; then
  echo 'NOTICE: PHP ini_get() returned an empty upload-progress value (e.g., php.ini Off); this is not evidence by itself that the callback is disabled.'
else
  echo 'NOTICE: upload-progress INI reports disabled; Patch200 behavior still requires patched-module verification.'
fi
handler=$(get_value 'session\.save_handler')
serializer=$(get_value 'session\.serialize_handler')
if [[ -z "$handler" || -z "$serializer" ]]; then
  echo 'NO-GO: missing Apache session save/serialize handler details.' >&2; exit 2
fi
if [[ "$handler" == 'files' ]]; then
  echo 'NOTICE: file-backed sessions require runtime regression tests for safe partial-write handling.'
fi
echo 'PASS: Apache request reports apache2handler and required runtime directives; upload-progress INI value recorded.' 
echo 'REVIEW REQUIRED: confirm directive values against approved staging configuration and installed RPM NEVRA.'
echo 'REMOVE THE TEMPORARY PHP PROBE FROM THE APACHE DOCUMENT ROOT NOW.'

#!/usr/bin/env bash
set -euo pipefail
CGI="${1:?Usage: bash cgi-path-info-smoke.sh /path/to/php-cgi}"
[[ -x "$CGI" ]] || { echo 'missing php-cgi binary' >&2; exit 2; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
printf '%s\n' '<?php echo "[" . (isset($_SERVER["PATH_INFO"]) ? $_SERVER["PATH_INFO"] : "<missing>") . "]"; ?>' > "$TMP/a.php"
for case_name in valid short empty; do
  case "$case_name" in
    valid) suffix=/b; path=/a/b; expect="[/b]";;
    short) suffix=/xxxxxxxxxxxxxxxx; path=/x; expect="[/x]";;
    empty) suffix=/xxxxxxxxxxxxxxxx; path=''; expect='[]';;
  esac
  set +e
  out="$(env -i PATH="${PATH:-/usr/bin:/bin}" REDIRECT_STATUS=1 REQUEST_METHOD=GET SCRIPT_FILENAME="$TMP/a.php$suffix" PATH_INFO="$path" "$CGI" -n -d cgi.fix_pathinfo=1 < /dev/null 2>&1)"
  code=$?
  set -e
  [[ "$code" -eq 0 ]] || { printf 'FAIL %s exit=%d\n%s\n' "$case_name" "$code" "$out" >&2; exit 1; }
  if [[ "$out" == *$'\r\n\r\n'* ]]; then
    body="${out#*$'\r\n\r\n'}"
  elif [[ "$out" == *$'\n\n'* ]]; then
    body="${out#*$'\n\n'}"
  else
    echo "FAIL $case_name: missing CGI HTTP headers/body delimiter" >&2; exit 1
  fi
  body="${body//$'\r'/}"
  [[ "$body" == "$expect" ]] || { printf 'FAIL %s expected [%s] got [%s] output:\n%s\n' "$case_name" "$expect" "$body" "$out" >&2; exit 1; }
  printf 'PASS %s\n' "$case_name"
done

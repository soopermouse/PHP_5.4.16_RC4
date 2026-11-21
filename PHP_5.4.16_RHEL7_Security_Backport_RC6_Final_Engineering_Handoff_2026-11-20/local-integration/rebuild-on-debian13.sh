#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVE="$ROOT/php-5.4.16-48.el7-securityrc6-fully-patched-source.tar.gz"
OUT="${1:-$ROOT/local-rebuild}"
[[ ! -e "$OUT" ]] || { echo "Refusing to overwrite $OUT" >&2; exit 2; }
mkdir -p "$OUT"
tar -xzf "$ARCHIVE" -C "$OUT"
cd "$OUT/php-5.4.16-48.el7-securityrc6-source"
./configure --disable-all --enable-cli --enable-cgi --enable-fpm --enable-soap --enable-libxml --with-libxml-dir=/usr --without-pear
make -j"${JOBS:-2}"
for f in sapi/cli/php sapi/cgi/php-cgi sapi/fpm/php-fpm; do
  test -x "$f" || { echo "FAIL $f missing" >&2; exit 1; }
done
sapi/cli/php -v | head -3
echo "SUCCESS: Debian source rebuild finished in $PWD. This does NOT produce a RHEL7-compatible RPM."

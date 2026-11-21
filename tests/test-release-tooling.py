#!/usr/bin/env python3
"""Self-contained local checks for the RHEL7 release-gate fixes (Python 3.6 syntax)."""
import ast
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
modphp = (ROOT / 'target-host-tests/test-modphp-isolated.py').read_text(encoding='utf-8')
runner = (ROOT / 'target-host-tests/run-rhel7-release-gates.sh').read_text(encoding='utf-8')
staging = (ROOT / 'release-gate/staging-checks.sh').read_text(encoding='utf-8')
assert (ROOT / 'rpm-kit/SHA256SUMS').is_file(), 'RPM checksum manifest missing'
for subdir in (ROOT, ROOT / 'rpm-kit'):
    result = subprocess.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=str(subdir),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    assert result.returncode == 0, ('checksum gate failed', str(subdir), result.stderr)
assert "sha256sum -c SHA256SUMS && (cd rpm-kit && sha256sum -c SHA256SUMS)" in runner
assert 'authz_host' in re.search(r"modules = .*?conf\.write_text", modphp, re.S).group(0)
assert 'module_lines(str(httpd), module_dir, name)' in modphp
assert "max_multipart_body_parts 2" in modphp and "limited.get('third') != 'missing'" in modphp
assert 'build-cgi/sapi/cgi/php-cgi' in runner
assert 'build-fpm/sapi/fpm/php-fpm' in runner
assert 'tests/test-fpm-rc6-source.py' in runner
assert 'PYTHON3_BIN' in runner
# Full suite revealed 13, not 12; fail the tooling test on stale gate metadata.
assert '13 observed PHPT compatibility divergences' in runner
assert '5 memory-limit + 8 upload progress' in runner
assert '13' in (ROOT / 'FULL_SUITE_VERIFICATION_HANDOFF_2026-11-20.md').read_text(encoding='utf-8')
assert 'python3.6' not in runner  # not hardwired to a missing binary
for file in (ROOT/'target-host-tests').glob('*.py'):
    if sys.version_info >= (3, 8):
        ast.parse(file.read_text(encoding='utf-8'), filename=str(file), feature_version=(3, 6))
    else:
        ast.parse(file.read_text(encoding='utf-8'), filename=str(file))
for file in (ROOT/'tests').glob('*.py'):
    if sys.version_info >= (3, 8):
        ast.parse(file.read_text(encoding='utf-8'), filename=str(file), feature_version=(3, 6))
    else:
        ast.parse(file.read_text(encoding='utf-8'), filename=str(file))
# subprocess.run(text=...) and capture_output=... were introduced in Python 3.7.
for file in (ROOT/'target-host-tests').glob('*.py'):
    source = file.read_text(encoding='utf-8')
    assert not re.search(r'\b(text\s*=\s*True|capture_output\s*=\s*True)', source), str(file)
for file in (ROOT/'tests').glob('*.py'):
    source = file.read_text(encoding='utf-8')
    assert not re.search(r'\b(text\s*=\s*True|capture_output\s*=\s*True)', source), str(file)
# Run the exact upload-progress case block on several php.ini forms, not a
# guessed simulation of bash's case-insensitive parameter expansion.
start = staging.index('case "${progress,,}" in')
end = staging.index('\nfi\n', start) + len('\nfi\n')
block = staging[start:end]
assert "grep -q '^session[.]upload_progress[.]enabled='" in staging
assert '[[ -z "$mem" || -z "$parts" ]]' in staging
for value in ('', '0', 'Off', 'off', '1', 'On', 'on', 'yes', 'no', 'TRUE', 'False'):
    proc = subprocess.run(['bash', '-c', 'progress="$1"\n' + block, '_', value],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert proc.returncode == 0, ('valid setting rejected', value, proc.stderr)
for value in ('garbage', 'maybe'):
    proc = subprocess.run(['bash', '-c', 'progress="$1"\n' + block, '_', value],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert proc.returncode != 0, ('unrecognized setting accepted', value)
# Source of truth for empty-vs-missing check is the actual staging shell block.
start = staging.index('if [[ -z "$mem" || -z "$parts" ]]')
end = staging.index('if ! [[ "$parts" =~', start)
required_block = staging[start:end]
for present in (True, False):
    payload = ('session.upload_progress.enabled=\n' if present else 'unrelated.directive=\n')
    result = subprocess.run(['bash', '-c', 'mem=128M; parts=2; probe="$1"\n' + required_block, '_', payload],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert (result.returncode == 0) == present, ('empty vs missing failed', present, result.stderr)
print('PASS: checksum gate includes both SHA256SUMS files, both verified')
print('PASS: empty Off value accepted, absent directive rejected')
print('PASS: four reported release-script defects have local logic/compatibility checks')
print('PASS: Python 3.6 syntax grammar and subprocess API compatibility scan')
print('PASS: php.ini progress empty/0/1/On/Off variants accepted; invalid values rejected')
print('NOTE: external Python 3.6.8 tested on Ubuntu 24.04; native RHEL7 RPM/Apache remains open')

#!/usr/bin/env python3
"""Assert release runner does not silently certify an unreviewed production build."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
script = (root / 'target-host-tests/run-rhel7-release-gates.sh').read_text(encoding='utf-8')
for name in ('FTPS_RHEL7_EVIDENCE_FILE', 'FULL_MEMORY_SAFETY_REVIEW_FILE',
             'PRODUCTION_CHANGE_APPROVAL_FILE', 'RC6_COMPAT_REVIEW_FILE'):
    assert name in script, name
assert 'NO-GO: missing $label' in script
assert 'independent external evidence' in script
assert '13 observed PHPT compatibility divergences' in script
assert 'ALL AUTOMATED TARGET GATES EXECUTED' in script
assert 'STAGING/SOURCE CHECKS COMPLETE; NO PRODUCTION APPROVAL' in script
result = subprocess.run(['bash', '-n', str(root / 'target-host-tests/run-rhel7-release-gates.sh')],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
assert result.returncode == 0, result.stderr
print('PASS: production mode requires independent FTPS, memory-safety, compatibility, and approval records')
print('PASS: staging mode cannot print production approval')
print('LIMIT: actual production gate must run on an authorized RHEL7 host')

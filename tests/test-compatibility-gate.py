#!/usr/bin/env python3
"""Positive/negative contract tests; DOES NOT create a genuine approval."""
from pathlib import Path
import datetime
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / 'release-gate/verify-compatibility-assessment.py'
TEMPLATE = ROOT / 'release-gate/compatibility-assessment.template.json'

def execute(path):
    return subprocess.run([sys.executable, str(GATE), str(path)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)

with tempfile.TemporaryDirectory(prefix='rc6_compatreview_test_') as t:
    path = Path(t) / 'review.json'
    template = json.loads(TEMPLATE.read_text())
    path.write_text(json.dumps(template))
    assert execute(path).returncode != 0, 'PENDING review incorrectly accepted'
    for key, value in [
        ('change_ticket','SEC-TEST-FAKE-123'), ('risk_owner','QA TEST ONLY'),
        ('independent_approver','DIFFERENT QA TESTER'),
        ('review_date_utc',datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')),
        ('application_inventory_reference','dummy://test/applications'),
        ('production_rollout_plan_reference','dummy://test/rollout'),
        ('rollback_plan_reference','dummy://test/rollback'),
        ('approver_comment','Synthetic exercise for validator, not a real approval.')]:
        template[key] = value
    template['decision']='accepted_with_conditions'
    for item in template['categories']:
        item['decision']='accepted_with_conditions'
        item['impacted_integrations']=['synthetic test app; no real inventory']
        item['reviewed_test_ids']=['synthetic local test; not real review']
    path.write_text(json.dumps(template))
    assert execute(path).returncode == 0, 'complete synthetic review failed validator'
    template['categories'][0]['observed_tests']=4
    path.write_text(json.dumps(template))
    assert execute(path).returncode != 0, 'incorrect count accepted'
    template['categories'][0]['observed_tests']=5
    template['rpm_kit_sha256s_manifest_digest']='0'*64
    path.write_text(json.dumps(template))
    assert execute(path).returncode != 0, 'mismatched patch kit accepted'
    print('PASS: pending review denied; synthetic schema complete accepted for test only; incorrect count and kit denied')

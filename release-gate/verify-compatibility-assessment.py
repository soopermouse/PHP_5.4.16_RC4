#!/usr/bin/env python3
"""Reject unreviewed or unsigned-in-process RC6 compatibility exceptions.

Validates completeness of an operator-maintained, independent risk review.
This does not verify the human identity or a cryptographic signature; the
production release workflow must authenticate approvals independently.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys

REQUIRED_DECISION = 'accepted_with_conditions'
EXPECTED = {'allocator-memory-limit': 5, 'session-upload-progress': 8}


def check(review, kit):
    errors = []
    manifest = Path(kit) / 'rpm-kit' / 'SHA256SUMS'
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if review.get('rpm_kit_sha256s_manifest_digest') != digest:
        errors.append('Review does not identify this exact RPM patch kit')
    if review.get('release') != 'PHP 5.4.16 for RHEL 7 Security Backport RC6':
        errors.append('Wrong candidate identity')
    if review.get('test_population') != 12315 or review.get('observed_patch_only_differences') != 13:
        errors.append('Full 12,315 suite / 13 differences not acknowledged')
    for key in ('change_ticket', 'risk_owner', 'independent_approver',
                'review_date_utc', 'application_inventory_reference',
                'production_rollout_plan_reference', 'rollback_plan_reference',
                'approver_comment'):
        if not isinstance(review.get(key), str) or not review[key].strip():
            errors.append('Missing ' + key)
    if review.get('risk_owner') and review.get('risk_owner') == review.get('independent_approver'):
        errors.append('Independent approver must differ from risk owner')
    if review.get('decision') != REQUIRED_DECISION:
        errors.append('Overall decision must be accepted_with_conditions, not pending')
    try:
        date = datetime.datetime.strptime(review.get('review_date_utc', ''), '%Y-%m-%d')
        if date.date() > datetime.datetime.now(datetime.timezone.utc).date():
            errors.append('Approval date cannot be in the future')
    except (ValueError, TypeError):
        errors.append('Review date must be YYYY-MM-DD UTC')
    cats = review.get('categories')
    if not isinstance(cats, list) or len(cats) != 2:
        errors.append('Exactly two compatibility categories required')
        cats = []
    observed = set()
    for item in cats:
        if not isinstance(item, dict):
            errors.append('Invalid compatibility category')
            continue
        ident = item.get('id')
        observed.add(ident)
        if ident not in EXPECTED or item.get('observed_tests') != EXPECTED.get(ident):
            errors.append('Unrecognized or incorrect category/count: ' + str(ident))
        if item.get('decision') != REQUIRED_DECISION:
            errors.append('Category not accepted: ' + str(ident))
        if not isinstance(item.get('mitigation'), str) or len(item['mitigation'].strip()) < 30:
            errors.append('Missing mitigation: ' + str(ident))
        if not isinstance(item.get('impacted_integrations'), list) or not item['impacted_integrations']:
            errors.append('No actual application inventory/impact recorded: ' + str(ident))
        if not isinstance(item.get('reviewed_test_ids'), list) or not item['reviewed_test_ids']:
            errors.append('No test IDs/evidence recorded: ' + str(ident))
    if observed != set(EXPECTED):
        errors.append('Missing a required category or duplicate category')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review_json')
    parser.add_argument('--kit-root', default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()
    try:
        review = json.loads(Path(args.review_json).read_text(encoding='utf-8'))
        problems = check(review, args.kit_root)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('NO-GO: ' + str(exc), file=sys.stderr)
        return 2
    if problems:
        for problem in problems:
            print('NO-GO: ' + problem, file=sys.stderr)
        return 2
    print('PASS: Compatibility assessment completeness for 13 differences')
    print('IMPORTANT: Approver identity and ticket must also be authenticated outside this script')
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Bindings shared by the local runner and CI; no network or model execution."""
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def suite_identity(kit):
    kit = Path(kit)
    files = set()
    for name in ['codex-template', 'codex-optional', 'scripts', 'licenses', '.github/workflows', 'tests']:
        for p in (kit/name).rglob('*'):
            if not p.is_file() or p.is_symlink():
                continue
            rel = p.relative_to(kit)
            if '__pycache__' in rel.parts or p.suffix == '.pyc':
                continue
            if str(rel).startswith(('tests/e2e/results/', 'tests/workflow/review-evidence/')):
                continue
            files.add(rel)
    for name in ['install.sh', 'vendored.tsv', 'THIRD_PARTY_NOTICES.md']:
        files.add(Path(name))
    catalog = json.loads((kit/'tests/workflow/cases.json').read_text())
    for case in catalog:
        files.add(Path('tests/e2e/results')/case['archive'])
    files.add(Path('tests/e2e/results/2026-10-24/oracle/regressions.rs'))
    hashes = {str(p): hashlib.sha256((kit/p).read_bytes()).hexdigest() for p in sorted(files)}
    return {'schema': 1, 'fingerprint': digest(hashes), 'files': hashes}


def binding(root):
    root = Path(root)
    suite = json.loads((root/'suite-identity.json').read_text())
    inputs = json.loads((root/'inputs.json').read_text())
    return {'schema': 1, 'suite': suite['fingerprint'], 'inputs': digest(inputs)}


def diagnostics_complete(root):
    root = Path(root)
    try:
        records = json.loads((root/'diagnostics.json').read_text())
        marker = json.loads((root/'diagnostics-complete.json').read_text())
        return (marker.get('completed') is True and isinstance(records, list) and len(records) > 0
                and marker.get('checks') == len(records)
                and len({r['name'] for r in records}) == len(records)
                and all(r.get('pass') is True for r in records))
    except (OSError, ValueError, KeyError, TypeError):
        return False

#!/usr/bin/env python3
"""Package inputs or import explicitly supplied review evidence, failing closed."""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tarfile
from support import binding, diagnostics_complete, suite_identity

KIT = pathlib.Path(__file__).resolve().parents[3]
RUNNER = KIT/'tests/run-workflow-regressions.py'


def assess(root):
    return subprocess.run([sys.executable,str(RUNNER),str(root),'--phase','assess'],cwd=KIT).returncode


def check_identity(root):
    stored=json.loads((root/'suite-identity.json').read_text())
    if stored != suite_identity(KIT):
        raise ValueError('Run belongs to a different workflow version. Prepare a fresh run.')


def files(root):
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Evidence cannot contain symlinks: '+str(path))
        if any(p=='target' or p.endswith('-target') or p in ['.git','.code-review-graph','__pycache__'] for p in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def export(root, destination=None):
    check_identity(root)
    if not diagnostics_complete(root) or assess(root) != 0:
        raise ValueError('Export requires complete diagnostics, all reports and semantic assessment.')
    target=destination or KIT/'tests/workflow/review-evidence'/binding(root)['suite']
    target.mkdir(parents=True,exist_ok=False)
    # Only evidence is transported: never replace cases or diagnostic results in CI.
    for name in ['reviews','logs']:
        for source in files(root/name):
            relative=source.relative_to(root); output=target/relative
            output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,output)
    shutil.copyfile(root/'semantic-assessment.json',target/'semantic-assessment.json')
    hashes={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files(target)}
    (target/'bundle.json').write_text(json.dumps({'binding':binding(root),'files':hashes},indent=2))
    print(target)


def import_evidence(root, evidence):
    manifest=json.loads((evidence/'bundle.json').read_text())
    if manifest.get('binding') != binding(root):
        raise ValueError('Stale review evidence: workflow or exact inputs differ.')
    hashes=manifest.get('files',{})
    if not hashes: raise ValueError('Empty evidence bundle')
    for relative,expected in hashes.items():
        rel=pathlib.Path(relative);source=evidence/rel
        if (rel.is_absolute() or '..' in rel.parts or
            not (rel.parts[0] in ['reviews','logs'] or relative=='semantic-assessment.json') or
            source.is_symlink() or not source.resolve().is_relative_to(evidence.resolve()) or not source.is_file()):
            raise ValueError('Invalid evidence path: '+relative)
        if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
            raise ValueError('Evidence hash mismatch: '+relative)
    # Avoid mixing partial or old reports with the imported set.
    if any((root/'reviews').rglob('report.md')) or (root/'semantic-assessment.json').exists():
        raise ValueError('Review destination is not empty; use the untouched CI input artifact.')
    for relative in hashes:
        target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(evidence/relative,target)


def gate(root, evidence=None):
    check_identity(root)
    if not diagnostics_complete(root):
        raise ValueError('Automatic diagnostics failed or did not finish; review gate cannot pass.')
    evidence=evidence or KIT/'tests/workflow/review-evidence'/binding(root)['suite']
    if not (evidence/'bundle.json').is_file():
        assess(root)
        print('Fresh review evidence MISSING. Automatic PASS is not workflow PASS.',file=sys.stderr)
        return 2
    import_evidence(root,evidence)
    return assess(root)


def pack(root, output):
    output.parent.mkdir(parents=True,exist_ok=True)
    def include(info):
        if any(p=='target' or p.endswith('-target') or p in ['.code-review-graph','__pycache__'] for p in pathlib.Path(info.name).parts):
            return None
        return info
    with tarfile.open(output,'w:gz') as archive:
        archive.add(root,arcname='run',filter=include)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['pack','export','gate'])
    p.add_argument('root',type=pathlib.Path)
    p.add_argument('--destination',type=pathlib.Path)
    args=p.parse_args()
    try:
        root=args.root.resolve()
        if args.action=='pack':
            if args.destination is None: p.error('pack requires --destination')
            pack(root,args.destination.resolve())
        elif args.action=='export': export(root,args.destination)
        else: raise SystemExit(gate(root,args.destination))
    except (ValueError,OSError,KeyError,TypeError) as error:
        print('Review gate FAILED: '+str(error),file=sys.stderr)
        raise SystemExit(1)

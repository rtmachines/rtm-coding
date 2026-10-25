#!/usr/bin/env python3
"""Replay the frozen escalation cases with newly supplied evidence."""
import pathlib, shutil, subprocess, sys, tarfile
kit = pathlib.Path(__file__).resolve().parents[2]
root = pathlib.Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=False)
fixture = kit / 'tests/e2e/closure-fixture'
with tarfile.open(kit / 'tests/e2e/results/2026-10-24-escalation/reviewed-repositories.tar.gz') as archive:
    archive.extractall(root, filter='data')
shutil.copytree(root/'r2', root/'r3')
def run(repo,*args):
    subprocess.run(args,cwd=repo,check=True,stdout=subprocess.DEVNULL)
for name in ['r1','r2','r3']:
    repo=root/name
    run(repo,'git','tag','escalated-input')
    run(repo,'bash',str(kit/'install.sh'),'--force','--no-ci',str(repo))
    with (repo/'REVIEW.md').open('a') as f:
        f.write("\n## Project policy\nUse RUST_GATE_FEATURES='' for ordinary gates. Run feature model separately.\nModel exploration may run to completion. Use an external process watchdog of 120 seconds; reaching it is not evidence of completion. Do not install dependencies or access external services.\n")
    if name=='r1':
        p=repo/'tests/publication_model.rs'
        s=p.read_text().replace('builder.max_permutations = Some(2); // Loom starts at 1; allow one execution.','builder.max_permutations = None;')
        s=s.replace('    builder.check(|| {','    builder.checkpoint_file = None;\n    let executions = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));\n    let seen = executions.clone();\n    builder.check(move || {\n        seen.fetch_add(1, std::sync::atomic::Ordering::SeqCst);')
        s=s.replace('    });\n}', '    });\n    let count = executions.load(std::sync::atomic::Ordering::SeqCst);\n    println!("completed model executions: {count}");\n    assert!(count > 1);\n}')
        p.write_text(s)
    else:
        shutil.copyfile(fixture/'VENDOR-CONTRACT.md', repo/'VENDOR-CONTRACT.md')
        (repo/'REQUIREMENTS.md').write_text('The deployment for this local example is Acme reference provider 1.0 as defined in VENDOR-CONTRACT.md. On timeout return the request for retry without duplicating the provider ledger effect, using the same request ID and namespace. Verify the exact provider implementation and execute the contract acceptance scenarios. Scope is the local reference provider, not a real proprietary SDK or crash-durable remote service.\n')
        if name=='r2':
            with (repo/'src/lib.rs').open('a') as f: f.write('\npub mod acme;\n')
            shutil.copyfile(fixture/'acme.rs',repo/'src/acme.rs')
            shutil.copyfile(fixture/'vendor_tests.rs',repo/'tests/vendor_tests.rs')
            shutil.copyfile(fixture/'vendor_model.rs',repo/'tests/vendor_model.rs')
    run(repo,'cargo','fmt','--all')
    run(repo,'git','add','.')
    run(repo,'git','commit','-qm','Supply updated validation resources')
print(root)

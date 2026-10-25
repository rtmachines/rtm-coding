#!/usr/bin/env python3
"""Independent behavioral checks; creates exact copies outside reviewed repos."""
import pathlib, shutil, subprocess, sys
root=pathlib.Path(sys.argv[1]).resolve()
out=root/'oracle'
out.mkdir(exist_ok=False)
for case in ['r1','r2']:
    probe=out/case
    probe.mkdir()
    for file in ['Cargo.toml','Cargo.lock']:
        shutil.copyfile(root/case/file,probe/file)
    for directory in ['src','tests']:
        shutil.copytree(root/case/directory,probe/directory)

def check(case,label,args,expect_failure=False):
    result=subprocess.run(['timeout','120','cargo','test','--offline','--locked',*args],cwd=out/case,capture_output=True,text=True)
    (out/f'{label}.log').write_text(result.stdout+result.stderr)
    (out/f'{label}.status').write_text(str(result.returncode)+'\n')
    if expect_failure:
        assert result.returncode==101 and 'test result: FAILED' in result.stdout, result.stderr
    else:
        assert result.returncode==0,result.stderr
    return result.stdout
model=check('r1','publication',['--features','model','--test','publication_model','--','--nocapture'])
assert 'completed model executions:' in model
check('r2','provider',['--test','vendor_tests'])
check('r2','provider-model',['--features','model','--test','vendor_model'])
# Negative control: make duplicate IDs repeat the effect. Do not touch review inputs.
p=out/'r2/src/acme.rs'
source=p.read_text()
assert 'if state.committed.insert(request) {' in source
p.write_text(source.replace('if state.committed.insert(request) {','state.committed.insert(request);\n        {'))
check('r2','duplicate-effect-mutation',['--test','vendor_tests'],True)
check('r2','duplicate-effect-model-mutation',['--features','model','--test','vendor_model'],True)
(out/'r2-mutation.patch').write_text(subprocess.run(['diff','-u',str(root/'r2/src/acme.rs'),str(p)],capture_output=True,text=True).stdout)
p.write_text(source)
print('Full models and provider tests pass; both suites reject duplicate-effect mutation.')

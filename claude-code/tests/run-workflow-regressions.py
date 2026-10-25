#!/usr/bin/env python3
"""Deterministic oracles + fresh review acceptance. No LLM result is fabricated."""
import argparse, hashlib, json, os, pathlib, re, shutil, subprocess, tarfile, time, sys
KIT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT/'tests/workflow/ci'))
from support import suite_identity, diagnostics_complete, git_input_files
MIRI_TOOLCHAIN = os.environ.get('MIRI_TOOLCHAIN', 'nightly')
CATALOG = json.loads((KIT/'tests/workflow/cases.json').read_text())
ENV = dict(os.environ, CARGO_NET_OFFLINE='true', CARGO_TERM_COLOR='never')
for key in list(ENV):
    if key.startswith('LOOM_') or key in ['MIRIFLAGS','CARGO_TARGET_DIR','RUSTFLAGS']:
        ENV.pop(key)

def shell(args, cwd, timeout=240, env=None):
    return subprocess.run(args, cwd=cwd, env=env or ENV, capture_output=True, text=True, timeout=timeout)

def setup(args, cwd):
    result=shell(args,cwd)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    return result.stdout

def snapshot(repo, runtime='codex'):
    if runtime == 'claude':
        files = git_input_files(repo)
    elif runtime == 'codex':
        files={}
        for folder in ['src','tests']:
            for p in sorted((repo/folder).rglob('*')):
                if p.is_file(): files[str(p.relative_to(repo))]=hashlib.sha256(p.read_bytes()).hexdigest()
    else:
        raise ValueError(f'Unknown review runtime: {runtime}')
    return {'files':files,'status':setup(['git','status','--porcelain'],repo),'head':setup(['git','rev-parse','HEAD'],repo).strip()}

def fixture_commit(repo, message):
    env=dict(ENV, GIT_AUTHOR_DATE='2000-01-01T00:00:00Z', GIT_COMMITTER_DATE='2000-01-01T00:00:00Z')
    result=shell(['git','-c','commit.gpgsign=false','commit','--allow-empty','-qm',message],repo,env=env)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)

def prepare(root, runtime='codex'):
    if runtime not in ('codex', 'claude'):
        raise ValueError(f'Unknown review runtime: {runtime}')
    root.mkdir(parents=True,exist_ok=False)
    (root/'cases').mkdir(); (root/'logs').mkdir(); (root/'reviews').mkdir()
    pins={}
    for case in CATALOG:
        archive=KIT/'tests/e2e/results'/case['archive']
        pins[case['archive']]=hashlib.sha256(archive.read_bytes()).hexdigest()
        scratch=root/'extract'; scratch.mkdir()
        with tarfile.open(archive) as tar:
            prefix=case['member']+'/'
            tar.extractall(scratch,members=[m for m in tar if m.name==case['member'] or m.name.startswith(prefix)],filter='data')
        repo=root/'cases'/case['id']; shutil.move(scratch/case['member'],repo); shutil.rmtree(scratch)
        setup(['git','config','user.name','Regression Fixture'],repo)
        setup(['git','config','user.email','fixture@example.invalid'],repo)
        if case['id']=='02':
            setup(['git','reset','--hard','baseline'],repo)
            with (repo/'src/lib.rs').open('a') as f: f.write('\nmod limits;\npub use limits::parse_limit;\n')
            (repo/'src/limits.rs').write_text('pub fn parse_limit(raw: &str) -> Option<u16> { raw.parse().ok() }\n')
            fixture_paths = ['src']
            if runtime == 'claude':
                (repo/'tests').mkdir(exist_ok=True)
                shutil.copyfile(KIT/'tests/e2e/results/2026-10-24/oracle/regressions.rs', repo/'tests/regressions.rs')
                fixture_paths.append('tests/regressions.rs')
            setup(['cargo','fmt','--all'],repo)
            setup(['git','add',*fixture_paths],repo); fixture_commit(repo,'Correct parse_limit implementation')
        old=(repo/'REVIEW.md').read_text()
        match=re.search(r'^## .*policy.*$',old,re.M|re.I)
        policy=old[match.start():] if match else ''
        runtime_args = ['--claude'] if runtime == 'claude' else []
        setup(['bash',str(KIT/'install.sh'),*runtime_args,'--force','--no-ci',str(repo)],KIT)
        if runtime == 'claude' and case['id'] in ['01', '02']:
            with (repo/'REQUIREMENTS.md').open('a') as f:
                f.write('\nFor parse_limit, valid input follows Rust u16::from_str, including an optional leading +.\n')
        with (repo/'REVIEW.md').open('a') as f:
            f.write('\n'+policy+'\nRun diagnostics offline using the existing toolchains and advisory database. Record this freshness limitation. Use equivalent offline gate commands if necessary. Do not install dependencies or access external services.\n')
        with (repo/'.gitignore').open('a') as f: f.write('\n/.code-review-graph/\n')
        instructions = ['.claude', 'CLAUDE.md'] if runtime == 'claude' else ['.agents', 'AGENTS.md']
        setup(['git','add',*instructions,'REVIEW.md','.gitignore'],repo)
        fixture_commit(repo,'Install current workflow for regression review')
    (root/'suite-identity.json').write_text(json.dumps(suite_identity(KIT, runtime),indent=2))
    (root/'inputs.json').write_text(json.dumps({c['id']:snapshot(root/'cases'/c['id'], runtime) for c in CATALOG},indent=2))
    (root/'archive-hashes.json').write_text(json.dumps(pins,indent=2))
    requests=[]
    for case in CATALOG:
        repo=root/'cases'/case['id']; out=root/'reviews'/case['id']
        instruction_file = 'CLAUDE.md' if runtime == 'claude' else 'AGENTS.md'
        requests.append({'id':case['id'],'repo':str(repo),'output':str(out),'request':f'Perform full independent review of {repo} against origin/main including dirty/untracked files. Follow {instruction_file}, REVIEW.md, REQUIREMENTS.md and installed rust-pr-review skill. Execute required diagnostics offline. Do not edit the reviewed tree. Exact-source probes outside it are permitted in {out}. Save report.md, logs, commands, status and source hashes in {out}. Use graph-first and Rust LSP; validate the report. Do not inspect sibling cases, oracle, catalog, historical reports or expected outcomes.'})
        if runtime == 'claude':
            requests[-1]['request'] += ' Return the complete report as your final response, exactly matching report.md, so the native CLI result can be bound to the saved report.'
    (root/'review-requests.json').write_text(json.dumps(requests,indent=2))
    print('Prepared 11 review inputs; requests in '+str(root/'review-requests.json'),flush=True)

class Run:
    def __init__(self,root):
        self.root=root; self.results=[]
    def check(self,name,args,cwd,code=0,contains=(),env=None,timeout=180):
        start=time.monotonic(); output=''; actual=None
        try:
            p=shell(args,cwd,timeout,env); actual=p.returncode; output=p.stdout+p.stderr
            ok=actual==code and all(s in output for s in contains)
        except subprocess.TimeoutExpired as e:
            output='WATCHDOG TIMEOUT: not a reproduced defect\n'+str(e); ok=False
        except Exception as e:
            output=repr(e); ok=False
        (self.root/'logs'/f'{name}.log').write_text(output)
        item={'name':name,'pass':ok,'expected_exit':code,'exit':actual,'seconds':round(time.monotonic()-start,3),'command':args,'cwd':str(cwd),'required_signals':list(contains)}
        self.results.append(item)
        (self.root/'diagnostics.json').write_text(json.dumps(self.results,indent=2))
        print(('PASS ' if ok else 'FAIL ')+name,flush=True)
        return ok
    def copy(self,case,label,tests=None):
        src=self.root/'cases'/case; dst=self.root/'probes'/label; dst.mkdir(parents=True)
        for name in ['Cargo.toml','Cargo.lock']: shutil.copyfile(src/name,dst/name)
        shutil.copytree(src/'src',dst/'src'); (dst/'tests').mkdir()
        if tests:
            for source,target in tests: shutil.copyfile(source,dst/'tests'/target)
        return dst

def diagnostics(root, runtime='codex'):
    run=Run(root); fx=KIT/'tests/workflow/fixtures'; adv=KIT/'tests/e2e/advanced-fixture/oracle'; hist=KIT/'tests/e2e/results'
    run.check('runner-evidence-guards',['python',str(KIT/'tests/workflow/test_runner.py')],KIT,contains=['Ran 5 tests','OK'])
    contract = 'test-claude.sh' if runtime == 'claude' else 'test-codex.sh'
    success = 'All Claude kit contract tests passed.' if runtime == 'claude' else 'All Codex kit tests passed.'
    run.check('kit-install-gates-validator',['bash',str(KIT/'tests'/contract)],KIT,contains=[success])
    for case in ['01','02']:
        probe=run.copy(case,'logic-'+case,[(hist/'2026-10-24/oracle/regressions.rs','regressions.rs')])
        for profile in ['debug','release']:
            args=['cargo','test','--offline','--locked','--test','regressions']+(['--release'] if profile=='release' else [])
            run.check(f'logic-{case}-{profile}',args,probe,101 if case=='01' else 0,['0 passed; 6 failed' if case=='01' else '6 passed; 0 failed'])
    for case in ['03','04','06']:
        probe=run.copy(case,'runtime-'+case,[(adv/'async_regressions.rs','async_regressions.rs'),(adv/'publication.rs','publication.rs'),(fx/'async_faults.rs','async_faults.rs'),(fx/'async_control.rs','async_control.rs'),(fx/'memory_edges.rs','memory_edges.rs')])
        fail=case=='03'
        for test,count in [('async_regressions',3),('async_faults',4)]:
            run.check(f'{case}-{test}',['cargo','test','--offline','--locked','--test',test],probe,101 if fail else 0,[f'0 passed; {count} failed' if fail else f'{count} passed; 0 failed'])
        if not fail:
            run.check(f'{case}-async-control',['cargo','test','--offline','--locked','--test','async_control'],probe,contains=['4 passed; 0 failed'])
        run.check(f'{case}-publication',['cargo','test','--offline','--locked','--features','model','--test','publication'],probe,101 if fail else 0,['left: 0' if fail else '1 passed; 0 failed'])
        if fail:
            for name in ['short_one','short_two','short_three','unaligned_word','registration_read_after_move','registration_read_during_unregister']:
                run.check('memory-edge-'+name,['cargo','+'+MIRI_TOOLCHAIN,'miri','test','--offline','--locked','--test','memory_edges',name],probe,1,['Undefined Behavior'])
    # Full lifetime tests: initially missed Box issue, good control, both aliasing models.
    for case in ['04','06']:
        src=root/'cases'/case/'src'; probe=root/'probes'/('alias-'+case); (probe/'src').mkdir(parents=True)
        for name in ['registration.rs','bytes.rs']: shutil.copyfile(src/name,probe/'src'/name)
        shutil.copyfile(fx/'aliasing.rs',probe/'src/lib.rs')
        (probe/'Cargo.toml').write_text('[package]\nname="alias-probe"\nversion="0.1.0"\nedition="2024"\n')
        setup(['cargo','generate-lockfile','--offline'],probe)
        for mode,flags in [('stacked',''),('tree','-Zmiri-tree-borrows')]:
            for test in ['retained_after_constructor_and_owner_move','unregister_reads_before_quiescence','empty_registration','arbitrary_alignment_and_short_input']:
                fail=case=='04' and test in ['retained_after_constructor_and_owner_move','unregister_reads_before_quiescence']
                run.check(f'alias-{case}-{mode}-{test}',['cargo','+'+MIRI_TOOLCHAIN,'miri','test','--offline','--locked',test],probe,1 if fail else 0,['Undefined Behavior' if fail else '1 passed; 0 failed'],dict(ENV,MIRIFLAGS=flags))
    # Original narrow test preserves the historically important model disagreement.
    probe=run.copy('04','narrow-alias',[(adv/'memory.rs','memory.rs')])
    p=probe/'tests/memory.rs'; p.write_text(p.read_text().replace('memory_probe','runtime_bridge'))
    for mode,flag in [('stacked',''),('tree','-Zmiri-tree-borrows')]:
        run.check('narrow-alias-'+mode,['cargo','+'+MIRI_TOOLCHAIN,'miri','test','--offline','--locked','--test','memory','ffi_storage_lives_until_unregister'],probe,1 if mode=='stacked' else 0,['Undefined Behavior' if mode=='stacked' else '1 passed; 0 failed'],dict(ENV,MIRIFLAGS=flag))
    # Escalation is decided by fresh review, not by calling an unavailable vendor.
    probe=run.copy('07','bounded-loom',[(root/'cases/07/tests/publication_model.rs','publication_model.rs')])
    p=probe/'tests/publication_model.rs'; s=p.read_text().replace('    builder.check(|| {','    let count = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));\n    let seen=count.clone();\n    builder.check(move || {\n        seen.fetch_add(1,std::sync::atomic::Ordering::SeqCst);')
    s=s.replace('    });\n}', '    });\n    let n=count.load(std::sync::atomic::Ordering::SeqCst);\n    println!("executions: {n}");\n    assert_eq!(n,1);\n}'); p.write_text(s)
    run.check('bounded-loom',['cargo','test','--offline','--locked','--features','model','--test','publication_model','--','--nocapture'],probe,contains=['executions: 1','1 passed; 0 failed'])
    probe=run.copy('08','ambiguous-cancellation',[(fx/'contract_gap.rs','contract_gap.rs')])
    run.check('ambiguous-cancellation',['cargo','test','--offline','--locked','--test','contract_gap','--','--nocapture'],probe,contains=['effects=0','effects=1','1 passed; 0 failed'])
    probe=run.copy('09','complete-loom',[(root/'cases/09/tests/publication_model.rs','publication_model.rs')])
    run.check('complete-loom',['cargo','test','--offline','--locked','--features','model','--test','publication_model','--','--nocapture'],probe,contains=['completed model executions: 6','1 passed; 0 failed'])
    probe=run.copy('10','provider',[(p,p.name) for p in (root/'cases/10/tests').glob('*.rs')]+[(fx/'provider_acceptance.rs','review_acceptance.rs')])
    for name,count in [('vendor_tests',3),('review_acceptance',2)]:
        run.check('provider-'+name,['cargo','test','--offline','--locked','--test',name],probe,contains=[f'{count} passed; 0 failed'])
    run.check('provider-model',['cargo','test','--offline','--locked','--features','model','--test','vendor_model'],probe,contains=['1 passed; 0 failed'])
    p=probe/'src/acme.rs'; source=p.read_text(); p.write_text(source.replace('if state.committed.insert(request) {','state.committed.insert(request);\n        {'))
    for target,flags in [('vendor_tests',[]),('vendor_model',['--features','model'])]:
        run.check('mutation-'+target,['cargo','test','--offline','--locked',*flags,'--test',target],probe,101,['test result: FAILED'])
    p.write_text(source)
    (root/'diagnostics-complete.json').write_text(json.dumps({'completed':True,'checks':len(run.results)}))
    return all(r['pass'] for r in run.results)

def assess(root, runtime='codex', review_guard=None):
    inputs=json.loads((root/'inputs.json').read_text()); results=[]
    for case in CATALOG:
        report=root/'reviews'/case['id']/'report.md'; item={'id':case['id'],'name':case['name'],'status':'PENDING'}
        if report.exists():
            text=report.read_text(); m=re.search(r'^## Verdict: (\w+)$',text,re.M)
            scripts = root/'cases'/case['id']/'.claude/skills/rust-pr-review/scripts' if runtime == 'claude' else KIT/'codex-template/.agents/skills/rust-pr-review/scripts'
            validation=shell(['bash',str(scripts/'check-report.sh'),str(report)],KIT)
            (root/'logs'/f'report-{case["id"]}.log').write_text(validation.stdout+validation.stderr)
            verdict=m.group(1) if m else None
            unchanged=snapshot(root/'cases'/case['id'], runtime)==inputs[case['id']]
            item.update(verdict=verdict,validator_exit=validation.returncode,unchanged=unchanged)
            item['status']='PASS' if verdict in case['verdicts'] and validation.returncode==0 and unchanged else 'FAIL'
            if review_guard is not None:
                errors = review_guard(root, case['id'])
                item['provenance_errors'] = errors
                if errors:
                    item['status'] = 'FAIL'
            # Symbols are review hints for a human assessor, not a semantic defect oracle.
            item['manual_detection_check']=case.get('symbols',[])
        results.append(item)
    (root/'review-results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False))
    diagnostics=json.loads((root/'diagnostics.json').read_text()) if (root/'diagnostics.json').exists() else []
    audit_path=root/'semantic-assessment.json'
    audit=json.loads(audit_path.read_text()) if audit_path.exists() else {}
    def valid_audit(entry):
        paths=entry.get('evidence')
        if not isinstance(entry.get('pass'),bool) or not entry.get('reason') or not isinstance(paths,list) or not paths:
            return False
        return all(isinstance(p,str) and (root/p).resolve().is_relative_to(root) and (root/p).is_file() for p in paths)
    audit_complete=all(c['id'] in audit and valid_audit(audit[c['id']]) for c in CATALOG)
    audit_pass=audit_complete and all(audit[c['id']]['pass'] for c in CATALOG)
    finished=diagnostics_complete(root)
    complete=finished and bool(diagnostics) and all(x['pass'] for x in diagnostics) and all(x['status']=='PASS' for x in results) and audit_pass
    lines=['# Workflow regression run','',f'Diagnostics: {sum(x["pass"] for x in diagnostics)}/{len(diagnostics)} PASS.',f'Fresh review acceptance: {sum(x["status"]=="PASS" for x in results)}/{len(results)} PASS.','', '| Case | Verdict | Acceptance |','| --- | --- | --- |']
    lines += [f'| {x["id"]}: {x["name"]} | {x.get("verdict","—")} | {x["status"]} |' for x in results]
    lines += ['', 'Semantic evidence assessment: '+('PASS' if audit_pass else 'PENDING/FAIL'), '', 'Report acceptance checks verdict, schema and source integrity. Defect explanations and evidence quality still require human/agent assessment. Missing fresh reports never count as PASS.','', 'Overall: '+('PASS' if complete else 'INCOMPLETE/FAIL')]
    (root/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
    return 0 if complete else (2 if finished and all(x['pass'] for x in diagnostics) and (any(x['status']=='PENDING' for x in results) or not audit_complete) else 1)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=pathlib.Path)
    parser.add_argument('--rerun',action='store_true',help='Archive an existing diagnostic attempt before rerunning it')
    parser.add_argument('--phase',choices=['all','prepare','diagnostics','assess'],default='all')
    args=parser.parse_args(); root=args.directory.resolve()
    if args.phase in ['all','prepare']: prepare(root)
    if args.phase in ['all','diagnostics']:
        if (root/'diagnostics.json').exists():
            if not args.rerun: raise SystemExit('Diagnostics already exist; use --rerun to preserve and repeat them')
            attempts=root/'attempts'; attempts.mkdir(exist_ok=True)
            previous=attempts/str(len(list(attempts.iterdir()))+1); previous.mkdir()
            for name in ['diagnostics.json','diagnostics-complete.json','logs','probes']:
                if (root/name).exists(): shutil.move(root/name,previous/name)
            (root/'logs').mkdir()
        ok=diagnostics(root)
        if args.phase=='diagnostics': raise SystemExit(0 if ok else 1)
    if args.phase in ['all','assess']: raise SystemExit(assess(root))

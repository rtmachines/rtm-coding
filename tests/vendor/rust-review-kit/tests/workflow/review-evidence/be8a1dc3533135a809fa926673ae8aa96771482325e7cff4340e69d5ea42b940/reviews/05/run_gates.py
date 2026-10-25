import pathlib, subprocess, os, sys, json
id=sys.argv[1]; root=pathlib.Path('/tmp/rust-review-current-20261025'); r=root/'cases'/id; e=root/'reviews'/id
env=dict(os.environ,CARGO_NET_OFFLINE='true',CARGO_TERM_COLOR='never',RUST_REVIEWDOG='1',RUST_GATE_FEATURES='',CARGO_TARGET_DIR=str(e/'gate-target'),TMPDIR=str(e))
commands=[('fmt',['cargo','fmt','--all','--','--check']),('clippy',['bash','.agents/skills/rust-pr-review/scripts/clippy.sh','--workspace','--all-targets','--locked','--offline','--','-D','warnings']),('tests',['cargo','test','--workspace','--locked','--offline','--no-fail-fast']),('doctests',['cargo','test','--workspace','--doc','--locked','--offline']),('deny',['cargo','deny','--offline','--locked','check','--disable-fetch'])]
status={}
for name,cmd in commands:
 (e/(name+'.command')).write_text('cwd='+str(r)+'\nenv='+repr({k:env[k] for k in ['CARGO_NET_OFFLINE','CARGO_TERM_COLOR','RUST_REVIEWDOG','RUST_GATE_FEATURES','CARGO_TARGET_DIR','TMPDIR']})+'\n'+repr(cmd))
 with (e/(name+'.log')).open('w') as out:
  try: p=subprocess.run(cmd,cwd=r,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=180);status[name]=p.returncode
  except subprocess.TimeoutExpired:status[name]=124
 (e/'gates-status.json').write_text(json.dumps(status,indent=2))
 print(id,name,status[name],flush=True)

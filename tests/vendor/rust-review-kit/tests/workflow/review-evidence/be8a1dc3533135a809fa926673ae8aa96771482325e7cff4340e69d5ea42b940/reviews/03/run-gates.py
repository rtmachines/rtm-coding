from pathlib import Path
import os,subprocess,json
for i in ['02','03','08','11']:
 r=Path('/tmp/rust-review-current-20261025/cases')/i;o=Path('/tmp/rust-review-current-20261025/reviews')/i
 env=os.environ.copy();env.update(CARGO_NET_OFFLINE='true',CARGO_TARGET_DIR=str(o/'gate-target'),RUST_REVIEWDOG='1',CARGO_TERM_COLOR='never',TMPDIR=str(o))
 features=['--all-features'] if i=='02' else []
 cmds=[('fmt',['cargo','fmt','--all','--','--check']),('clippy',['bash','.agents/skills/rust-pr-review/scripts/clippy.sh','--workspace','--all-targets',*features,'--locked','--','-D','warnings']),('tests',['cargo','test','--offline','--workspace',*features,'--locked','--no-fail-fast']),('doctests',['cargo','test','--offline','--workspace','--doc',*features,'--locked']),('deny',['cargo','deny','--offline','--locked','check','--disable-fetch'])]
 statuses={}
 for name,cmd in cmds:
  with (o/(name+'.log')).open('w') as f:
   f.write('$ '+' '.join(cmd)+'\n');f.flush()
   p=subprocess.run(cmd,cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT)
  statuses[name]=p.returncode
 (o/'gates-status.json').write_text(json.dumps(statuses,indent=2))
 (o/'gate-commands.json').write_text(json.dumps(cmds,indent=2))
 print(i,statuses,flush=True)

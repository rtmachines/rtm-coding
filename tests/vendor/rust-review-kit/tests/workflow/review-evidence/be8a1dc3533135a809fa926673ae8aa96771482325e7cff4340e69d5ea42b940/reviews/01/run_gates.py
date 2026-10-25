from pathlib import Path
import os,subprocess,json,concurrent.futures

def run(id):
 r=Path('/tmp/rust-review-current-20261025/cases')/id;e=Path('/tmp/rust-review-current-20261025/reviews')/id
 env=os.environ|{'CARGO_NET_OFFLINE':'true','RUST_REVIEWDOG':'1','CARGO_TARGET_DIR':str(e/'target'),'TMPDIR':str(e),'CARGO_TERM_COLOR':'never'}
 flags=['--all-features'] if id=='01' else []
 cmds=[('versions',['rustc','-Vv']),('fmt',['cargo','fmt','--all','--','--check']),('clippy',['bash','.agents/skills/rust-pr-review/scripts/clippy.sh','--offline','--workspace','--all-targets',*flags,'--locked','--','-D','warnings']),('tests',['cargo','test','--offline','--workspace',*flags,'--locked','--lib','--tests']),('doctests',['cargo','test','--offline','--workspace',*flags,'--locked','--doc']),('deny',['cargo','deny','--offline','--locked','check'])]
 results={}
 for name,cmd in cmds:
  with (e/(name+'.log')).open('w') as f:
   f.write('$ '+' '.join(cmd)+'\n');f.flush();p=subprocess.run(cmd,cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  results[name]={'cmd':cmd,'status':p.returncode}
 (e/'gates.json').write_text(json.dumps(results,indent=2));print(id,results,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as x:list(x.map(run,['01','04','07','10']))

import subprocess,os,json
from pathlib import Path
b=Path('/tmp/rust-review-current-20261025/reviews')
jobs=[('02','contracts','probe',['cargo','test','--offline','--locked','--test','contracts'],{}),
('03','async','probe',['cargo','test','--offline','--locked','--test','async_contracts'],{}),
('03','loom','probe',['cargo','test','--offline','--locked','--features','model','--test','publication_model'],{})]
for test in ['unaligned_word','short_word','retained_until_unregister']:
 jobs.append(('03','miri-'+test,'memory',['cargo','+nightly','miri','test','--offline',test],{'MIRI_SYSROOT':'/home/rtm/.cache/miri','MIRIFLAGS':''}))
for i,name,cwd,cmd,extra in jobs:
 env={**os.environ,'CARGO_NET_OFFLINE':'true','CARGO_TARGET_DIR':str(b/i/(cwd+'-target')),**extra}
 with (b/i/(name+'.log')).open('w') as f:
  f.write('$ '+' '.join(cmd)+'\n'+repr(extra)+'\n');f.flush()
  try: p=subprocess.run(cmd,cwd=b/i/cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120);status=p.returncode
  except subprocess.TimeoutExpired:status=124
 (b/i/(name+'-status.json')).write_text(json.dumps({'command':cmd,'cwd':str(b/i/cwd),'env':extra,'exit':status}))
 print(i,name,status,flush=True)

from pathlib import Path
import subprocess,os,json,concurrent.futures
root=Path('/tmp/rust-skills-review-20261025')
jobs=[('04','transitions','reviews/04/probe','cargo +stable test --locked --offline --test transitions'),('04','loom','reviews/04/probe','cargo +stable test --locked --offline --features model --test publication_model'),('04','miri-stacked','reviews/04/memory-probe','MIRI_SYSROOT=/home/rtm/.cache/miri cargo +nightly miri test --offline --test memory'),('04','miri-tree','reviews/04/memory-probe','MIRI_SYSROOT=/home/rtm/.cache/miri MIRIFLAGS=-Zmiri-tree-borrows cargo +nightly miri test --offline --test memory'),('07','loom','cases/07','cargo +stable test --locked --offline --features model --test publication_model'),('10','loom','cases/10','cargo +stable test --locked --offline --features model --test vendor_model')]
def run(j):
 id,name,cwd,cmd=j;o=root/'reviews'/id;env=os.environ.copy();env.update(CARGO_NET_OFFLINE='true',CARGO_TERM_COLOR='never',CARGO_TARGET_DIR=f'/tmp/rust-review-probe-target-a-{id}-{name}')
 with (o/(name+'.log')).open('w') as f:
  try:p=subprocess.run(cmd,shell=True,executable='/bin/bash',cwd=root/cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120);code=p.returncode
  except subprocess.TimeoutExpired:code=124
 (o/(name+'-command.json')).write_text(json.dumps({'command':cmd,'cwd':str(root/cwd),'exit':code,'timeout_seconds':120},indent=2));print(id,name,code,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(run,jobs))

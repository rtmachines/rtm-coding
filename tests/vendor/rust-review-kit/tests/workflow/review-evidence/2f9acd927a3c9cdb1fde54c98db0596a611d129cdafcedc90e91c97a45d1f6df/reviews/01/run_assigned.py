from pathlib import Path
import subprocess,os,json,concurrent.futures
root=Path('/tmp/rust-skills-review-20261025')
def run(id):
 r=root/'cases'/id;o=root/'reviews'/id;env=os.environ.copy();env.update(CARGO_NET_OFFLINE='true',CARGO_TERM_COLOR='never',RUSTUP_TOOLCHAIN='stable',CARGO_TARGET_DIR=f'/tmp/rust-review-target-a-{id}')
 cmds={'versions':'rustc --version --verbose && cargo --version && cargo deny --version','fmt':'cargo fmt --all -- --check','clippy':'cargo clippy --workspace --all-targets --locked --offline --message-format=short --color=never -- -D warnings','tests':'cargo test --workspace --locked --offline --no-fail-fast','doctests':'cargo test --workspace --doc --locked --offline','deny':'cargo deny --locked --offline check','reviewdog':f'/home/rtm/.local/bin/reviewdog -f=clippy -reporter=local -filter-mode=nofilter -fail-level=warning < {o}/clippy.log'}
 results={}
 for name,cmd in cmds.items():
  with (o/(name+'.log')).open('w') as f:
   try:p=subprocess.run(cmd,shell=True,executable='/bin/bash',cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120);results[name]={'command':cmd,'exit':p.returncode}
   except subprocess.TimeoutExpired:results[name]={'command':cmd,'exit':124}
  (o/'commands.json').write_text(json.dumps(results,indent=2))
 print(id,results,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(run,['01','04','07','10']))

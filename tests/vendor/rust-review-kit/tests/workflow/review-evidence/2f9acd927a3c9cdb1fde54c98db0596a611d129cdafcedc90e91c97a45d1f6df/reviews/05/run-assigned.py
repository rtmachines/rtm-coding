import subprocess,pathlib,os,json,concurrent.futures
root=pathlib.Path('/tmp/rust-skills-review-20261025')
def run(id):
 p=root/'cases'/id;o=root/'reviews'/id
 env=os.environ.copy();env.update(CARGO_NET_OFFLINE='true',CARGO_TARGET_DIR=f'/tmp/rust-review-target-c-{id}',RUSTUP_TOOLCHAIN='stable',CARGO_TERM_COLOR='never')
 cmds=[('versions','rustc -Vv; cargo -V; cargo deny --version; cargo +nightly miri --version'),('fmt','cargo fmt --all -- --check'),('clippy','cargo clippy --workspace --all-targets --locked --offline --message-format=short -- -D warnings'),('reviewdog',f'/home/rtm/.local/bin/reviewdog -f=clippy -reporter=local -filter-mode=nofilter -fail-level=warning < {o}/clippy.log'),('tests','cargo test --workspace --locked --offline --no-fail-fast'),('doctests','cargo test --workspace --doc --locked --offline'),('deny','cargo deny --locked --offline check')]
 if id in ['06','09']:cmds.append(('loom','timeout 120 cargo test --locked --offline --features model --test '+('publication' if id=='06' else 'publication_model')+' -- --nocapture'))
 if id=='06':cmds.append(('miri','timeout 120 cargo +nightly miri test --locked --offline --test memory'))
 result=[]
 for name,cmd in cmds:
  with (o/(name+'.log')).open('w') as f:r=subprocess.run(['bash','-c',cmd],cwd=p,env=env,stdout=f,stderr=subprocess.STDOUT)
  result.append(dict(name=name,command=cmd,cwd=str(p),environment={k:env[k] for k in ['CARGO_NET_OFFLINE','CARGO_TARGET_DIR','RUSTUP_TOOLCHAIN','CARGO_TERM_COLOR']},exit=r.returncode));(o/'commands.json').write_text(json.dumps(result,indent=2));print(id,name,r.returncode,flush=True)
with concurrent.futures.ThreadPoolExecutor(3) as e:list(e.map(run,['05','06','09']))

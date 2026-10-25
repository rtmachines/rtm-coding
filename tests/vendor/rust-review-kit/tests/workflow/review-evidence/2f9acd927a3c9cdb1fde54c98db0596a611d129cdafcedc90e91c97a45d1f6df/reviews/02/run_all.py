import pathlib,subprocess,os,json,concurrent.futures
root=pathlib.Path('/tmp/rust-skills-review-20261025')
def run(i):
 p=root/'cases'/i;o=root/'reviews'/i;env=os.environ.copy();env.update(CARGO_NET_OFFLINE='true',RUSTUP_TOOLCHAIN='stable',CARGO_TARGET_DIR=f'/tmp/rust-review-build-b/{i}')
 features=['--all-features'] if i=='02' else []
 cmds=[('context',['bash','.agents/skills/rust-pr-review/scripts/context.sh','origin/main']),('diff',['git','diff','--no-ext-diff','--no-textconv','origin/main','--']),('fmt',['cargo','fmt','--all','--','--check']),('clippy',['cargo','clippy','--offline','--locked','--workspace','--all-targets']+features+['--message-format=short','--color=never','--','-D','warnings']),('tests',['cargo','test','--offline','--locked','--workspace']+features),('doctests',['cargo','test','--offline','--locked','--workspace','--doc']+features),('deny',['cargo','deny','--locked','--offline','check']),('versions',['rustc','--version','--verbose'])]
 status={}
 for name,cmd in cmds:
  with (o/(name+'.log')).open('w') as f:
   try:r=subprocess.run(cmd,cwd=p,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120);status[name]=r.returncode
   except subprocess.TimeoutExpired:status[name]=124
  with (o/'commands.jsonl').open('a') as f:f.write(json.dumps({'command':cmd,'cwd':str(p),'env':{k:env[k] for k in ['CARGO_NET_OFFLINE','RUSTUP_TOOLCHAIN','CARGO_TARGET_DIR']},'exit':status[name]})+'\n')
 with (o/'clippy.log').open() as f,(o/'reviewdog.log').open('w') as out:
  r=subprocess.run(['/home/rtm/.local/bin/reviewdog','-f=clippy','-reporter=local','-filter-mode=nofilter','-fail-level=warning'],cwd=p,stdin=f,stdout=out,stderr=subprocess.STDOUT);status['reviewdog']=r.returncode
 (o/'status.json').write_text(json.dumps(status));print(i,status,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as e:list(e.map(run,['02','03','08','11']))

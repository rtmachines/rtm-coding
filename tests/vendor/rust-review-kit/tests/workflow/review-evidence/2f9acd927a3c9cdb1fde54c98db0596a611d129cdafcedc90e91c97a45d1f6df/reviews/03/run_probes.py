import os,subprocess,pathlib,json
root=pathlib.Path('/tmp/rust-skills-review-20261025/reviews');env=os.environ.copy();env.update(CARGO_NET_OFFLINE='true',CARGO_TARGET_DIR='/tmp/rust-review-build-b/probes',RUSTUP_TOOLCHAIN='stable')
commands=[('02','contracts','probe',['cargo','test','--offline','--locked','--test','contracts'],{}),('03','async','probe',['cargo','test','--offline','--locked','--test','async'],{}),('03','loom','probe',['cargo','test','--offline','--locked','--features','model','--test','model'],{})]
for test in ['short_word','unaligned_word','retained_buffer']:
 commands.append(('03','miri-'+test,'memory',['cargo','+nightly','miri','test','--offline',test],{'MIRI_SYSROOT':'/home/rtm/.cache/miri','MIRIFLAGS':'-Zmiri-strict-provenance'}))
for i,name,d,cmd,extra in commands:
 o=root/i
 with (o/(name+'.log')).open('w')as f:
  try:r=subprocess.run(cmd,cwd=o/d,env=env|extra,stdout=f,stderr=subprocess.STDOUT,timeout=120);s=r.returncode
  except subprocess.TimeoutExpired:s=124
 with(o/'commands.jsonl').open('a')as f:f.write(json.dumps({'command':cmd,'cwd':str(o/d),'env':{k:v for k,v in (env|extra).items() if k in ['CARGO_NET_OFFLINE','CARGO_TARGET_DIR','RUSTUP_TOOLCHAIN','MIRI_SYSROOT','MIRIFLAGS']},'exit':s})+'\n')
 (o/(name+'.exit')).write_text(str(s));print(name,s,flush=True)

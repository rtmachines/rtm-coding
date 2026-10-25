from pathlib import Path
import os,subprocess,json,concurrent.futures
root=Path('/tmp/rust-review-current-20261025')
items=[('01','contracts',True,['cargo','test','--offline','--locked','--test','contracts'],{}),('04','targeted',True,['cargo','test','--offline','--locked','--test','targeted'],{}),('04','model',True,['cargo','test','--offline','--locked','--features','model','--test','model'],{}),('04','miri-stacked',True,['cargo','+nightly','miri','test','--offline','--locked','--test','memory'],{'MIRI_SYSROOT':'/home/rtm/.cache/miri','MIRIFLAGS':''}),('04','miri-tree',True,['cargo','+nightly','miri','test','--offline','--locked','--test','memory'],{'MIRI_SYSROOT':'/home/rtm/.cache/miri','MIRIFLAGS':'-Zmiri-tree-borrows'}),('07','model',False,['cargo','test','--offline','--locked','--features','model','--test','publication_model'],{}),('10','model',False,['cargo','test','--offline','--locked','--features','model','--test','vendor_model'],{}),('10','before_timeout',True,['cargo','test','--offline','--locked','--test','before_timeout'],{})]
def run(item):
 id,name,probe,cmd,extra=item;e=root/'reviews'/id;cwd=e/'probe' if probe else root/'cases'/id
 env=os.environ|{'CARGO_NET_OFFLINE':'true','CARGO_TARGET_DIR':str(e/(name+'-target')),'CARGO_TERM_COLOR':'never','RUST_REVIEWDOG':'1'}|extra
 with (e/(name+'.log')).open('w') as f:
  f.write('$ '+' '.join(cmd)+'\n'+str(extra)+'\n');f.flush()
  try: p=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120);status=p.returncode
  except subprocess.TimeoutExpired:status=124
 (e/(name+'-status.json')).write_text(json.dumps({'cwd':str(cwd),'command':cmd,'environment':extra,'status':status,'watchdog_seconds':120},indent=2));print(id,name,status,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as p:list(p.map(run,items))

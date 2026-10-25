import pathlib,subprocess,os,json,hashlib,sys
case=sys.argv[1]; mode=sys.argv[2]; root=pathlib.Path('/tmp/rust-review-lsp-20261025/cases')/case; out=pathlib.Path('/tmp/rust-review-lsp-20261025/reviews')/case;out.mkdir(exist_ok=True)
def run(name,cmd,cwd=root):
 p=subprocess.run(['timeout','90s','bash','-c',cmd.replace(' --all-features','') if case in ('03','08','11') else cmd],cwd=cwd,env={**os.environ,'CARGO_NET_OFFLINE':'true','CARGO_TARGET_DIR':str(out/'target'),'CARGO_TERM_COLOR':'never'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (out/(name+'.log')).write_bytes(p.stdout);(out/'commands.log').open('a').write(f'{name}: cwd={cwd} timeout 90s {cmd}\nexit={p.returncode}\n');print(name,p.returncode,p.stdout.decode()[-1200:])
if mode in ('before','after'):
 files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
 (out/(mode+'.json')).write_text(json.dumps({p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files if (root/p).is_file()},indent=2))
 (out/('git-'+mode+'.txt')).write_text(subprocess.check_output(['git','status','--porcelain=v1'],cwd=root).decode()+subprocess.check_output(['git','rev-parse','HEAD','origin/main'],cwd=root).decode())
 run('context','bash .agents/skills/rust-pr-review/scripts/context.sh origin/main')
 run('diff','rtk bypass git diff --no-ext-diff --no-textconv origin/main --')
if mode=='gates':
 for name,cmd in [('versions','rustc -Vv; cargo -V; cargo deny --version'),('fmt','cargo fmt --all -- --check'),('clippy','cargo clippy --workspace --all-targets --all-features --locked --message-format=short --color=never -- -D warnings'),('reviewdog',f'/home/rtm/.local/bin/reviewdog -f=clippy -reporter=local -filter-mode=nofilter -fail-level=warning < {out}/clippy.log'),('tests','cargo test --workspace --all-features --locked --no-fail-fast'),('doctests','cargo test --workspace --doc --all-features --locked'),('deny','cargo deny --locked --offline check')]: run(name,cmd)
if mode=='validate': run('validate',f'bash .agents/skills/rust-pr-review/scripts/check-report.sh {out}/report.md')

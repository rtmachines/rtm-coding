"""Bindings shared by the local runner and CI; no network or model execution."""
import hashlib
import json
import os
import stat
import subprocess
from contextlib import ExitStack, contextmanager
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@contextmanager
def _parent_directory(repo, relative):
    """Open each ancestor without traversing a symlink, including during races."""
    with ExitStack() as opened:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptor = os.open(repo, flags)
        opened.callback(os.close, descriptor)
        for component in relative.parts[:-1]:
            try:
                descriptor = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                raise
            except OSError as error:
                raise ValueError(f'Unsupported symlink or non-directory ancestor: {relative}') from error
            opened.callback(os.close, descriptor)
        yield descriptor


def _check_link_target(repo, relative, target, visible):
    destination = Path(os.path.normpath(os.path.join(repo, relative.parent, target)))
    if not destination.is_relative_to(repo):
        raise ValueError(f'Unsupported escaping symlink: {relative}')
    target_relative = destination.relative_to(repo)
    if str(target_relative) not in visible:
        raise ValueError(f'Unsupported symlink target outside Git-visible inputs: {relative}')
    try:
        with _parent_directory(repo, target_relative) as parent:
            info = os.stat(target_relative.name, dir_fd=parent, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                raise ValueError(f'Unsupported indirect symlink: {relative}')
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f'Unsupported non-file symlink target: {relative}')
    except FileNotFoundError as error:
        raise ValueError(f'Unsupported dangling symlink: {relative}') from error


def git_input_files(repo):
    """Hash Git-visible bytes/modes, never dereference a symlink or ignored cache."""
    repo = Path(repo).resolve()
    listing = subprocess.run(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
        cwd=repo, capture_output=True, check=True,
    )
    files = {}
    visible = {os.fsdecode(name) for name in listing.stdout.split(b'\0') if name}
    for name in sorted(visible):
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError(f'Invalid Git input path: {name}')
        try:
            with _parent_directory(repo, relative) as parent:
                info = os.stat(relative.name, dir_fd=parent, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    target = os.readlink(relative.name, dir_fd=parent)
                    _check_link_target(repo, relative, target, visible)
                    files[name] = {'type': 'symlink', 'sha256': hashlib.sha256(os.fsencode(target)).hexdigest()}
                elif stat.S_ISREG(info.st_mode):
                    descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                    with os.fdopen(descriptor, 'rb') as stream:
                        opened = os.fstat(stream.fileno())
                        if not stat.S_ISREG(opened.st_mode):
                            raise ValueError(f'Unsupported non-file input: {name}')
                        files[name] = {
                            'type': 'file', 'mode': stat.S_IMODE(opened.st_mode),
                            'sha256': hashlib.file_digest(stream, 'sha256').hexdigest(),
                        }
                else:
                    raise ValueError(f'Unsupported non-file input (including submodules): {name}')
        except FileNotFoundError:
            files[name] = {'type': 'missing'}
    return files


def suite_identity(kit, runtime='codex'):
    kit = Path(kit)
    if runtime not in ('codex', 'claude'):
        raise ValueError(f'Unknown review runtime: {runtime}')
    files = set()
    templates = ['codex-template', 'codex-optional'] if runtime == 'codex' else ['template', 'optional']
    if runtime == 'claude':
        templates.append('codex-template/.agents/skills/rust-skills')
    for name in templates + ['scripts', 'licenses', '.github/workflows', 'tests']:
        for p in (kit/name).rglob('*'):
            if not p.is_file() or p.is_symlink():
                continue
            rel = p.relative_to(kit)
            if '__pycache__' in rel.parts or p.suffix == '.pyc':
                continue
            if str(rel).startswith(('tests/e2e/results/', 'tests/workflow/review-evidence/')):
                continue
            files.add(rel)
    for name in ['install.sh', 'vendored.tsv', 'THIRD_PARTY_NOTICES.md']:
        files.add(Path(name))
    if runtime == 'claude':
        files.add(Path('install-claude.sh'))
    catalog = json.loads((kit/'tests/workflow/cases.json').read_text())
    for case in catalog:
        files.add(Path('tests/e2e/results')/case['archive'])
    files.add(Path('tests/e2e/results/2026-10-24/oracle/regressions.rs'))
    hashes = {str(p): hashlib.sha256((kit/p).read_bytes()).hexdigest() for p in sorted(files)}
    identity = {'schema': 1, 'fingerprint': digest(hashes), 'files': hashes}
    if runtime == 'claude':
        identity['runtime'] = runtime
    return identity


def binding(root):
    root = Path(root)
    suite = json.loads((root/'suite-identity.json').read_text())
    inputs = json.loads((root/'inputs.json').read_text())
    return {'schema': 1, 'suite': suite['fingerprint'], 'inputs': digest(inputs)}


def diagnostics_complete(root):
    root = Path(root)
    try:
        records = json.loads((root/'diagnostics.json').read_text())
        marker = json.loads((root/'diagnostics-complete.json').read_text())
        return (marker.get('completed') is True and isinstance(records, list) and len(records) > 0
                and marker.get('checks') == len(records)
                and len({r['name'] for r in records}) == len(records)
                and all(r.get('pass') is True for r in records))
    except (OSError, ValueError, KeyError, TypeError):
        return False

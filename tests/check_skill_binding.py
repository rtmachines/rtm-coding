"""Require published skill sources to match the inputs reviewed by the suite."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGING = {
    'rust-pr-review/LICENSE.txt',
    'rust-pr-review/THIRD_PARTY_NOTICES.md',
    'rust-best-practices/LICENSE.txt',
}


def inventory(root, excluded=()):
    result = {}
    for path in root.rglob('*'):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f'Symlink is not a reviewed source: {path}')
        if path.is_file() and relative not in excluded:
            result[relative] = path.read_bytes()
    return result


def check(root=ROOT):
    source = root / 'tests/vendor/rust-review-kit/codex-template/.agents/skills'
    expected = inventory(source)
    actual = inventory(root / 'skills', PACKAGING | {'README.md'})
    if not expected or actual != expected:
        changed = sorted(key for key in actual.keys() | expected.keys()
                         if actual.get(key) != expected.get(key))
        raise ValueError('Published skills differ from reviewed inputs: '
                         + ', '.join(changed)
                         + '. Update the suite sources and supply matching review evidence.')
    print(f'PASS: {len(expected)} published sources match reviewed suite inputs')


if __name__ == '__main__':
    check()

#!/usr/bin/env python3
"""Install an isolated RobCo profile. No network access or elevated privileges."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent
PROFILE_ID = '83E18F48-2400-4A12-9DB5-2D8CBFE48D67'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def paths(home):
    return (home / 'Library/Application Support/RobCo Terminal',
            home / 'Library/Application Support/iTerm2/DynamicProfiles/RobCo-Terminal.json',
            home / 'Library/Fonts/RobCoCaseHeavy-Regular.ttf')


def files_under(root):
    return {str(p.relative_to(root)): digest(p.read_bytes())
            for p in root.rglob('*') if p.is_file() and p.name != '.robco-install.json'}


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.robco-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def verify_install(target, profile, font):
    marker = target / '.robco-install.json'
    if not marker.is_file() or marker.is_symlink():
        raise ValueError(f'Unmanaged installation directory: {target}')
    state = json.loads(marker.read_text())
    if state.get('id') != PROFILE_ID:
        raise ValueError('Installation identity mismatch.')
    for path, key in ((profile, 'profile_hash'), (font, 'font_hash')):
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != state[key]:
            raise ValueError(f'File missing or changed; preserve/restore it before removal: {path}')
    # History, completion caches and user-created files stay in the retained folder.
    for rel, expected in state['files'].items():
        path = target / rel
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError(f'Installed file changed; back it up and restore before removal: {path}')
    return state


def install(home):
    target, profile, font = paths(home)
    if target.is_symlink() or profile.is_symlink() or font.is_symlink():
        raise ValueError('Refusing symlink at an installation destination.')
    if target.exists():
        verify_install(target, profile, font)
        print('RobCo Terminal is already installed. Uninstall before installing a new version.')
        return
    if profile.exists():
        raise ValueError(f'Profile filename already exists: {profile}')
    # Prevent duplicate GUIDs in another dynamic-profile file.
    if profile.parent.exists():
        import plistlib
        for path in profile.parent.iterdir():
            if not path.is_file():
                continue
            try:
                raw = path.read_bytes()
                try:
                    document = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    document = plistlib.loads(raw)
            except (ValueError, plistlib.InvalidFileException):
                continue
            if isinstance(document, dict) and any(
                isinstance(p, dict) and p.get('Guid') == PROFILE_ID
                for p in document.get('Profiles', [])):
                raise ValueError(f'RobCo profile GUID already exists in {path}')
    font_data = (SOURCE / 'payload/fonts/RobCoCaseHeavy-Regular.ttf').read_bytes()
    if font.exists() and font.read_bytes() != font_data:
        raise ValueError(f'A different font already exists: {font}')
    font_owned = not font.exists()
    p = json.loads((SOURCE / 'profile-template.json').read_text())
    # An absolute interpreter path also works when Python is not on login PATH.
    command = ['/usr/bin/env', 'ZDOTDIR=' + str(target / 'shell'),
               'ROBCO_PYTHON=' + sys.executable, '/bin/zsh', '-l']
    p.update({'Command': shlex.join(command), 'Working Directory': str(home),
              'Background Image Location': str(target / 'logo.png')})
    profile_data = (json.dumps({'Profiles': [p]}, indent=2) + '\n').encode()
    created = []
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.robco-stage-', dir=target.parent) as temp:
            stage = Path(temp) / 'payload'
            shutil.copytree(SOURCE / 'payload', stage,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
            state = {'id': PROFILE_ID, 'files': files_under(stage),
                     'profile_hash': digest(profile_data), 'font_hash': digest(font_data),
                     'font_owned': font_owned}
            (stage / '.robco-install.json').write_text(json.dumps(state, indent=2) + '\n')
            stage.rename(target)
        created.append(target)
        if font_owned:
            atomic_write(font, font_data)
            created.append(font)
        atomic_write(profile, profile_data)
        created.append(profile)
    except Exception:
        for path in reversed(created):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        raise
    print('Installed RobCo Terminal. Open iTerm2 > Profiles > RobCo Terminal.')
    print('Allow the background image if iTerm2 asks. Your default profile was not changed.')


def uninstall(home):
    target, profile, font = paths(home)
    if not target.exists():
        print('No managed RobCo installation found; nothing removed.')
        return
    state = verify_install(target, profile, font)
    profile.unlink()
    if state['font_owned']:
        font.unlink()
    for rel in state['files']:
        (target / rel).unlink()
    (target / '.robco-install.json').unlink()
    for path in sorted(target.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and not path.is_symlink():
            try:
                path.rmdir()
            except OSError:
                pass
    try:
        target.rmdir()
    except OSError:
        print(f'Kept shell history, caches or extra files in {target}')
    print('Removed the RobCo profile and managed files. Existing profiles were not changed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--test-home', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.test_home is None and sys.platform != 'darwin':
        parser.error('RobCo Terminal requires macOS and iTerm2.')
    if sys.version_info < (3, 9):
        parser.error('Python 3.9 or newer is required.')
    home = (args.test_home or Path.home()).resolve()
    try:
        (uninstall if args.uninstall else install)(home)
    except (OSError, ValueError, KeyError) as error:
        print(f'Stopped: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

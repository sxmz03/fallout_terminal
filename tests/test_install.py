"""Run with python3 -m unittest discover -s tests -v."""
import importlib.util
import json
import os
import io
import shlex
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'installer.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="robco friend's home ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.target, self.profile, self.font = installer.paths(self.home)
        (self.home / '.zshrc').write_text('PERSONAL_CONFIG_UNTOUCHED=1\n')

    def test_round_trip_repeat_and_isolated_shell(self):
        installer.install(self.home)
        p = json.loads(self.profile.read_text())['Profiles'][0]
        self.assertEqual(p['Guid'], installer.PROFILE_ID)
        self.assertEqual(p['Normal Font'], 'RobCoCaseHeavy-Regular 22')
        self.assertEqual(Path(p['Background Image Location']), self.target / 'logo.png')
        before = self.profile.read_bytes()
        installer.install(self.home)
        self.assertEqual(before, self.profile.read_bytes())
        env = dict(os.environ, HOME=str(self.home), ZDOTDIR=str(self.target / 'shell'),
                   TERM_PROGRAM='test', TERM='xterm-256color')
        result = subprocess.run(shlex.split(p['Command']) + ['-i', '-c',
            '[[ $PROMPT == *\'[>]\'* && $_robco_header_hex == 0x[0-9a-f][0-9a-f][0-9a-f][0-9a-f] ]] || exit 20; '
            '[[ ${(j:,:)zle_highlight} == *default:fg=black,bg=green* ]] || exit 21; '
            '[[ -z ${PERSONAL_CONFIG_UNTOUCHED:-} ]] || exit 22'],
            env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        # Simulate normal runtime-created history; uninstall must retain it.
        history = self.target / 'shell/.zsh_history'
        history.write_text('echo hello\n')
        installer.uninstall(self.home)
        self.assertFalse(self.profile.exists())
        self.assertFalse(self.font.exists())
        self.assertTrue(history.exists())
        self.assertEqual((self.home / '.zshrc').read_text(), 'PERSONAL_CONFIG_UNTOUCHED=1\n')

    def test_preserve_preexisting_identical_font(self):
        self.font.parent.mkdir(parents=True)
        original = (ROOT / 'payload/fonts/RobCoCaseHeavy-Regular.ttf').read_bytes()
        self.font.write_bytes(original)
        installer.install(self.home)
        installer.uninstall(self.home)
        self.assertEqual(self.font.read_bytes(), original)

    def test_refuse_conflicts_before_changes(self):
        self.font.parent.mkdir(parents=True)
        self.font.write_bytes(b'other font')
        with self.assertRaises(ValueError):
            installer.install(self.home)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.profile.exists())
        self.assertEqual(self.font.read_bytes(), b'other font')

    def test_profile_collision(self):
        self.profile.parent.mkdir(parents=True)
        self.profile.write_text('personal profile')
        with self.assertRaises(ValueError):
            installer.install(self.home)
        self.assertEqual(self.profile.read_text(), 'personal profile')
        self.assertFalse(self.target.exists())

    def test_duplicate_guid(self):
        self.profile.parent.mkdir(parents=True)
        other = self.profile.parent / 'other.json'
        other.write_text(json.dumps({'Profiles':[{'Guid':installer.PROFILE_ID}]}))
        with self.assertRaises(ValueError):
            installer.install(self.home)
        self.assertFalse(self.target.exists())

    def test_modified_files_preserved(self):
        installer.install(self.home)
        logo = self.target / 'logo.png'
        logo.write_bytes(b'personal replacement')
        with self.assertRaises(ValueError):
            installer.uninstall(self.home)
        self.assertTrue(self.profile.exists())
        self.assertTrue(self.font.exists())
        self.assertEqual(logo.read_bytes(), b'personal replacement')

    def test_rollback_on_profile_write_failure(self):
        original = installer.atomic_write
        def failing_write(path, data):
            if path == self.profile:
                raise OSError('simulated profile write failure')
            original(path, data)
        with patch.object(installer, 'atomic_write', side_effect=failing_write):
            with self.assertRaises(OSError):
                installer.install(self.home)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.font.exists())
        self.assertFalse(self.profile.exists())

    def test_reinstall_after_normal_removal(self):
        installer.install(self.home)
        installer.uninstall(self.home)
        self.assertFalse(self.target.exists())
        installer.install(self.home)
        installer.verify_install(self.target, self.profile, self.font)

    def test_install_from_relocated_repository(self):
        checkout = self.home / "downloaded repo's folder"
        shutil.copytree(ROOT, checkout, ignore=shutil.ignore_patterns('__pycache__'))
        result = subprocess.run([str(checkout/'install.sh'), '--test-home', str(self.home)],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        installer.verify_install(self.target, self.profile, self.font)
        # Neither generated profile nor scripts may refer back to the checkout.
        for path in [self.profile, *self.target.rglob('*.zsh')]:
            self.assertNotIn(str(checkout), path.read_text())

    def test_full_player_control_sequence_and_pacing(self):
        player_spec = importlib.util.spec_from_file_location('player_full', ROOT/'payload/startup-animations/play.py')
        player = importlib.util.module_from_spec(player_spec)
        player_spec.loader.exec_module(player)
        class Terminal(io.StringIO):
            def isatty(self):
                return True
            def fileno(self):
                raise OSError('test terminal')
        terminal = Terminal()
        env = {'TERM_PROGRAM': 'iTerm.app'}
        delays = []
        with patch.dict(os.environ, env, clear=True), \
             patch.object(player.sys, 'stdout', terminal), \
             patch.object(player.shutil, 'get_terminal_size', return_value=os.terminal_size((110,32))), \
             patch.object(player.time, 'monotonic', side_effect=[0,4]), \
             patch.object(player.time, 'sleep', side_effect=delays.append), \
             patch.object(player.subprocess, 'run') as restore:
            self.assertTrue(player.play('TEST [>]'))
        output = terminal.getvalue()
        self.assertIn('MultipartFile=inline=1', output)
        self.assertIn('FileEnd', output)
        self.assertIn(player.BOOT_MESSAGE, output)
        self.assertLess(output.index(player.BOOT_MESSAGE), output.index('TEST [>]'))
        self.assertTrue(output.endswith('\x1b[?25h'))
        self.assertEqual(delays.count(0.4), 3)
        self.assertTrue(all(delay in (0.030,0.4) for delay in delays))
        self.assertEqual(Path(restore.call_args.args[0][1]), ROOT/'payload/show-image-logo.zsh')

    def test_copied_assets_and_gif_processing(self):
        player_spec = importlib.util.spec_from_file_location('player', ROOT/'payload/startup-animations/play.py')
        player = importlib.util.module_from_spec(player_spec)
        player_spec.loader.exec_module(player)
        data = (ROOT/'payload/startup-animations/standard.gif').read_bytes()
        processed = player.single_play_gif(player.green_palette(data))
        self.assertTrue(processed.startswith((b'GIF87a', b'GIF89a')))
        self.assertTrue(processed.endswith(b';'))
        self.assertNotIn(b'NETSCAPE2.0', processed)
        self.assertEqual((ROOT/'payload/logo.png').read_bytes()[:8], b'\x89PNG\r\n\x1a\n')


if __name__ == '__main__':
    unittest.main()

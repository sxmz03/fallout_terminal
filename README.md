# RobCo Terminal

A Fallout-inspired terminal setup for macOS and iTerm2: phosphor green colours,
custom heavy lettering, a Vault-Tec corner logo, animated GIF startup, a typed
welcome message and a three-line prompt.

## Requirements

- macOS with **iTerm2 3.5 or newer** (the animation uses multipart inline images).
- Python **3.9 or newer**, available as `python3` when installing.
- macOS's built-in `/bin/zsh`. Git is optional for prompt Git information.

No Oh My Zsh, Python packages, administrator access or installer downloads are
required. Installation is local; the installer does not access the network.

## Install

Download this repository as a ZIP and extract it, or clone it with Git. Open a
terminal in the extracted repository and run:

```sh
./install.sh
```

Then open **iTerm2 → Profiles → RobCo Terminal**. Allow the background image if
iTerm2 requests permission. The installer adds a separate dynamic profile and
keeps your existing profiles, default profile, `.zshrc` and Oh My Zsh installation.
You can choose RobCo as your default yourself in iTerm2 Settings → Profiles.

The repository URL is deliberately not hardcoded: after publishing, use the
Clone button on your GitHub repository to get its actual URL.

The installer copies the runtime into:

```text
~/Library/Application Support/RobCo Terminal/
```

It also installs:

```text
~/Library/Application Support/iTerm2/DynamicProfiles/RobCo-Terminal.json
~/Library/Fonts/RobCoCaseHeavy-Regular.ttf
```

The downloaded repository can then be moved or deleted. Keep the installed
Application Support folder in place. The generated profile contains paths for
**your** account, so run the installer on each Mac rather than copying its
already-generated profile JSON.

## What you get

- Green `#66FF33` text on dark `#030A05`, with a blinking block cursor.
- RobCoCaseHeavy at size 22, with normal character spacing and ASCII smoothing off.
- Lowercase ASCII displayed as capitals; actual uppercase letters have a short
  underline. This affects glyph appearance, not the text you type or copy.
- A green-tinted GIF played once, a final-frame pause, and a letter-by-letter
  `Welcome to ROBCO Industries (TM) Termlink...` with slower final dots.
- A small green Vault-Tec logo at the top right after playback.
- Random bracketed hex header, identity, clock, exit status and command duration;
  directory and Git details; boxed `[>]` input marker and black-on-green input.

Username, hostname, directories and Git details reflect the current machine.
Logo proportions follow the pane's aspect ratio. Different display scaling or
pane sizes can change the apparent size; this is the same rendering approach as
the original setup. Windows initially request 110 columns and 32 rows.

## Shell configuration

RobCo uses its own zsh startup directory so existing themes cannot replace its
prompt or play a second startup animation. It does **not** load your usual
`.zshrc`, `.zprofile` or Oh My Zsh plugins. System-wide zsh startup files still run.
Standard completion, Emacs-style editing and persistent history are included.

Put optional aliases and environment settings in:

```text
~/.config/robco-terminal/local.zsh
```

Do not source an entire existing theme from that file if you want RobCo's prompt
to remain intact. History and completion caches live in the same config directory
and are preserved on removal.

To skip the animation for a session, run `export ROBCO_NO_ANIMATION=1` before
starting a nested RobCo shell. For a persistent setting, add a `.zshenv` file in
the installed `shell/` directory containing `export ROBCO_NO_ANIMATION=1`.
The welcome message and logo still appear. Small panes also skip GIF playback.

## Remove or reinstall

Finish work in RobCo tabs and close those tabs yourself before removal. From
another terminal, run this from the repository:

```sh
./install.sh --uninstall
```

If you deleted the repository, download it again to obtain the uninstall command.
The uninstaller removes the profile and managed runtime files. A font that was
already installed with identical contents is retained. History, personal config
and extra files are retained. If a managed file or profile has changed, removal
stops before deleting anything; back up your edits and restore the original file
before trying again. If extra files leave the install directory behind, move that
folder aside before reinstalling.

Running the installer again verifies an existing installation and leaves it in
place. To apply a newer release, uninstall the old version, then install the new
one. Python's installed path is recorded for playback; reinstall after moving or
removing that Python installation.

## Troubleshooting and verification

- Missing profile: check iTerm2's dynamic-profile errors and the generated JSON.
  Restart iTerm2 after finishing active work if it has not picked up the profile.
- Missing logo: allow its image permission in iTerm2 and open a fresh RobCo tab.
- Missing GIF: use iTerm2 3.5+, a pane at least 70 × 20, and a direct local session.
  Animation is skipped inside tmux/screen or when `ROBCO_NO_ANIMATION` is set.
- Wrong lettering: confirm `RobCoCaseHeavy-Regular 22` in the profile. If the
  font is newly installed, restart iTerm2 after finishing active work.

Developer checks:

```sh
python3 -m unittest discover -s tests -v
```

These exercise installation/removal in temporary home directories, conflicts,
rollback, standalone prompt loading and GIF processing. They do not verify
macOS font registration, actual iTerm2 rendering, image permission or full
quit/relaunch persistence. A fresh-Mac visual check remains required for those.

## Credits and assets

The custom font is a modified VT323 by The VT323 Project Authors, distributed
under the included [SIL Open Font License](payload/fonts/OFL.txt).
See [ASSETS.md](ASSETS.md) for artwork provenance and licensing scope.

The installation format follows iTerm2's
[Dynamic Profiles documentation](https://iterm2.com/documentation-dynamic-profiles.html).

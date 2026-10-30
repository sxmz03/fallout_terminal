"""Play the startup GIF, then reveal the first prompt letter by letter."""
import base64
import fcntl
import os
import re
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import termios
import time


BOOT_MESSAGE = 'Welcome to ROBCO Industries (TM) Termlink...'


def reveal_prompt(header, write, dot_delay=None):
    # Send colour/control sequences atomically; delay only visible characters.
    tokens = re.findall(r'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07)|.',
                        header, re.DOTALL)
    for token in tokens:
        write('\r\n' if token == '\n' else token)
        if not token.startswith('\x1b') and token.isprintable():
            time.sleep(dot_delay if token == '.' and dot_delay is not None else 0.030)


def image_sequence(data, width, height):
    # Multipart keeps each OSC below iTerm2's per-sequence size limit (3.5+).
    encoded = base64.b64encode(data).decode('ascii')
    header = (f'\033]1337;MultipartFile=inline=1;size={len(data)};'
              f'width={width};height={height};preserveAspectRatio=1\a')
    parts = ''.join('\033]1337;FilePart=' + encoded[i:i+65536] + '\a'
                    for i in range(0, len(encoded), 65536))
    return header + parts + '\033]1337;FileEnd\a'


def placement(data, columns, rows, cell_ratio, reserved_rows=0):
    if data[:6] not in (b'GIF87a', b'GIF89a'):
        raise ValueError('Not a GIF')
    pixels_w, pixels_h = struct.unpack('<HH', data[6:10])
    # Four times the previous 32-column / 12-row bounds, fitting the splash.
    max_w = min(128, columns - 4)
    max_h = max(1, min(48, rows - max(4, reserved_rows)))
    aspect = pixels_w / pixels_h / cell_ratio
    width = max(1, min(max_w, round(max_h * aspect)))
    height = max(1, min(max_h, round(width / aspect)))
    return width, height, (rows-height)//2+1, (columns-width)//2+1


def green_palette(data):
    """Tint GIF colour tables #66FF33 without re-encoding animated frames."""
    result = bytearray(data)
    def tint(start, count):
        for pos in range(start, start + count * 3, 3):
            brightness = max(data[pos:pos + 3])
            result[pos:pos + 3] = bytes((round(brightness * 102 / 255),
                                       brightness, round(brightness * 51 / 255)))
    offset = 13
    if data[10] & 128:
        count = 2 ** ((data[10] & 7) + 1)
        tint(offset, count)
        offset += count * 3
    while offset < len(data):
        tag = data[offset]
        offset += 1
        if tag == 0x3B:
            return bytes(result)
        if tag == 0x21:
            offset += 1
        elif tag == 0x2C:
            packed = data[offset + 8]
            offset += 9
            if packed & 128:
                count = 2 ** ((packed & 7) + 1)
                tint(offset, count)
                offset += count * 3
            offset += 1
        else:
            raise ValueError('Invalid GIF block')
        while True:
            count = data[offset]
            offset += 1
            if not count:
                break
            offset += count
    raise ValueError('Missing GIF trailer')


def single_play_gif(data):
    """Remove loop metadata and keep the final frame displayed until cleanup."""
    if data[:6] not in (b'GIF87a', b'GIF89a'):
        raise ValueError('Not a GIF')
    offset = 13 + (3 * (2 ** ((data[10] & 7) + 1)) if data[10] & 128 else 0)
    output = bytearray(data[:offset])
    last_delay = None
    while offset < len(data):
        start = offset
        tag = data[offset]
        offset += 1
        if tag == 0x3B:
            output.extend(data[start:])
            # Some renderers repeat GIFs even without loop metadata. Keep the
            # last frame for ten seconds; splash cleanup removes it after the
            # requested visible pause, before any repeat can occur.
            if last_delay is not None:
                struct.pack_into('<H', output, last_delay, 1000)
            return bytes(output)
        if tag == 0x21:
            label = data[offset]
            offset += 1
            loop = label == 0xFF and data[offset + 1:offset + 12] in (
                b'NETSCAPE2.0', b'ANIMEXTS1.0')
        elif tag == 0x2C:
            packed = data[offset + 8]
            offset += 9
            if packed & 128:
                offset += 3 * 2 ** ((packed & 7) + 1)
            offset += 1  # LZW minimum code size
            loop = False
        else:
            raise ValueError('Invalid GIF block')
        while True:
            count = data[offset]
            offset += 1
            if not count:
                break
            offset += count
        if not loop:
            block = bytearray(data[start:offset])
            if tag == 0x21 and label == 0xF9:
                last_delay = len(output) + 4
            output.extend(block)
    raise ValueError('Missing GIF trailer')


def play(header=''):
    if (not sys.stdout.isatty() or os.environ.get('ROBCO_NO_ANIMATION')
            or os.environ.get('TERM_PROGRAM') != 'iTerm.app'
            or os.environ.get('TMUX') or os.environ.get('STY')):
        return
    size = shutil.get_terminal_size()
    if size.columns < 70 or size.lines < 20:
        return
    data = single_play_gif(green_palette(
        (Path(__file__).resolve().parent / 'standard.gif').read_bytes()))
    ratio = .5
    try:
        rows, cols, xpixels, ypixels = struct.unpack('HHHH', fcntl.ioctl(
            sys.stdout.fileno(), termios.TIOCGWINSZ, b'\0' * 8))
        if all((rows, cols, xpixels, ypixels)):
            ratio = (xpixels / cols) / (ypixels / rows)
    except OSError:
        pass
    header_rows = header.count('\n') + 1 if header else 0
    gap_rows = 4
    width, height, _, left = placement(
        data, size.columns, size.lines, ratio, header_rows + gap_rows + 2)
    # Reserve the entire splash before saving position, so scrolling cannot
    # invalidate the restore position when a new shell starts near the bottom.
    reserved = header_rows + height + gap_rows + 1
    out = sys.stdout
    def write(value):
        out.write(value)
        out.flush()
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    previous = {s: signal.signal(s, interrupted)
                for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGWINCH)}
    revealed = False
    try:
        write('\r' + '\n' * reserved + f'\033[{reserved}A\r\0337\033[?25l')
        # Keep the prompt area blank until playback and the final pause finish.
        write('\n' * (header_rows + gap_rows))
        # Leave the cursor below the image while iTerm2 plays the GIF once at normal speed.
        write(f'\033[{left}G' + image_sequence(data, width, height)
              + f'\0338\033[{reserved}B\r')
        start = time.monotonic()
        # Play the 1.60-second cycle, then hold its final frame for 1.5 seconds.
        while time.monotonic() - start < 3.1:
            if shutil.get_terminal_size() != size:
                break
            time.sleep(1 / 30)
        write('\0338\033[J')
        # Restore the image immediately after playback, before typing the prompt.
        subprocess.run(['/bin/zsh', str(Path(__file__).resolve().parent.parent
                                       / 'show-image-logo.zsh')], check=False)
        # Leave the welcome line above the origin used for zsh's prompt redraw.
        reveal_prompt('\033[0;32m' + BOOT_MESSAGE + '\033[0m', write, dot_delay=0.4)
        write('\r\n\r\n\0337')
        reveal_prompt(header, write)
        revealed = True
    except KeyboardInterrupt:
        pass
    finally:
        # Redraw the editable prompt at the same origin, without flashing away
        # the revealed text. No background writer can erase input.
        write('\033[0m\0338' + ('' if revealed else '\033[J') + '\033[?25h')
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    return True


if __name__ == '__main__':
    sys.exit(0 if play(sys.argv[1] if len(sys.argv) > 1 else '') else 2)

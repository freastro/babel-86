# Babel 86

A live AI translation box with the face of 1980s rack gear.

Speech goes in one audio device, out to a cloud speech-to-speech model
(Google Gemini or Alibaba's Qwen), and the translated speech comes back out
another audio device. Think of it as an effects unit: what goes in is your
voice, and what comes out is your voice in another language.

```
 mic / line in ──► [ Babel 86 ] ──► cloud model (Gemini | Qwen) ──► [ Babel 86 ] ──► speakers / line out
```

> **Status:** Milestone 2, the interactive front panel. Every control works by
> mouse, touch and keyboard, the setup dialog adds, edits and removes languages,
> and the rack is saved and restored after a restart. Output devices are a mock
> list and there is no audio or cloud code yet, so units show IDLE. See the
> [roadmap](#roadmap).

## Requirements

- Python 3.11 or newer, **with Tk**. Tk ships with the python.org installers
  for Windows and macOS. Some setups need it added:
  - Debian/Ubuntu: `sudo apt install python3-tk`
  - Fedora: `sudo dnf install python3-tkinter`
  - macOS with Homebrew Python: `brew install python-tk`
  - [uv](https://docs.astral.sh/uv/)-managed Pythons include Tk already.

  Check it with `python -m tkinter`; a small test window should open.

## Run it

With [uv](https://docs.astral.sh/uv/) (recommended):

```sh
uv run babel86
```

Or with plain pip and a virtual environment:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate   macOS/Linux: source .venv/bin/activate
pip install -e .
babel86            # or: python -m babel86
```

What you can do in this milestone:

- The first launch shows the input unit alone; press **ADD LANGUAGE OUTPUT**
  to add up to four languages. It opens the setup dialog in Add mode, filled
  in with the first language not yet in the rack, Gemini, the last unit's
  device, the next free channel and an unused colour.
- The rack starts with the power on, overriding `docs/design.md` until audio
  arrives. Press the power key to darken the displays.
- Press the power key, **MUTE INPUT** or a language's **MUTE** to latch them.
- Turn a knob by dragging it up or down, scrolling over it, or with the arrow
  keys (1 dB steps, **Shift** for 0.1 dB). Double-click resets it to 0 dB.
- **Keyboard:** **Tab** and **Shift+Tab** move a gold focus ring through every
  control; **Space** or **Enter** presses the focused key.
- **Touch:** taps, double taps and drags work like the mouse, and every target
  is at least 44 × 44 px.
- A language's **SETUP** opens the setup dialog in Edit mode. Choose the target
  language (only those the model can speak; ones already in the rack say IN
  RACK), the label (up to 24 characters; it follows the language until you
  type your own), the model, the output device and channel, and the colour. A
  channel another language already uses gets an amber warning. **Enter**
  confirms and **Esc** cancels. **REMOVE LANGUAGE** asks for a second press
  while the power is on.
- The input unit's SETUP does nothing yet.

The output devices are a mock list (Speakers, 2 channels; Interpreter Desk,
8 channels) until real audio devices arrive. A saved device that is missing
shows as "(disconnected)" and its unit reads ERROR.

### Saved rack

The rack is saved to `babel86.json` half a second after each change and when
the window closes, and loaded at launch:

- Windows: `%APPDATA%\babel86\babel86.json`
- macOS: `~/Library/Application Support/babel86/babel86.json`
- Linux: `$XDG_CONFIG_HOME/babel86/babel86.json` (default `~/.config`)

Power is never saved. A file that cannot be read is renamed to
`babel86.json.bad`, a warning is logged and the app starts empty; a single
out-of-range value is clamped or reset on its own.

Flags:

- `--display vfd|led|lcd` picks the display colour and saves it.
- `--config PATH` loads and saves another file, for experiments.
- `--units 1-4` shows the mock rack from the design canvas and saves nothing
  (dev, for screenshots).
- `--power-off` starts with the power off (dev).
- `--dialog add` or `--dialog edit:2` opens the dialog at launch (dev).

### Platforms and text

- **Windows and macOS** are the v1 targets. All text is drawn by Tk, which
  shapes complex scripts and falls back to a system font per character, so
  Khmer, Arabic, Hindi, CJK and Thai render correctly.
- **Linux** runs, but the bundled fonts are not registered (text uses a stock
  font) and Tk 8.6 probably cannot shape Khmer or Arabic there. This waits on
  Tk 9. See `docs/adr/0003-native-text-and-linux-best-effort.md`.
- **High DPI:** on Windows the app turns on per-monitor DPI awareness and scales
  the whole rack, shrinking it if it would not fit the screen. On macOS Tk 8.6
  draws images blurry on Retina, so knob and lamp sprites may look soft until
  Python ships Tk 9. The macOS look has not been checked on a real Mac.

## Develop

```sh
uv run pytest            # tests (GUI tests skip without a display)
uv run ruff check .      # lint
uv run ruff format .     # format
```

On a headless Linux box, run the GUI tests under a virtual display:
`xvfb-run uv run pytest`.

The rack's round parts (knobs, screws, lamps) are PNG sprites pre-rendered with
Pillow, because Tk's canvas cannot anti-alias or glow. Pillow is a dev-only
dependency and never ships. After changing `tools/make_sprites.py` or the
theme colours it uses:

```sh
uv run python tools/make_sprites.py          # regenerate the committed PNGs
uv run python tools/make_sprites.py --check  # what the tests run
```

## Fonts

Michroma, Archivo Narrow and Share Tech Mono are bundled in
`src/babel86/assets/fonts` under the SIL Open Font License 1.1. The licence
texts sit next to the fonts. Archivo Narrow Regular and Bold are static
instances cut from Google's variable font by `tools/make_static_fonts.py`.

## Project layout

```
src/babel86/
  app.py        window, DPI, command line, dialog opening, debounced saving
  rack.py       the rack canvas: drawing from state, hit testing, input, focus
  dialogs.py    language setup dialog and its dropdown popup
  state.py      rack state, dialog rules, mock rack and the rules derived from it
  languages.py  target languages and which models speak them (pure)
  devices.py    output devices; a mock list until audio arrives (pure)
  persist.py    babel86.json: load, validate, atomic save (pure)
  layout.py     rack geometry as a function of window size (pure)
  meters.py     dB, knob and meter maths (pure)
  textfit.py    wrapping and ellipsis for any script (pure)
  theme.py      colours, type and dimensions
  fonts.py      private font registration and the Tk font cache
  assets.py     sprite loading
  widgets/      knob, meter, button, ear, panel drawing helpers
  assets/       bundled fonts and pre-rendered sprites
tools/          sprite and font generators (dev only)
tests/          pytest suite
docs/           design spec and architecture decisions
```

## Roadmap

1. **Audio I/O.** Pick input and output devices, show levels on a VU meter.
   Likely [`sounddevice`](https://python-sounddevice.readthedocs.io/)
   (PortAudio), which works on Windows, macOS, and Linux.
2. **First provider.** Stream audio to one cloud model and play the
   translation back.
3. **Second provider.** The same, behind a common interface, with a front-panel
   selector.
4. **The Input Setup dialog.** Source device, channel and language.
5. **Packaging.** Standalone builds (for example, PyInstaller or Briefcase)
   so users don't need Python installed.

## Providers

- **Google Gemini**, through the Gemini Live API, which streams audio in both
  directions.
- **Qwen**, the model family from Alibaba. Its API is served by Alibaba Cloud
  Model Studio (also called DashScope). Qwen has live speech-translation
  models.

Each provider needs its own API key, and each bills for usage. See
`.env.example` for the variable names.

## License

[MIT](LICENSE) © 2026 Gregory Hart.

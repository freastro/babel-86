# Babel 86

A live AI translation box with the face of 1980s rack gear.

Speech goes in one audio device, out to a cloud speech-to-speech model
(Google Gemini or Alibaba's Qwen), and the translated speech comes back out
another audio device. Think of it as an effects unit: what goes in is your
voice, and what comes out is your voice in another language.

```
 mic / line in ──► [ Babel 86 ] ──► cloud model (Gemini | Qwen) ──► [ Babel 86 ] ──► speakers / line out
```

> **Status:** Milestone 1, the front panel. The app shows the full rack from
> `docs/design.md` driven by mock data. Power, mutes and knobs change in memory
> only, and the language setup dialog is display-only. There is no audio, cloud
> code or saving yet. See the [roadmap](#roadmap).

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

- The rack starts with the power off, as the design requires. Click the power
  key to light the displays.
- Click the power key, **MUTE INPUT** or a language's **MUTE** to latch them.
- Turn a knob by dragging it up or down, scrolling over it, or clicking it and
  using the arrow keys (1 dB steps, **Shift** for 0.1 dB). Double-click resets
  it to 0 dB.
- Click a language's **SETUP** or **ADD LANGUAGE OUTPUT** to see the setup
  dialog; the rack dims behind it. **Esc** or **Cancel** closes it and returns
  to the rack. The input unit's SETUP does nothing yet.

Dev flags: `--display vfd|led|lcd`, `--units 1-4`, `--power-on`, and
`--dialog add` or `--dialog edit:2` to open the dialog at launch (handy for
screenshots).

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
  app.py        window, DPI, command line, dialog opening
  rack.py       the rack canvas: drawing from state, hit testing, input
  dialogs.py    language setup dialog (display-only for now)
  state.py      rack state, mock data and the rules derived from it
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
4. **Saving and the Input Setup dialog.** Working setup fields and a saved
   rack.
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

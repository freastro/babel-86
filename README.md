# Babel 86

A live AI translation box with the face of 1980s rack gear.

Speech goes in one audio device, out to a cloud speech-to-speech model
(Google Gemini or Alibaba's Qwen), and the translated speech comes back out
another audio device. Think of it as an effects unit: what goes in is your
voice, and what comes out is your voice in another language.

```
 mic / line in ──► [ Babel 86 ] ──► cloud model (Gemini | Qwen) ──► [ Babel 86 ] ──► speakers / line out
```

> **Status:** foundation only. The app opens a hello-world faceplate and has
> no audio or cloud code yet. See the [roadmap](#roadmap).

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

Click the toggle switch or press **Space** to switch power. **Esc** quits.

## Develop

```sh
uv run pytest            # tests (the GUI test skips without a display)
uv run ruff check .      # lint
uv run ruff format .     # format
```

On a headless Linux box, run the GUI test under a virtual display:
`xvfb-run uv run pytest`.

## Project layout

```
src/babel86/
  __init__.py   version
  __main__.py   python -m babel86
  app.py        window and faceplate
  theme.py      colors, fonts, panel dimensions
tests/          pytest suite
```

## Roadmap

1. **Audio I/O.** Pick input and output devices, show levels on a VU meter.
   Likely [`sounddevice`](https://python-sounddevice.readthedocs.io/)
   (PortAudio), which works on Windows, macOS, and Linux.
2. **First provider.** Stream audio to one cloud model and play the
   translation back.
3. **Second provider.** The same, behind a common interface, with a front-panel
   selector.
4. **Front panel.** Language selectors, input/output gain, bypass, and a
   status display.
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

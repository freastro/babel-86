# CLAUDE.md

Guidance for Claude Code (and other contributors) working in this repo.

## What this is

Babel 86 is a desktop app that acts like an audio effects unit for live
translation: audio in → cloud speech-to-speech model (Google Gemini or
Alibaba's Qwen) → translated audio out. The UI imitates 1970s–80s rack gear
(amps, compressors, effects racks). The project is at the foundation stage:
a Tk hello-world faceplate, no audio or network code yet.

## Stack and constraints

- Python 3.11+, `src/` layout, package `babel86`, built with hatchling.
- GUI is **Tkinter only**: drawn on `tk.Canvas` to get the hardware look.
  Don't add another GUI toolkit.
- Must run on Windows, macOS, and Linux. Use `pathlib`, and don't call
  shell commands or OS-specific APIs without a fallback.
- The project has no runtime dependencies so far. Add one only when a
  feature needs it, and say why in the commit message.
- No CI yet. Run the checks below locally before committing.

## Commands

```sh
uv run babel86          # launch the app
uv run pytest           # tests; GUI test skips with no display
xvfb-run uv run pytest  # headless Linux, GUI test included
uv run ruff check .     # lint
uv run ruff format .    # format
```

## Conventions

- Colors, fonts, and panel dimensions belong in `theme.py`, not inline in
  drawing code.
- Keep UI code (Tk) apart from audio and provider code, so audio and
  network logic can be tested without a display.
- Tk is single-threaded. Audio callbacks and network streams run on other
  threads or in asyncio, and they must hand results to the UI through
  `root.after(...)` or a queue. They must never touch widgets directly.
- Providers (Gemini, Qwen) should sit behind one common interface so the
  front panel can switch between them.
- API keys come from environment variables (`GEMINI_API_KEY`,
  `DASHSCOPE_API_KEY`) or the OS keychain. Never hard-code, log, or commit
  them.
- The license is MIT (copyright Gregory Hart). Only add code, assets, or
  dependencies whose licenses are compatible with it, such as MIT, BSD,
  Apache-2.0, or public domain. Avoid GPL-family code.

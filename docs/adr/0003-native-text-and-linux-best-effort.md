---
status: accepted
---

# Render all text with native Tk fonts; Linux is best-effort

The app must support every language, including complex scripts such as Khmer and Arabic. None of the design fonts (Michroma, Archivo Narrow, Share Tech Mono) covers them, and no single bundled font does either. All text is therefore drawn by Tk, which anti-aliases, shapes and falls back per character through the OS. The bundled design fonts are used for Chrome only, and user content (Transcript, Translation, language names, device names) uses the design font first, then OS fallback.

Shaping works on Windows and macOS but, with the Tk 8.6 that ships with Python 3.13, is likely missing on Linux. Windows and macOS are the v1 targets. Linux runs but complex scripts may render unshaped, and the README says so until Tk 9 is available.

## Considered Options

- **Bundle Noto fonts**: hundreds of MB, and does not fix Linux shaping because shaping is done by Tk, not the font.
- **Render text with Pillow and Raqm**: Pillow's Windows wheels need a separate `fribidi.dll`.

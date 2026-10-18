---
status: accepted
---

# Pre-render sprites at build time; Pillow is dev-only

Tk's canvas cannot draw anti-aliased circles, glows, radial gradients or inset shadows, which the design depends on. We render these as PNG sprites with Pillow in `tools/make_sprites.py` and commit them, at 1x, 1.25x, 1.5x, 2x and 3x scales. The app loads them with `tk.PhotoImage`, so Pillow is never imported at runtime and does not ship (its wheel is about 7 MB to download and 14 MB on disk, mostly unused codecs).

Shapes whose size or angle change (panel gradients, knob pointers, meter segments) use plain canvas primitives. On macOS Retina, Tk 8.6 draws photo images blurry, so Retina-sensitive shapes (screws, LEDs, knob rings) stay as canvas primitives and glows and shadows may look soft until Python ships Tk 9.

## Considered Options

- **Pure `tk.Canvas`**: no extra tooling, but jagged circles and no glows.
- **Pillow at runtime**: sprites sized on demand, but adds a shipped dependency.

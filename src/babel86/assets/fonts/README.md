# Bundled fonts

| Font | File | Licence | Source |
| --- | --- | --- | --- |
| Michroma | `Michroma-Regular.ttf` | SIL OFL 1.1, `OFL-michroma.txt` | https://github.com/google/fonts/tree/main/ofl/michroma |
| Share Tech Mono | `ShareTechMono-Regular.ttf` | SIL OFL 1.1, `OFL-sharetechmono.txt` | https://github.com/google/fonts/tree/main/ofl/sharetechmono |
| Archivo Narrow | `ArchivoNarrow-Regular.ttf`, `ArchivoNarrow-Bold.ttf` | SIL OFL 1.1, `OFL-archivonarrow.txt` | https://github.com/google/fonts/tree/main/ofl/archivonarrow |

The two Archivo Narrow files are static instances (wght 400 and 700) cut from the
upstream variable font by `tools/make_static_fonts.py`, because Tk cannot choose
weights from a variable font. The font declares no Reserved Font Name.

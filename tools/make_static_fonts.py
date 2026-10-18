"""Cut static Archivo Narrow Regular and Bold fonts from Google's variable font.

Tk 8.6 on Windows and macOS cannot pick weights out of a variable font, so the app
bundles two static instances. Run this only when updating the bundled font:

    pip install fonttools
    python tools/make_static_fonts.py path/to/ArchivoNarrow[wght].ttf

The source is https://github.com/google/fonts/tree/main/ofl/archivonarrow (SIL OFL 1.1).
"""

import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

OUT = Path(__file__).resolve().parents[1] / "src" / "babel86" / "assets" / "fonts"
WEIGHTS = {"Regular": 400, "Bold": 700}


def main(source: str) -> int:
    for style, wght in WEIGHTS.items():
        font = TTFont(source)
        static = instantiateVariableFont(font, {"wght": wght}, updateFontNames=True)
        dest = OUT / f"ArchivoNarrow-{style}.ttf"
        static.save(dest)
        print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))

"""Colors, fonts, and dimensions for the rack-unit look.

Everything visual lives here so the faceplate code stays about layout, not
paint. Fonts use family names Tk maps on every platform.
"""

# Panel
PANEL = "#1b1b1d"  # black anodized faceplate
PANEL_EDGE = "#3a3a3e"
EAR = "#2a2a2e"  # rack ears
SCREW = "#8a8a90"
SCREW_SLOT = "#3a3a3e"

# Silkscreen
INK = "#e8e2d0"  # off-white panel lettering
INK_DIM = "#8f8a7c"
ACCENT = "#ff7a1a"  # 80s orange stripe

# Vacuum fluorescent display
VFD_BG = "#050a09"
VFD_ON = "#5ff5d2"
VFD_OFF = "#10221e"

# Pilot lamp
LAMP_ON = "#ff2a1a"
LAMP_GLOW = "#5a120c"
LAMP_OFF = "#3a1410"

# Fonts
LOGO_FONT = ("Helvetica", 30, "bold italic")
LABEL_FONT = ("Helvetica", 8, "bold")
SUBTITLE_FONT = ("Helvetica", 9, "bold")
VFD_FONT = ("Courier", 22, "bold")

# Geometry: a 2U panel is roughly 19" x 3.5", i.e. about 5.4:1.
WIDTH = 900
HEIGHT = 170
EAR_WIDTH = 40
DISPLAY_BOX = (360, 42, 700, 112)  # x0, y0, x1, y1 of the VFD window

# Recessed black wells (VFD bezel, switch slot, lamp rim)
WELL = "#000000"

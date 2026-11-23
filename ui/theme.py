"""SPECTRA theme: the Cosmic Gold palette, screen scaling and fonts.

Every color in the app comes from this file, so the whole look can be tuned in one place.
All sizes go through px() and all fonts through font(), which keeps the layout correct on
high-DPI laptop screens (for example Windows display scaling at 125% or 150%).
"""
import sys
import tkinter as tk
from tkinter import font as tkfont

# --- Brand palette: names and hex codes taken from the supplied color map -------------------
VOID_NAVY = "#0B1020"        # 01  main background / brand foundation
CHAMPAGNE_GOLD = "#E3C58B"   # 02  primary accent, actions, highlights
DEEP_COSMOS = "#151C2E"      # 03  sidebar, main surfaces
ORBIT_SLATE = "#202A40"      # 04  cards, elevated UI
NEBULA_VIOLET = "#8A79B8"    # 05  decorative accents
AURORA_TEAL = "#5D9F9A"      # 06  interactive states (focus)
SOLAR_CHAMPAGNE = "#F0CC83"  # 07  highlights, hover
ANCIENT_BRONZE = "#9C7945"   # 08  borders, details
MOON_DUST = "#F2EFE8"        # 09  text, light surfaces
COSMIC_ASH = "#A9ADBB"       # 10  secondary text


def hex_to_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def blend(color_a, color_b, amount):
    """Mix two palette colors. amount=0 gives color_a, amount=1 gives color_b."""
    a, b = hex_to_rgb(color_a), hex_to_rgb(color_b)
    mixed = tuple(round(x + (y - x) * amount) for x, y in zip(a, b))
    return "#%02X%02X%02X" % mixed


# --- Role names used by the UI code ----------------------------------------------------------
BG = VOID_NAVY
SIDEBAR = DEEP_COSMOS
CARD = ORBIT_SLATE
TEXT = MOON_DUST
TEXT_DIM = COSMIC_ASH
ACCENT = CHAMPAGNE_GOLD
ACCENT_HOVER = SOLAR_CHAMPAGNE
FOCUS = AURORA_TEAL

# Tints derived from palette colors (so no unrelated colors sneak in)
HAIRLINE = blend(ORBIT_SLATE, COSMIC_ASH, 0.16)        # thin borders and dividers
SURFACE_HOVER = blend(ORBIT_SLATE, NEBULA_VIOLET, 0.20)  # hovered cards, rows and chips

# --- Scaling and fonts -----------------------------------------------------------------------
SCALE = 1.0
DISPLAY_FAMILY = "Times New Roman"
BODY_FAMILY = "Arial"
_root = None
_font_cache = {}

_DISPLAY_CANDIDATES = ["Cormorant Garamond", "Palatino Linotype", "Book Antiqua", "Georgia",
                       "DejaVu Serif", "Times New Roman", "Times"]
_BODY_CANDIDATES = ["Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue",
                    "Inter", "DejaVu Sans", "Arial", "Helvetica"]


def enable_dpi_awareness():
    """Ask Windows not to bitmap-stretch the window (call before creating the Tk root)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass  # older Windows: the app still works, just not DPI-sharp


def init(root):
    """Measure the screen scale and pick fonts. Call once, right after creating the Tk root."""
    global SCALE, DISPLAY_FAMILY, BODY_FAMILY, _root
    _root = root
    try:
        SCALE = max(1.0, min(2.5, root.winfo_fpixels("1i") / 96.0))
    except tk.TclError:
        SCALE = 1.0
    installed = {name.lower(): name for name in tkfont.families(root)}
    DISPLAY_FAMILY = next((installed[c.lower()] for c in _DISPLAY_CANDIDATES if c.lower() in installed),
                          DISPLAY_FAMILY)
    BODY_FAMILY = next((installed[c.lower()] for c in _BODY_CANDIDATES if c.lower() in installed),
                       BODY_FAMILY)


def px(value):
    """Convert a design pixel size to real pixels for this screen."""
    return int(round(value * SCALE))


def font(size, weight="normal", display=False, slant="roman"):
    """A cached font. 'size' is in design pixels; display=True uses the elegant serif face."""
    key = (size, weight, display, slant)
    if key not in _font_cache:
        _font_cache[key] = tkfont.Font(root=_root, family=DISPLAY_FAMILY if display else BODY_FAMILY,
                                       size=-px(size), weight=weight, slant=slant)
    return _font_cache[key]


def dark_title_bar(window):
    """Use Windows' dark title bar so dialogs match the theme (purely cosmetic, Windows 10/11 only)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        enabled = ctypes.c_int(1)
        for attribute in (20, 19):  # 20 on current Windows builds, 19 on early Windows 10
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(enabled),
                                                          ctypes.sizeof(enabled)) == 0:
                break
    except (AttributeError, OSError):
        pass  # cosmetic only

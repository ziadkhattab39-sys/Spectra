"""Image helpers for the UI: anti-aliased shapes, thumbnails and a background loader.

Tkinter cannot draw smooth rounded shapes or open JPEGs by itself, so Pillow (already used by
Images.py) renders them and Tk just displays the result.
"""
import os
import queue
import sys
import threading
import traceback
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image as PILImage, ImageChops, ImageDraw, ImageOps, ImageTk

from . import theme

RESAMPLE = PILImage.Resampling.LANCZOS if hasattr(PILImage, "Resampling") else PILImage.LANCZOS
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# Errors that simply mean "this file is unreadable" (not programming mistakes)
EXPECTED_IMAGE_ERRORS = (OSError, ValueError, SyntaxError, PILImage.DecompressionBombError)


def _rgba(color):
    """'#RRGGBB' or an (r, g, b, a) tuple -> (r, g, b, a)."""
    if isinstance(color, tuple):
        return color if len(color) == 4 else color + (255,)
    return theme.hex_to_rgb(color) + (255,)


# --- Sizes and ratios --------------------------------------------------------------------------
def parse_ratio(text):
    """'16:9' -> 0.5625 (height divided by width). Returns None when the text is not a ratio."""
    try:
        width, height = str(text).split(":")
        width, height = float(width), float(height)
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return height / width


_size_cache = {}


def peek_size(path):
    """(width, height) as the photo is displayed (EXIF rotation applied), or None if unreadable."""
    key = str(path)
    if key not in _size_cache:
        try:
            with PILImage.open(key) as im:
                width, height = im.size
                if im.getexif().get(0x0112) in (5, 6, 7, 8):  # rotated 90 degrees by the camera
                    width, height = height, width
            _size_cache[key] = (width, height)
        except EXPECTED_IMAGE_ERRORS:
            _size_cache[key] = None
    return _size_cache[key]


def ratio_for(image):
    """height/width for an Image object: the stored Aspect_Ratio when present, else read from the file."""
    ratio = parse_ratio(image.Aspect_Ratio)
    if ratio is None:
        size = peek_size(image.Img_Path)
        ratio = size[1] / size[0] if size else None
    return ratio


# --- Smooth shapes -----------------------------------------------------------------------------
def rounded_mask(size, radius, ss=3):
    """An anti-aliased rounded-rectangle alpha mask (mode 'L')."""
    width, height = size
    big = PILImage.new("L", (width * ss, height * ss), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, width * ss - 1, height * ss - 1), radius=radius * ss, fill=255)
    return big.resize((width, height), RESAMPLE)


def _ring(big_size, radius, color, line_width):
    """Rounded outline drawn at supersampled size (returned un-shrunk)."""
    outer = PILImage.new("L", big_size, 0)
    ImageDraw.Draw(outer).rounded_rectangle((0, 0, big_size[0] - 1, big_size[1] - 1), radius=radius, fill=255)
    inner = PILImage.new("L", big_size, 0)
    ImageDraw.Draw(inner).rounded_rectangle((line_width, line_width, big_size[0] - 1 - line_width,
                                             big_size[1] - 1 - line_width),
                                            radius=max(radius - line_width, 0), fill=255)
    ring = PILImage.new("RGBA", big_size, _rgba(color))
    ring.putalpha(ImageChops.multiply(ImageChops.subtract(outer, inner), ring.getchannel("A")))
    return ring


_shape_cache = {}


def shape_photo(width, height, radius, fill=None, outline=None, outline_width=1, gradient=None):
    """A smooth rounded rectangle as a Tk image (used for buttons, chips, entries).

    fill / outline: '#RRGGBB' or (r, g, b, a). gradient: (top_color, bottom_color) instead of fill.
    The result is cached because many widgets share the same shapes.
    """
    key = (width, height, radius, fill, outline, outline_width, gradient)
    if key in _shape_cache:
        return _shape_cache[key]
    ss = 3
    big_size = (width * ss, height * ss)
    shape = PILImage.new("RGBA", big_size, (0, 0, 0, 0))
    outer = PILImage.new("L", big_size, 0)
    ImageDraw.Draw(outer).rounded_rectangle((0, 0, big_size[0] - 1, big_size[1] - 1), radius=radius * ss, fill=255)
    if gradient:
        top, bottom = gradient
        shape = PILImage.composite(PILImage.new("RGBA", big_size, _rgba(bottom)),
                                   PILImage.new("RGBA", big_size, _rgba(top)),
                                   PILImage.linear_gradient("L").resize(big_size))
        shape.putalpha(ImageChops.multiply(shape.getchannel("A"), outer))
    elif fill is not None:
        shape = PILImage.new("RGBA", big_size, _rgba(fill))
        shape.putalpha(ImageChops.multiply(shape.getchannel("A"), outer))
    if outline:
        shape = PILImage.alpha_composite(shape, _ring(big_size, radius * ss, outline, outline_width * ss))
    photo = ImageTk.PhotoImage(shape.resize((width, height), RESAMPLE))
    _shape_cache[key] = photo
    return photo


_logo_cache = {}


def load_logo(height):
    """The official gold logo mark (transparent PNG), trimmed of empty margin and scaled to 'height' px."""
    if height not in _logo_cache:
        mark = PILImage.open(ASSETS_DIR / "logo_mark.png").convert("RGBA")
        mark = mark.crop(mark.getchannel("A").getbbox())
        width = max(1, round(mark.width * height / mark.height))
        _logo_cache[height] = ImageTk.PhotoImage(mark.resize((width, height), RESAMPLE))
    return _logo_cache[height]


def window_icon():
    """The app icon for the window title bar."""
    return ImageTk.PhotoImage(PILImage.open(ASSETS_DIR / "app_icon.png").convert("RGBA").resize((256, 256), RESAMPLE))


# --- Loading photos ----------------------------------------------------------------------------
def _flatten(im):
    """Photos with transparency are placed on a card-colored background."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        base = PILImage.new("RGBA", im.size, _rgba(theme.ORBIT_SLATE))
        return PILImage.alpha_composite(base, im).convert("RGB")
    return im.convert("RGB")


def load_scaled(path, side):
    """Open a photo, apply its EXIF rotation and shrink it so its longest side is at most 'side' px."""
    with PILImage.open(path) as im:
        im.draft("RGB", (side, side))  # lets Pillow decode JPEGs at reduced size (much faster)
        im = ImageOps.exif_transpose(im)
        im.thumbnail((side, side), RESAMPLE)
        return _flatten(im)


def load_full(path):
    """A large version of the photo for the viewer (longest side capped at 2400 px)."""
    return load_scaled(path, 2400)


def make_card_image(base, size, radius):
    """A card-sized rounded picture: the photo fitted inside (never stretched) on the card color."""
    width, height = size
    card = PILImage.new("RGBA", (width, height), _rgba(theme.ORBIT_SLATE))
    if base is not None:
        fitted = ImageOps.contain(base, (width, height), RESAMPLE)
        card.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    card.putalpha(rounded_mask((width, height), radius))
    return card


_overlay_cache = OrderedDict()


def hover_overlay_photo(width, height, radius):
    """Transparent overlay for a hovered card: dark fade at the bottom for text plus a gold outline."""
    key = (width, height, radius)
    if key in _overlay_cache:
        _overlay_cache.move_to_end(key)
        return _overlay_cache[key]
    overlay = PILImage.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    fade_height = min(height, max(theme.px(96), int(height * 0.45)))
    void = theme.hex_to_rgb(theme.VOID_NAVY)
    for step in range(fade_height):
        alpha = int(230 * (step / fade_height) ** 1.5)
        y = height - fade_height + step
        draw.line([(0, y), (width, y)], fill=void + (alpha,))
    overlay.putalpha(ImageChops.multiply(overlay.getchannel("A"), rounded_mask((width, height), radius)))
    ss = 3
    ring = _ring((width * ss, height * ss), radius * ss, theme.CHAMPAGNE_GOLD, max(2, theme.px(2)) * ss)
    overlay = PILImage.alpha_composite(overlay, ring.resize((width, height), RESAMPLE))
    photo = ImageTk.PhotoImage(overlay)
    _overlay_cache[key] = photo
    while len(_overlay_cache) > 24:
        _overlay_cache.popitem(last=False)
    return photo


# --- Background loader -------------------------------------------------------------------------
class ThumbnailService:
    """Loads photos on worker threads so the window never freezes while scrolling.

    Workers only produce Pillow images; the results are handed back to the Tk thread through a
    queue (Tkinter must only be touched from its own thread).
    """
    BASE_SIDE = 560
    BASE_CACHE_LIMIT = 120

    def __init__(self, root):
        self.root = root
        self._pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="spectra-loader")
        self._results = queue.Queue()
        self._base_cache = OrderedDict()
        self._lock = threading.Lock()
        self._closed = False
        self._poll_job = None
        self._poll()

    def submit(self, work, callback):
        """Run work() on a background thread, then call callback(result) on the Tk thread.

        callback receives None if the work failed (an unreadable photo, for example).
        """
        if not self._closed:
            self._pool.submit(self._run, work, callback)

    def _run(self, work, callback):
        try:
            result = work()
        except EXPECTED_IMAGE_ERRORS:
            result = None
        except Exception:
            traceback.print_exc(file=sys.stderr)  # a real bug: make it visible, do not swallow it
            result = None
        self._results.put((callback, result))

    def _poll(self):
        try:
            while True:
                callback, result = self._results.get_nowait()
                try:
                    callback(result)
                except Exception:
                    traceback.print_exc(file=sys.stderr)
        except queue.Empty:
            pass
        if not self._closed:
            self._poll_job = self.root.after(30, self._poll)

    def render_card(self, path, size, radius):
        """(card_image, photo_was_readable) for one gallery card. Runs on a worker thread."""
        base = self._get_base(path)
        return make_card_image(base, size, radius), base is not None

    def _get_base(self, path):
        key = str(path)
        try:
            cache_key = (key, os.path.getmtime(key))
        except OSError:
            return None  # file is missing
        with self._lock:
            base = self._base_cache.get(cache_key)
            if base is not None:
                self._base_cache.move_to_end(cache_key)
                return base
        try:
            base = load_scaled(key, self.BASE_SIDE)
        except EXPECTED_IMAGE_ERRORS:
            return None
        with self._lock:
            self._base_cache[cache_key] = base
            while len(self._base_cache) > self.BASE_CACHE_LIMIT:
                self._base_cache.popitem(last=False)
        return base

    def close(self):
        self._closed = True
        if self._poll_job is not None:
            try:
                self.root.after_cancel(self._poll_job)
            except Exception:
                pass
        self._pool.shutdown(wait=False, cancel_futures=True)

"""The first screen: the official SPECTRA artwork with the two starting choices."""
import math
import tkinter as tk

from PIL import Image as PILImage, ImageTk

from . import imaging, theme
from .theme import px
from .widgets import CanvasButton

ART_WIDTH, ART_HEIGHT = 1536, 1024
TAGLINE_Y = 727   # where "DISCOVER THE UNSEEN." sits inside the artwork (in its own pixels)


class StartupScreen(tk.Frame):
    """Full-window artwork (the supplied logo lockup, scaled evenly, never stretched) plus two buttons."""

    def __init__(self, parent, on_view_existing, on_create_new):
        super().__init__(parent, bg=theme.VOID_NAVY)
        self.on_view_existing, self.on_create_new = on_view_existing, on_create_new
        self.art = PILImage.open(imaging.ASSETS_DIR / "wordmark_lockup.png").convert("RGB")
        self.canvas = tk.Canvas(self, bg=theme.VOID_NAVY, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._photo = None
        self._buttons = []
        self._redraw_job = None
        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        if self._redraw_job:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(50, self._redraw)

    def _redraw(self):
        self._redraw_job = None
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        # "Cover" scaling: one uniform scale factor, then crop the overflow (proportions are preserved).
        scale = max(width / ART_WIDTH, height / ART_HEIGHT)
        scaled_size = (math.ceil(ART_WIDTH * scale), math.ceil(ART_HEIGHT * scale))
        left = (scaled_size[0] - width) // 2
        top = int((scaled_size[1] - height) * 0.35)  # crop a little more from the bottom than the top
        picture = self.art.resize(scaled_size, imaging.RESAMPLE).crop((left, top, left + width, top + height))
        self._photo = ImageTk.PhotoImage(picture)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        button_height, gap = px(52), px(18)
        tagline = TAGLINE_Y * scale - top
        center_y = int(min(tagline + px(88), height - px(60)))
        center_x = width // 2
        button_width = px(268)
        self._buttons = [
            CanvasButton(self.canvas, center_x - button_width // 2 - gap // 2, center_y, "View Existing Gallery",
                         self.on_view_existing, style="primary", width=268, height=52),
            CanvasButton(self.canvas, center_x + button_width // 2 + gap // 2, center_y, "Create New Gallery",
                         self.on_create_new, style="secondary", width=268, height=52),
        ]

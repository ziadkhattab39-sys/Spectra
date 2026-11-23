"""The photo wall: a scrolling masonry layout that never crops or stretches a photo.

Each photo keeps its own proportions (taken from Image.Aspect_Ratio, or read from the file when
that is empty) and every card is placed in the currently shortest column. Thumbnails are loaded
lazily: only cards near the visible area are rendered, and cards far off-screen release their memory.
"""
import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from . import imaging, theme
from .theme import px
from .widgets import register_wheel

MIN_CARD_RATIO = 0.6   # tallest "wide" card: panoramas get letterboxed instead of becoming slivers
MAX_CARD_RATIO = 1.7   # tallest "portrait" card: very tall photos are letterboxed too
FALLBACK_RATIO = 0.75  # used when a photo cannot be measured (missing file)


class Card:
    """Layout and loading state of one photo on the wall."""
    __slots__ = ("index", "x", "y", "w", "h", "state", "photo", "items")

    def __init__(self, index, x, y, w, h):
        self.index, self.x, self.y, self.w, self.h = index, x, y, w, h
        self.state = "idle"   # idle -> loading -> ready (or missing)
        self.photo = None
        self.items = []       # canvas item ids belonging to this card


class MasonryGrid(tk.Frame):
    def __init__(self, parent, thumbs, on_open):
        super().__init__(parent, bg=theme.BG)
        self.thumbs, self.on_open = thumbs, on_open
        self.images, self.cards = [], []
        self._generation = 0
        self._layout_width = 0
        self._resize_job = None
        self._visible_job = None
        self._hover_index = None
        self.canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0, bd=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", style="Spectra.Vertical.TScrollbar", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._on_yscroll, yscrollincrement=px(40))
        self.bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", lambda e: self._set_hover(None))
        self.canvas.bind("<Button-1>", self._on_click)
        register_wheel(self, lambda units: self.canvas.yview_scroll(units, "units"))

    # --- public ------------------------------------------------------------------------------
    def set_images(self, images, reset_scroll=True):
        """Show these Image objects (in this order)."""
        self.images = list(images)
        self._relayout(reset_scroll)

    # --- layout ------------------------------------------------------------------------------
    def _on_configure(self, event):
        if event.width != self._layout_width:
            if self._resize_job:
                self.after_cancel(self._resize_job)
            self._resize_job = self.after(120, lambda: self._relayout(reset_scroll=False))
        else:
            self._schedule_visible_update()

    def _relayout(self, reset_scroll):
        self._resize_job = None
        width = self.canvas.winfo_width()
        if width <= 1:
            return  # not on screen yet; the first <Configure> will call this again
        self._layout_width = width
        previous_position = 0.0 if reset_scroll else self.canvas.yview()[0]
        self._generation += 1
        self._hover_index = None
        self.canvas.delete("all")
        pad, gap, min_column = px(28), px(18), px(250)
        columns = max(1, (width - 2 * pad + gap) // (min_column + gap))
        column_width = (width - 2 * pad - gap * (columns - 1)) // columns
        column_bottoms = [px(6)] * columns
        self.cards = []
        for index, image in enumerate(self.images):
            ratio = imaging.ratio_for(image) or FALLBACK_RATIO
            height = max(int(column_width * min(max(ratio, MIN_CARD_RATIO), MAX_CARD_RATIO)), px(120))
            column = column_bottoms.index(min(column_bottoms))
            card = Card(index, pad + column * (column_width + gap), column_bottoms[column], column_width, height)
            column_bottoms[column] += height + gap
            self.cards.append(card)
            self._draw_placeholder(card)
        total_height = max(column_bottoms) + pad
        self.canvas.configure(scrollregion=(0, 0, width, total_height))
        self.canvas.yview_moveto(previous_position)
        self._schedule_visible_update()

    def _draw_placeholder(self, card):
        card.items = [self._rounded_rect(card.x, card.y, card.x + card.w, card.y + card.h, px(14),
                                         fill=theme.ORBIT_SLATE, tags=("card", "card_%d" % card.index))]

    def _rounded_rect(self, x1, y1, x2, y2, r, **options):
        points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
                  x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.canvas.create_polygon(points, smooth=True, outline="", **options)

    # --- lazy loading ------------------------------------------------------------------------
    def _on_yscroll(self, first, last):
        self.bar.set(first, last)
        self._schedule_visible_update()

    def _schedule_visible_update(self):
        if self._visible_job is None:
            self._visible_job = self.after_idle(self._update_visible)

    def _update_visible(self):
        self._visible_job = None
        viewport = self.canvas.winfo_height()
        top = self.canvas.canvasy(0)
        bottom = top + viewport
        for card in self.cards:
            near = card.y < bottom + viewport and card.y + card.h > top - viewport
            if near and card.state == "idle":
                self._request(card)
            elif card.state in ("ready", "missing") and (card.y + card.h < top - 3 * viewport or card.y > bottom + 3 * viewport):
                self._unload(card)

    def _request(self, card):
        card.state = "loading"
        generation = self._generation
        path = self.images[card.index].Img_Path
        size, radius = (card.w, card.h), px(14)

        def work():
            if generation != self._generation:
                return None  # the layout changed while this was queued
            return self.thumbs.render_card(path, size, radius)

        def done(result):
            if generation == self._generation and card.state == "loading":
                self._show_card(card, result)

        self.thumbs.submit(work, done)

    def _show_card(self, card, result):
        self.canvas.delete(*card.items)
        tags = ("card", "card_%d" % card.index)
        if result is None:
            pil_card, readable = None, False
        else:
            pil_card, readable = result
        if pil_card is not None:
            card.photo = ImageTk.PhotoImage(pil_card)
            card.items = [self.canvas.create_image(card.x, card.y, anchor="nw", image=card.photo, tags=tags)]
        else:
            self._draw_placeholder(card)
        if not readable:
            self._draw_missing_text(card, tags)
        card.state = "ready" if readable else "missing"

    def _draw_missing_text(self, card, tags):
        image = self.images[card.index]
        middle_x, middle_y = card.x + card.w // 2, card.y + card.h // 2
        card.items += [
            self.canvas.create_text(middle_x, middle_y - px(18), text="✦", fill=theme.ANCIENT_BRONZE,
                                    font=theme.font(26), tags=tags),
            self.canvas.create_text(middle_x, middle_y + px(14), text="Photo not found", fill=theme.MOON_DUST,
                                    font=theme.font(14, "bold"), tags=tags),
            self.canvas.create_text(middle_x, middle_y + px(36), text=self._ellipsize(image.Img_Name, theme.font(12),
                                                                                    card.w - px(32)),
                                    fill=theme.COSMIC_ASH, font=theme.font(12), tags=tags)]

    def _unload(self, card):
        self.canvas.delete(*card.items)
        card.photo = None
        card.state = "idle"
        self._draw_placeholder(card)

    # --- hover and click ---------------------------------------------------------------------
    def _card_at_pointer(self):
        items = self.canvas.find_withtag("current")
        if items:
            for tag in self.canvas.gettags(items[0]):
                if tag.startswith("card_"):
                    return int(tag[5:])
        return None

    def _on_motion(self, event):
        index = self._card_at_pointer()
        if index != self._hover_index:
            self._set_hover(index)

    def _set_hover(self, index):
        self.canvas.delete("hover")
        self._hover_index = index
        if index is None or index >= len(self.cards) or self.cards[index].state != "ready":
            self.canvas.configure(cursor="hand2" if index is not None else "")
            return
        card, image = self.cards[index], self.images[index]
        self.canvas.configure(cursor="hand2")
        tags = ("hover", "card_%d" % index)
        self._hover_photo = imaging.hover_overlay_photo(card.w, card.h, px(14))
        self.canvas.create_image(card.x, card.y, anchor="nw", image=self._hover_photo, tags=tags)
        text_x, text_width = card.x + px(16), card.w - px(32)
        baseline = card.y + card.h - px(14)
        if image.Tags:
            shown = " · ".join(image.Tags[:3]) + ("  +%d" % (len(image.Tags) - 3) if len(image.Tags) > 3 else "")
            self.canvas.create_text(text_x, baseline, anchor="sw", text=self._ellipsize(shown, theme.font(12), text_width),
                                    fill=theme.CHAMPAGNE_GOLD, font=theme.font(12), tags=tags)
            baseline -= px(22)
        self.canvas.create_text(text_x, baseline, anchor="sw",
                                text=self._ellipsize(image.Img_Name, theme.font(14, "bold"), text_width),
                                fill=theme.MOON_DUST, font=theme.font(14, "bold"), tags=tags)

    def _on_click(self, event):
        index = self._card_at_pointer()
        if index is not None and index < len(self.images):
            self.on_open(self.images[index])

    @staticmethod
    def _ellipsize(text, font, max_width):
        if font.measure(text) <= max_width:
            return text
        while text and font.measure(text + "…") > max_width:
            text = text[:-1]
        return text + "…"

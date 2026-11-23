"""Full-size photo viewer with previous/next, tag editing and remove-from-gallery."""
import tkinter as tk

from PIL import ImageOps, ImageTk

from Images import Image  # only for Image.DEFAULT_TAGS (suggested tags)

from . import dialogs, imaging, theme
from .theme import px
from .widgets import ChipFlow, PillEntry, SpectraButton, TagChip

PANEL_WIDTH = 340


class ImageViewer(tk.Frame):
    """An overlay that covers the gallery view. Left/Right keys browse, Esc closes."""

    def __init__(self, parent, gallery, tag_manager, thumbs, images, index, on_changed, on_close):
        super().__init__(parent, bg=theme.BG, takefocus=1)
        self.gallery, self.tag_manager, self.thumbs = gallery, tag_manager, thumbs
        self.images, self.index = list(images), index
        self.on_changed, self.on_close = on_changed, on_close
        self._pil = None            # the large version of the current photo
        self._photo = None          # what Tk is currently displaying
        self._load_token = 0        # lets us ignore results for a photo we already left
        self._redraw_job = None
        self._hint_job = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_stage()
        self._build_panel()
        for key, action in (("<Left>", lambda e: self.step(-1)), ("<Right>", lambda e: self.step(1)),
                            ("<Escape>", lambda e: self.close())):
            self.bind(key, action)
        self.show_current()
        self.focus_set()

    # --- building ----------------------------------------------------------------------------
    def _build_stage(self):
        self.stage = tk.Canvas(self, bg=theme.BG, highlightthickness=0, bd=0)
        self.stage.grid(row=0, column=0, sticky="nsew")
        self.stage.bind("<Configure>", self._on_stage_resize)
        self.back_button = SpectraButton(self.stage, "←  Back to gallery", self.close, style="ghost", width=170,
                                         height=38, font_size=13, bg=theme.BG)
        self.stage.create_window(px(22), px(20), anchor="nw", window=self.back_button)
        self.counter = self.stage.create_text(0, px(39), fill=theme.COSMIC_ASH, font=theme.font(13), text="")
        self._nav = {}
        size = px(50)
        for side, glyph in (("prev", "‹"), ("next", "›")):
            normal = imaging.shape_photo(size, size, size // 2, fill=theme.hex_to_rgb(theme.VOID_NAVY) + (190,),
                                         outline=theme.HAIRLINE, outline_width=max(1, px(1)))
            hover = imaging.shape_photo(size, size, size // 2, fill=theme.hex_to_rgb(theme.VOID_NAVY) + (225,),
                                        outline=theme.CHAMPAGNE_GOLD, outline_width=max(2, px(2)))
            tag = "nav_" + side
            background = self.stage.create_image(0, 0, image=normal, tags=(tag,))
            label = self.stage.create_text(0, 0, text=glyph, fill=theme.CHAMPAGNE_GOLD, font=theme.font(32, "bold"),
                                           tags=(tag,))
            self._nav[side] = (background, label, normal, hover)
            self.stage.tag_bind(tag, "<Enter>", lambda e, s=side: self._nav_hover(s, True))
            self.stage.tag_bind(tag, "<Leave>", lambda e, s=side: self._nav_hover(s, False))
            self.stage.tag_bind(tag, "<Button-1>", lambda e, d=-1 if side == "prev" else 1: self.step(d))

    def _build_panel(self):
        tk.Frame(self, bg=theme.HAIRLINE, width=1).grid(row=0, column=1, sticky="ns")
        panel = tk.Frame(self, bg=theme.DEEP_COSMOS, width=px(PANEL_WIDTH))
        panel.grid(row=0, column=2, sticky="ns")
        panel.grid_propagate(False)
        panel.pack_propagate(False)
        inner_width = px(PANEL_WIDTH) - px(56)
        body = tk.Frame(panel, bg=theme.DEEP_COSMOS)
        body.pack(fill="both", expand=True, padx=px(28), pady=px(28))
        self.name_label = tk.Label(body, bg=theme.DEEP_COSMOS, fg=theme.MOON_DUST, font=theme.font(22, display=True),
                                   anchor="w", justify="left", wraplength=inner_width)
        self.name_label.pack(fill="x")
        self.meta_label = tk.Label(body, bg=theme.DEEP_COSMOS, fg=theme.CHAMPAGNE_GOLD, font=theme.font(12, "bold"),
                                   anchor="w", justify="left", wraplength=inner_width)
        self.meta_label.pack(fill="x", pady=(px(6), 0))
        self.path_label = tk.Label(body, bg=theme.DEEP_COSMOS, fg=theme.COSMIC_ASH, font=theme.font(11), anchor="w",
                                   justify="left", wraplength=inner_width - px(10))
        self.path_label.pack(fill="x", pady=(px(6), px(18)))
        tk.Frame(body, bg=theme.HAIRLINE, height=1).pack(fill="x")
        self._caption(body, "TAGS").pack(fill="x", pady=(px(18), px(10)))
        self.tag_flow = ChipFlow(body, theme.DEEP_COSMOS)
        self.tag_flow.pack(fill="x")
        self.no_tags_label = tk.Label(body, text="No tags yet. Add the first one below.", bg=theme.DEEP_COSMOS,
                                      fg=theme.COSMIC_ASH, font=theme.font(12), anchor="w")
        self.tag_entry = PillEntry(body, placeholder="Add a tag and press Enter", width=PANEL_WIDTH - 56, height=40,
                                   bg=theme.DEEP_COSMOS, on_submit=self._submit_tag, show_clear=False)
        self.tag_entry.pack(anchor="w", pady=(px(16), 0))
        self.tag_entry.entry.bind("<Escape>", lambda e: self.focus_set())
        self.hint_label = tk.Label(body, text="", bg=theme.DEEP_COSMOS, fg=theme.NEBULA_VIOLET, font=theme.font(12),
                                   anchor="w")
        self.hint_label.pack(fill="x", pady=(px(6), 0))
        self.suggestions_caption = self._caption(body, "SUGGESTIONS")
        self.suggestion_flow = ChipFlow(body, theme.DEEP_COSMOS)
        bottom = tk.Frame(body, bg=theme.DEEP_COSMOS)
        bottom.pack(side="bottom", fill="x")
        tk.Label(bottom, text="Removing a photo only takes it out of this gallery. The file stays on your computer.",
                 bg=theme.DEEP_COSMOS, fg=theme.COSMIC_ASH, font=theme.font(11), anchor="w", justify="left",
                 wraplength=inner_width).pack(fill="x", pady=(0, px(10)))
        self.remove_button = SpectraButton(bottom, "Remove from gallery", self.remove_current, style="secondary",
                                           width=PANEL_WIDTH - 56, height=42, font_size=13, bg=theme.DEEP_COSMOS)
        self.remove_button.pack(anchor="w")

    @staticmethod
    def _caption(parent, text):
        return tk.Label(parent, text=text, bg=theme.DEEP_COSMOS, fg=theme.COSMIC_ASH, font=theme.font(11, "bold"),
                        anchor="w")

    # --- showing a photo ---------------------------------------------------------------------
    @property
    def current(self):
        return self.images[self.index]

    def show_current(self):
        image = self.current
        self._pil = None
        self._load_token += 1
        token = self._load_token
        self._redraw_image(status="Loading…")
        self._refresh_panel()
        self._update_counter()

        def done(pil):
            if token == self._load_token and self.winfo_exists():
                self._pil = pil
                self._redraw_image(status=None if pil is not None else "missing")

        self.thumbs.submit(lambda: imaging.load_full(image.Img_Path), done)

    def step(self, direction):
        if len(self.images) > 1:
            self.index = (self.index + direction) % len(self.images)
            self.show_current()
        self.focus_set()

    def _update_counter(self):
        self.stage.itemconfigure(self.counter, text="%d  /  %d" % (self.index + 1, len(self.images)))
        state = "normal" if len(self.images) > 1 else "hidden"
        for background, label, _, _ in self._nav.values():
            self.stage.itemconfigure(background, state=state)
            self.stage.itemconfigure(label, state=state)

    def _on_stage_resize(self, event):
        width, height = event.width, event.height
        self.stage.coords(self.counter, width // 2, px(39))
        margin = px(34)
        self.stage.coords(self._nav["prev"][0], margin + px(25), height // 2)
        self.stage.coords(self._nav["prev"][1], margin + px(25), height // 2 - px(3))
        self.stage.coords(self._nav["next"][0], width - margin - px(25), height // 2)
        self.stage.coords(self._nav["next"][1], width - margin - px(25), height // 2 - px(3))
        if self._redraw_job:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(70, lambda: self._redraw_image(status=self._status_now()))

    def _status_now(self):
        if self._pil is not None:
            return None
        return "missing" if getattr(self, "_missing", False) else "Loading…"

    def _nav_hover(self, side, hovering):
        background, label, normal, hover = self._nav[side]
        self.stage.itemconfigure(background, image=hover if hovering else normal)
        self.stage.configure(cursor="hand2" if hovering else "")

    def _redraw_image(self, status):
        self._redraw_job = None
        self._missing = status == "missing"
        self.stage.delete("photo")
        width, height = self.stage.winfo_width(), self.stage.winfo_height()
        if width <= 1:
            return
        if self._pil is None:
            if status == "missing":
                lines = [("✦", theme.ANCIENT_BRONZE, 34, -50), ("This photo could not be opened", theme.MOON_DUST, 18, 0),
                         ("The file may have been moved, renamed or deleted.", theme.COSMIC_ASH, 13, 30)]
            else:
                lines = [(status or "", theme.COSMIC_ASH, 16, 0)]
            for text, color, size, offset in lines:
                self.stage.create_text(width // 2, height // 2 + px(offset), text=text, fill=color,
                                       font=theme.font(size), tags="photo")
            return
        margin_x, margin_top, margin_bottom = px(110), px(78), px(40)
        box_w, box_h = max(width - 2 * margin_x, 50), max(height - margin_top - margin_bottom, 50)
        scale = min(box_w / self._pil.width, box_h / self._pil.height, 2.0)  # never blow tiny images up more than 2x
        size = (max(1, int(self._pil.width * scale)), max(1, int(self._pil.height * scale)))
        fitted = self._pil.resize(size, imaging.RESAMPLE).convert("RGBA")
        fitted.putalpha(imaging.rounded_mask(size, px(10)))
        self._photo = ImageTk.PhotoImage(fitted)
        self.stage.create_image(width // 2, margin_top + (height - margin_top - margin_bottom) // 2,
                                image=self._photo, tags="photo")

    def _refresh_panel(self):
        image = self.current
        self.name_label.configure(text=image.Img_Name)
        size = imaging.peek_size(image.Img_Path)
        parts = [image.Img_Format.lstrip(".").upper()]
        if size:
            parts.append("%d × %d" % size)
        if image.Aspect_Ratio:
            parts.append(image.Aspect_Ratio)
        self.meta_label.configure(text="  ·  ".join(parts))
        self.path_label.configure(text=str(image.Img_Path))
        self._refresh_tags()

    def _refresh_tags(self):
        image = self.current
        self.tag_flow.clear()
        self.no_tags_label.pack_forget()
        if image.Tags:
            for tag in image.Tags:
                self.tag_flow.add(TagChip(self.tag_flow, tag, removable=True, remove_command=lambda t=tag: self.remove_tag(t)))
            self.tag_flow.finish()
        else:
            self.no_tags_label.pack(fill="x", after=self.tag_flow)
        self.suggestion_flow.clear()
        have = {t.lower() for t in image.Tags}
        seen, suggestions = set(), []
        for tag in list(Image.DEFAULT_TAGS) + self.tag_manager.Get_All_Tags(self.gallery):
            if tag.lower() not in have and tag.lower() not in seen:
                seen.add(tag.lower())
                suggestions.append(tag)
        self.suggestions_caption.pack_forget()
        self.suggestion_flow.pack_forget()
        if suggestions:
            self.suggestions_caption.pack(fill="x", pady=(px(16), px(10)))
            self.suggestion_flow.pack(fill="x")
            for tag in suggestions[:8]:
                self.suggestion_flow.add(TagChip(self.suggestion_flow, "+ " + tag, compact=True,
                                                 command=lambda t=tag: self.add_tag(t)))
            self.suggestion_flow.finish()

    # --- editing -----------------------------------------------------------------------------
    def _submit_tag(self, text):
        if text:
            if self.add_tag(text):
                self.tag_entry.clear()
        self.tag_entry.entry.focus_set()

    def add_tag(self, text):
        """Add a tag with Image.Add_Tag, then save with Gallery.Save_Gallery. Returns True on success."""
        if not self.current.Add_Tag(text):
            self._flash("That tag is empty or already on this photo.")
            return False
        self._save_and_refresh()
        return True

    def remove_tag(self, tag):
        if self.current.Remove_Tag(tag):
            self._save_and_refresh()

    def _save_and_refresh(self):
        if not self.gallery.Save_Gallery():  # the backend does not save tag edits by itself
            dialogs.show_message(self, "Couldn't save changes",
                                 "SPECTRA could not write the gallery file. Your tag change is visible now but "
                                 "may be lost when the app closes. Check that the Galleries folder is writable.",
                                 kind="error")
        self._refresh_tags()
        self.on_changed()

    def _flash(self, message):
        self.hint_label.configure(text=message)
        if self._hint_job:
            self.after_cancel(self._hint_job)
        self._hint_job = self.after(2600, lambda: self.hint_label.configure(text=""))

    def remove_current(self):
        image = self.current
        confirmed = dialogs.ask_yes_no(self, "Remove this photo?",
                                       "“%s” will be removed from this gallery. The file on your computer "
                                       "will not be deleted." % image.Img_Name, yes_text="Remove", no_text="Keep")
        if not confirmed:
            self.focus_set()
            return
        if not self.gallery.Remove_Image(image.Img_ID):
            dialogs.show_message(self, "Couldn't remove the photo",
                                 "The gallery did not accept the removal, so nothing was changed.", kind="error")
            return
        self.images.pop(self.index)
        self.on_changed()
        if not self.images:
            self.close()
            return
        self.index = min(self.index, len(self.images) - 1)
        self.show_current()
        self.focus_set()

    def close(self):
        self.on_close()
        self.destroy()

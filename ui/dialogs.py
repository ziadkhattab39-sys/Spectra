"""Themed dialogs: messages, confirmations, gallery picker and the photo import dialog."""
import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from Images import Image  # only for Image.DEFAULT_TAGS (suggested tags)

from . import theme
from .theme import px
from .widgets import ChipFlow, PillEntry, ScrollFrame, SpectraButton, TagChip


class SpectraDialog(tk.Toplevel):
    """Base class: a modal window with the SPECTRA look, centered over its parent."""
    
    def __init__(self, parent, title, width=480, scrollable=False, max_height=560):
        super().__init__(parent, bg=theme.HAIRLINE)
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda e: self.cancel())
        self.result = None
        self.buttons = {}
        self._min_width = px(width)
        self._scroll_canvas = None
        self._scroll_window = None
        self._max_height = px(max_height) if scrollable else None
        if scrollable:
            container = tk.Frame(self, bg=theme.DEEP_COSMOS)
            container.pack(fill="both", expand=True, padx=1, pady=1)
            canvas = tk.Canvas(
                container,
                bg=theme.DEEP_COSMOS,
                highlightthickness=0,
                bd=0,
                width=px(width) - px(18),
                height=px(max_height)
            )
            scrollbar = ttk.Scrollbar(
                container,
                orient="vertical",
                command=canvas.yview
            )
            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            self.body = tk.Frame(
                canvas,
                bg=theme.DEEP_COSMOS,
                padx=px(30),
                pady=px(26)
            )
            self._scroll_window = canvas.create_window(
                (0, 0),
                window=self.body,
                anchor="nw"
            )
            self._scroll_canvas = canvas
            self.body.bind("<Configure>", self._update_scroll_region)
            canvas.bind("<Configure>", self._resize_scroll_body)
        else:
            self.body = tk.Frame(
                self,
                bg=theme.DEEP_COSMOS,
                padx=px(30),
                pady=px(26)
            )
            self.body.pack(
                fill="both",
                expand=True,
                padx=1,
                pady=1
            )
    
    def _update_scroll_region(self, event=None):
        """Update the scrollable area whenever the body changes size."""
        if self._scroll_canvas:
            self._scroll_canvas.configure(
                scrollregion=self._scroll_canvas.bbox("all")
            )
    
    def _resize_scroll_body(self, event):
        """Keep the body width synchronized with the canvas."""
        self._scroll_canvas.itemconfigure(
            self._scroll_window,
            width=event.width
        )
    
    def add_button_row(self, buttons):
        """buttons: list of (key, text, style, command) shown right-aligned."""
        row = tk.Frame(self.body, bg=theme.DEEP_COSMOS)
        row.pack(fill="x", pady=(px(22), 0))
        for key, text, style, command in reversed(buttons):
            button = SpectraButton(row, text, command, style=style, width=118 if len(text) < 11 else 150, height=40,
                                   font_size=13)
            button.pack(side="right", padx=(px(10), 0))
            self.buttons[key] = button
        return row

    def show(self):
        """Center the dialog over its parent, block until it closes, return self.result."""
        self.update_idletasks()
        width = max(self._min_width, self.winfo_reqwidth())
        height = self.winfo_reqheight()
        if self._max_height is not None:
            height = min(height, self._max_height + px(2))
        parent = self.master.winfo_toplevel()
        x = parent.winfo_rootx() + max((parent.winfo_width() - width) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - height) // 3, 0)
        self.geometry("%dx%d+%d+%d" % (width, height, x, y))
        theme.dark_title_bar(self)
        self.deiconify()
        self.wait_visibility()
        try:
            self.grab_set()
        except tk.TclError:
            pass  # grab can fail on some Linux window managers; the dialog still works
        self.focus_set()
        self.wait_window(self)
        return self.result
    
    def cancel(self):
        self.result = None
        self.destroy()

class MessageDialog(SpectraDialog):
    """An information, warning or error message with an OK button (or Yes/No when asking)."""
    
    def __init__(self, parent, title, message, kind="info", ask=False, yes_text="Yes", no_text="Cancel"):
        super().__init__(parent, title, width=460)
        row = tk.Frame(self.body, bg=theme.DEEP_COSMOS)
        row.pack(fill="x")
        icon_size = px(46)
        icon = tk.Canvas(row, width=icon_size, height=icon_size, bg=theme.DEEP_COSMOS, highlightthickness=0)
        icon.pack(side="left", anchor="n", padx=(0, px(18)))
        ring_color = {"info": theme.AURORA_TEAL, "warning": theme.ANCIENT_BRONZE, "error": theme.ANCIENT_BRONZE,
                      "question": theme.NEBULA_VIOLET}.get(kind, theme.AURORA_TEAL)
        glyph = {"info": "✦", "question": "?"}.get(kind, "!")
        icon.create_oval(2, 2, icon_size - 2, icon_size - 2, outline=ring_color, width=max(2, px(2)))
        icon.create_text(icon_size // 2, icon_size // 2, text=glyph, fill=theme.SOLAR_CHAMPAGNE,
                         font=theme.font(20, "bold"))
        text_column = tk.Frame(row, bg=theme.DEEP_COSMOS)
        text_column.pack(side="left", fill="x", expand=True)
        tk.Label(text_column, text=title, bg=theme.DEEP_COSMOS, fg=theme.CHAMPAGNE_GOLD, font=theme.font(20, display=True),
                 anchor="w", justify="left", wraplength=px(340)).pack(fill="x")
        tk.Label(text_column, text=message, bg=theme.DEEP_COSMOS, fg=theme.COSMIC_ASH, font=theme.font(13), anchor="w",
                 justify="left", wraplength=px(340)).pack(fill="x", pady=(px(8), 0))
        if ask:
            self.add_button_row([("no", no_text, "secondary", self.cancel),
                                 ("yes", yes_text, "primary", self._yes)])
            self.bind("<Return>", lambda e: self._yes())
        else:
            self.add_button_row([("ok", "OK", "primary", self._yes)])
            self.bind("<Return>", lambda e: self._yes())
    
    def _yes(self):
        self.result = True
        self.destroy()


def show_message(parent, title, message, kind="info"):
    """Show a themed message and wait for OK."""
    MessageDialog(parent, title, message, kind).show()


def ask_yes_no(parent, title, message, yes_text="Yes", no_text="Cancel"):
    """Show a themed question. Returns True for the confirm button, False otherwise."""
    return bool(MessageDialog(parent, title, message, kind="question", ask=True, yes_text=yes_text,
                              no_text=no_text).show())


class GalleryPickerDialog(SpectraDialog):
    """Lets the user choose between several gallery files. result = the chosen Path, or None."""
    
    def __init__(self, parent, gallery_files):
        super().__init__(parent, "Choose a gallery", width=480)
        self.files = list(gallery_files)
        self.selected = len(self.files) - 1  # newest gallery preselected
        tk.Label(self.body, text="Choose a gallery", bg=theme.DEEP_COSMOS, fg=theme.CHAMPAGNE_GOLD,
                 font=theme.font(22, display=True), anchor="w").pack(fill="x")
        tk.Label(self.body, text="Several galleries were found. Which one would you like to open?",
                 bg=theme.DEEP_COSMOS, fg=theme.COSMIC_ASH, font=theme.font(13), anchor="w", justify="left",
                 wraplength=px(400)).pack(fill="x", pady=(px(6), px(16)))
        if len(self.files) > 5:
            scroller = ScrollFrame(self.body, theme.DEEP_COSMOS)
            scroller.configure(height=px(5 * 62))
            scroller.pack(fill="x")
            scroller.canvas.configure(height=px(5 * 62))
            container = scroller.inner
        else:
            container = tk.Frame(self.body, bg=theme.DEEP_COSMOS)
            container.pack(fill="x")
        self.rows = []
        for index, path in enumerate(self.files):
            self.rows.append(self._build_row(container, index, path))
        self._highlight()
        self.add_button_row([("cancel", "Cancel", "secondary", self.cancel), ("open", "Open", "primary", self._open)])
        self.bind("<Return>", lambda e: self._open())
    
    def _build_row(self, parent, index, path):
        row = tk.Frame(parent, bg=theme.ORBIT_SLATE, highlightthickness=1, highlightbackground=theme.HAIRLINE,
                       cursor="hand2", padx=px(16), pady=px(10))
        row.pack(fill="x", pady=(0, px(8)))
        modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%b %d, %Y  ·  %H:%M")
        name = tk.Label(row, text=path.stem.replace("_", " "), bg=theme.ORBIT_SLATE, fg=theme.MOON_DUST,
                        font=theme.font(15, "bold"), anchor="w")
        name.pack(fill="x")
        detail = tk.Label(row, text="Last changed " + modified, bg=theme.ORBIT_SLATE, fg=theme.COSMIC_ASH,
                          font=theme.font(12), anchor="w")
        detail.pack(fill="x")
        for widget in (row, name, detail):
            widget.bind("<Button-1>", lambda e, i=index: self._select(i))
            widget.bind("<Double-Button-1>", lambda e, i=index: (self._select(i), self._open()))
        return row, (name, detail)
    
    def _select(self, index):
        self.selected = index
        self._highlight()
    
    def _highlight(self):
        for index, (row, labels) in enumerate(self.rows):
            active = index == self.selected
            fill = theme.SURFACE_HOVER if active else theme.ORBIT_SLATE
            row.configure(bg=fill, highlightbackground=theme.CHAMPAGNE_GOLD if active else theme.HAIRLINE)
            for label in labels:
                label.configure(bg=fill)
    
    def _open(self):
        self.result = self.files[self.selected]
        self.destroy()


class ImportDialog(SpectraDialog):
    """Pick tags for the chosen photos, then add them to the gallery using Gallery.Add_Image.
    
    result = {"added": int, "duplicates": [names], "failed": [names]} once finished, else None.
    """
    
    def __init__(self, parent, gallery, tag_manager, paths):
        super().__init__(parent, "Import photos", width=540, scrollable=True, max_height=560)
        self.gallery = gallery
        self.paths = list(paths)
        self.selected_tags = []
        self._events = queue.Queue()
        self._running = False
        count = len(self.paths)
        tk.Label(self.body, text="Import %d photo%s" % (count, "" if count == 1 else "s"), bg=theme.DEEP_COSMOS,
                 fg=theme.CHAMPAGNE_GOLD, font=theme.font(22, display=True), anchor="w").pack(fill="x")
        names = ", ".join(os.path.basename(p) for p in self.paths[:3])
        if count > 3:
            names += " and %d more" % (count - 3)
        tk.Label(self.body, text=names, bg=theme.DEEP_COSMOS, fg=theme.COSMIC_ASH, font=theme.font(12), anchor="w",
                 justify="left", wraplength=px(470)).pack(fill="x", pady=(px(4), px(18)))
        tk.Label(self.body, text="TAGS FOR THESE PHOTOS", bg=theme.DEEP_COSMOS, fg=theme.COSMIC_ASH,
                 font=theme.font(11, "bold"), anchor="w").pack(fill="x", pady=(0, px(8)))
        self.chip_flow = ChipFlow(self.body, theme.DEEP_COSMOS)
        self.chip_flow.pack(fill="x")
        for tag in self._suggested_tags(tag_manager):
            self._add_suggestion(tag)
        self.chip_flow.finish()
        tk.Label(self.body, text="Or type your own, separated by commas", bg=theme.DEEP_COSMOS, fg=theme.COSMIC_ASH,
                 font=theme.font(12), anchor="w").pack(fill="x", pady=(px(16), px(8)))
        self.tag_entry = PillEntry(self.body, placeholder="golden hour, street, family", width=470, height=40,
                                   bg=theme.DEEP_COSMOS, on_submit=lambda text: self._start(), show_clear=False)
        self.tag_entry.pack(anchor="w")
        self.status = tk.Label(self.body, text="", bg=theme.DEEP_COSMOS, fg=theme.COSMIC_ASH, font=theme.font(12),
                               anchor="w")
        self.progress = ttk.Progressbar(self.body, style="Spectra.Horizontal.TProgressbar", mode="determinate",
                                        maximum=max(count, 1))
        self.add_button_row([("cancel", "Cancel", "secondary", self.cancel), ("import", "Import", "primary", self._start)])
        self.bind("<Return>", lambda event: self._start())
        self.bind("<KP_Enter>", lambda event: self._start())
    
    def _suggested_tags(self, tag_manager):
        """Default tags first, then tags already used in the gallery (no case-insensitive duplicates)."""
        seen, tags = set(), []
        for tag in list(Image.DEFAULT_TAGS) + tag_manager.Get_All_Tags(self.gallery):
            if tag.lower() not in seen:
                seen.add(tag.lower())
                tags.append(tag)
        return tags
    
    def _add_suggestion(self, tag):
        chip_holder = {}
    
        def toggle():
            if tag in self.selected_tags:
                self.selected_tags.remove(tag)
            else:
                self.selected_tags.append(tag)
            self._replace_chip(chip_holder, tag)
    
        chip_holder["toggle"] = toggle
        chip_holder["chip"] = TagChip(self.chip_flow, tag, selected=False, command=toggle, compact=True)
        self.chip_flow.add(chip_holder["chip"])
    
    def _replace_chip(self, holder, tag):
        """Rebuild one chip with its new selected state, keeping its position in the flow."""
        old = holder["chip"]
        index = self.chip_flow.chips.index(old)
        new = TagChip(self.chip_flow, tag, selected=tag in self.selected_tags, command=holder["toggle"], compact=True)
        self.chip_flow.chips[index] = new
        old.destroy()
        holder["chip"] = new
        self.chip_flow.reflow()
    
    def _chosen_tags(self):
        tags = list(self.selected_tags)
        typed = self.tag_entry.get()
        for piece in typed.split(","):
            piece = piece.strip()
            if piece and piece.lower() not in [t.lower() for t in tags]:
                tags.append(piece)
        return tags
    
    def _start(self):
        if self._running:
            return
        self._running = True
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # cannot close while importing
        self.bind("<Escape>", lambda e: None)
        self.buttons["import"].set_enabled(False)
        self.buttons["cancel"].set_enabled(False)
        self.status.pack(fill="x", pady=(px(16), px(6)), before=self.buttons["import"].master)
        self.progress.pack(fill="x", before=self.buttons["import"].master)
        tags = self._chosen_tags()
        threading.Thread(target=self._import_worker, args=(tags,), daemon=True).start()
        self.after(40, self._drain_events)
    
    def _import_worker(self, tags):
        """Runs on a background thread. Only Gallery.Add_Image touches the gallery here."""
        existing = {os.path.normcase(os.path.abspath(str(img.Img_Path))) for img in self.gallery.Images}
        added, duplicates, failed = 0, [], []
        for number, path in enumerate(self.paths, start=1):
            name = os.path.basename(path)
            self._events.put(("progress", number - 1, name))
            if os.path.normcase(os.path.abspath(path)) in existing:
                duplicates.append(name)
            elif self.gallery.Add_Image(path, list(tags) if tags else None):
                added += 1
                existing.add(os.path.normcase(os.path.abspath(path)))
            else:
                failed.append(name)
        self._events.put(("done", {"added": added, "duplicates": duplicates, "failed": failed}))
    
    def _drain_events(self):
        try:
            while True:
                event = self._events.get_nowait()
                if event[0] == "progress":
                    self.progress["value"] = event[1]
                    self.status.configure(text="Importing %d of %d  ·  %s" % (event[1] + 1, len(self.paths), event[2]))
                else:
                    self.result = event[1]
                    self.destroy()
                    return
        except queue.Empty:
            pass
        self.after(40, self._drain_events)
    
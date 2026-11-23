"""Reusable SPECTRA widgets: buttons, tag chips, search entry, scrolling frames.

Shapes are rendered by Pillow (see imaging.shape_photo) so corners are smooth instead of the
jagged default Tk look.
"""
import sys
import tkinter as tk
from tkinter import ttk

from . import imaging, theme
from .theme import px


# --- ttk styling (scrollbar and progress bar are the only ttk widgets used) --------------------
def apply_ttk_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    style.layout("Spectra.Vertical.TScrollbar",
                 [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
                     ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    style.configure("Spectra.Vertical.TScrollbar", troughcolor=theme.BG, background=theme.HAIRLINE,
                    bordercolor=theme.BG, lightcolor=theme.HAIRLINE, darkcolor=theme.HAIRLINE,
                    gripcount=0, width=px(10), relief="flat")
    style.map("Spectra.Vertical.TScrollbar",
              background=[("active", theme.ANCIENT_BRONZE), ("pressed", theme.CHAMPAGNE_GOLD)],
              lightcolor=[("active", theme.ANCIENT_BRONZE), ("pressed", theme.CHAMPAGNE_GOLD)],
              darkcolor=[("active", theme.ANCIENT_BRONZE), ("pressed", theme.CHAMPAGNE_GOLD)])
    style.configure("Spectra.Horizontal.TProgressbar", troughcolor=theme.ORBIT_SLATE, background=theme.CHAMPAGNE_GOLD,
                    bordercolor=theme.ORBIT_SLATE, lightcolor=theme.CHAMPAGNE_GOLD, darkcolor=theme.CHAMPAGNE_GOLD,
                    thickness=px(8))


# --- Mouse wheel routing -----------------------------------------------------------------------
# One global handler finds the scrollable area under the pointer (works the same on Windows,
# macOS and Linux, and never scrolls an area the pointer is not over).
_wheel_targets = {}


def register_wheel(widget, scroll_units):
    """Make 'widget' (and everything inside it) scroll with the mouse wheel via scroll_units(n)."""
    _wheel_targets[widget] = scroll_units
    widget.bind("<Destroy>", lambda e, w=widget: _wheel_targets.pop(w, None) if e.widget is w else None, add="+")


def install_wheel_router(root):
    root.bind_all("<MouseWheel>", _route_wheel)
    root.bind_all("<Button-4>", _route_wheel)
    root.bind_all("<Button-5>", _route_wheel)


def _route_wheel(event):
    if event.num == 4:
        units = -2
    elif event.num == 5:
        units = 2
    elif sys.platform == "darwin":
        units = -int(event.delta) or (-1 if event.delta > 0 else 1)
    else:
        units = -int(event.delta / 120) * 2 or (-2 if event.delta > 0 else 2)
    try:
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
    except (KeyError, tk.TclError):
        return
    while widget is not None:
        if widget in _wheel_targets:
            _wheel_targets[widget](units)
            return
        widget = widget.master


# --- Buttons -----------------------------------------------------------------------------------
def _button_look(style, width, height):
    """(state -> shape image, state -> text color) for a button style."""
    radius = height // 2
    void = theme.hex_to_rgb(theme.VOID_NAVY)
    if style == "primary":
        shapes = {
            "normal": dict(gradient=(theme.blend(theme.SOLAR_CHAMPAGNE, theme.CHAMPAGNE_GOLD, 0.35),
                                     theme.blend(theme.CHAMPAGNE_GOLD, theme.ANCIENT_BRONZE, 0.30))),
            "hover": dict(gradient=(theme.SOLAR_CHAMPAGNE, theme.CHAMPAGNE_GOLD)),
            "pressed": dict(gradient=(theme.CHAMPAGNE_GOLD, theme.blend(theme.CHAMPAGNE_GOLD, theme.ANCIENT_BRONZE, 0.5))),
            "disabled": dict(fill=theme.HAIRLINE),
        }
        colors = {"normal": theme.VOID_NAVY, "hover": theme.VOID_NAVY, "pressed": theme.VOID_NAVY,
                  "disabled": theme.COSMIC_ASH}
    elif style == "secondary":
        shapes = {
            "normal": dict(fill=void + (150,), outline=theme.CHAMPAGNE_GOLD, outline_width=max(1, px(1))),
            "hover": dict(fill=theme.blend(theme.VOID_NAVY, theme.CHAMPAGNE_GOLD, 0.16), outline=theme.SOLAR_CHAMPAGNE,
                          outline_width=max(1, px(1))),
            "pressed": dict(fill=theme.blend(theme.VOID_NAVY, theme.CHAMPAGNE_GOLD, 0.26), outline=theme.CHAMPAGNE_GOLD,
                            outline_width=max(1, px(1))),
            "disabled": dict(fill=None, outline=theme.HAIRLINE, outline_width=max(1, px(1))),
        }
        colors = {"normal": theme.CHAMPAGNE_GOLD, "hover": theme.SOLAR_CHAMPAGNE, "pressed": theme.CHAMPAGNE_GOLD,
                  "disabled": theme.COSMIC_ASH}
    else:  # ghost
        shapes = {
            "normal": dict(fill=void + (0,)),
            "hover": dict(fill=theme.SURFACE_HOVER),
            "pressed": dict(fill=theme.ORBIT_SLATE),
            "disabled": dict(fill=void + (0,)),
        }
        colors = {"normal": theme.COSMIC_ASH, "hover": theme.MOON_DUST, "pressed": theme.CHAMPAGNE_GOLD,
                  "disabled": theme.HAIRLINE}
    photos = {state: imaging.shape_photo(width, height, radius, **kwargs) for state, kwargs in shapes.items()}
    return photos, colors


class SpectraButton(tk.Canvas):
    """A rounded button. style: 'primary' (gold), 'secondary' (gold outline) or 'ghost' (quiet)."""

    def __init__(self, parent, text, command=None, style="primary", width=180, height=44, font_size=14, bg=None):
        self.button_width, self.button_height = px(width), px(height)
        super().__init__(parent, width=self.button_width, height=self.button_height, highlightthickness=0, bd=0,
                         bg=bg or parent.cget("bg"), cursor="hand2", takefocus=1)
        self.command = command
        self.enabled = True
        self._photos, self._colors = _button_look(style, self.button_width, self.button_height)
        self._background = self.create_image(0, 0, anchor="nw", image=self._photos["normal"])
        self._label = self.create_text(self.button_width // 2, self.button_height // 2, text=text,
                                       font=theme.font(font_size, "bold"), fill=self._colors["normal"])
        self.bind("<Enter>", lambda e: self._set_state("hover"))
        self.bind("<Leave>", lambda e: self._set_state("normal"))
        self.bind("<ButtonPress-1>", lambda e: self._set_state("pressed"))
        self.bind("<ButtonRelease-1>", self._released)
        self.bind("<FocusIn>", lambda e: self._set_state("hover"))
        self.bind("<FocusOut>", lambda e: self._set_state("normal"))
        self.bind("<Return>", lambda e: self.invoke())
        self.bind("<space>", lambda e: self.invoke())

    def _set_state(self, state):
        if not self.enabled:
            state = "disabled"
        self.itemconfigure(self._background, image=self._photos[state])
        self.itemconfigure(self._label, fill=self._colors[state])

    def _released(self, event):
        if not self.enabled:
            return
        inside = 0 <= event.x < self.button_width and 0 <= event.y < self.button_height
        self._set_state("hover" if inside else "normal")
        if inside:
            self.invoke()

    def invoke(self):
        if self.enabled and self.command:
            self.command()

    def set_text(self, text):
        self.itemconfigure(self._label, text=text)

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._set_state("normal")


class CanvasButton:
    """The same look as SpectraButton, but drawn straight onto an existing canvas.

    Used on the startup screen, where a button must sit on top of a picture (a normal widget
    would leave a solid rectangle around its rounded corners).
    """

    def __init__(self, canvas, center_x, center_y, text, command, style="primary", width=260, height=52, font_size=15):
        self.canvas, self.command = canvas, command
        w, h = px(width), px(height)
        self.photos, self.colors = _button_look(style, w, h)
        self.tag = "button_%d" % id(self)
        left, top = center_x - w // 2, center_y - h // 2
        self.background = canvas.create_image(left, top, anchor="nw", image=self.photos["normal"], tags=(self.tag,))
        self.label = canvas.create_text(center_x, center_y, text=text, font=theme.font(font_size, "bold"),
                                        fill=self.colors["normal"], tags=(self.tag,))
        canvas.tag_bind(self.tag, "<Enter>", lambda e: self._show("hover", "hand2"))
        canvas.tag_bind(self.tag, "<Leave>", lambda e: self._show("normal", ""))
        canvas.tag_bind(self.tag, "<ButtonPress-1>", lambda e: self._show("pressed"))
        canvas.tag_bind(self.tag, "<ButtonRelease-1>", self._released)

    def _show(self, state, cursor=None):
        self.canvas.itemconfigure(self.background, image=self.photos[state])
        self.canvas.itemconfigure(self.label, fill=self.colors[state])
        if cursor is not None:
            self.canvas.configure(cursor=cursor)

    def _released(self, event):
        under = self.canvas.find_withtag("current")
        inside = bool(under) and self.tag in self.canvas.gettags(under[0])
        self._show("hover" if inside else "normal")
        if inside:
            self.command()


# --- Tag chips ---------------------------------------------------------------------------------
class TagChip(tk.Canvas):
    """A pill showing a tag. Gold when selected; an optional count and an optional x to remove."""

    def __init__(self, parent, text, count=None, selected=False, removable=False, command=None,
                 remove_command=None, bg=None, compact=False):
        label_font = theme.font(11 if compact else 12, "bold" if selected else "normal")
        count_font = theme.font(10 if compact else 11)
        pad = px(12 if compact else 14)
        gap = px(8)
        self.chip_height = px(26 if compact else 30)
        label_width = label_font.measure(text)
        count_width = count_font.measure(str(count)) + gap if count is not None else 0
        cross_width = px(20) if removable else 0
        self.chip_width = pad * 2 + label_width + count_width + cross_width
        super().__init__(parent, width=self.chip_width, height=self.chip_height, highlightthickness=0, bd=0,
                         bg=bg or parent.cget("bg"), cursor="hand2")
        self.command, self.remove_command = command, remove_command
        self.removable = removable
        radius = self.chip_height // 2
        line = max(1, px(1))
        if selected:
            self._photos = {"normal": imaging.shape_photo(self.chip_width, self.chip_height, radius,
                                                          fill=theme.CHAMPAGNE_GOLD),
                            "hover": imaging.shape_photo(self.chip_width, self.chip_height, radius,
                                                         fill=theme.SOLAR_CHAMPAGNE)}
            text_color, count_color = theme.VOID_NAVY, theme.blend(theme.VOID_NAVY, theme.ANCIENT_BRONZE, 0.35)
        else:
            self._photos = {"normal": imaging.shape_photo(self.chip_width, self.chip_height, radius,
                                                          fill=theme.ORBIT_SLATE, outline=theme.HAIRLINE,
                                                          outline_width=line),
                            "hover": imaging.shape_photo(self.chip_width, self.chip_height, radius,
                                                         fill=theme.SURFACE_HOVER, outline=theme.NEBULA_VIOLET,
                                                         outline_width=line)}
            text_color, count_color = theme.MOON_DUST, theme.COSMIC_ASH
        self._background = self.create_image(0, 0, anchor="nw", image=self._photos["normal"])
        middle = self.chip_height // 2
        self.create_text(pad, middle, text=text, anchor="w", font=label_font, fill=text_color)
        if count is not None:
            self.create_text(pad + label_width + gap, middle, text=str(count), anchor="w", font=count_font,
                             fill=count_color)
        if removable:
            self.create_text(self.chip_width - pad - px(4), middle, text="×", anchor="e",
                             font=theme.font(15, "bold"), fill=text_color if selected else theme.COSMIC_ASH)
        self.bind("<Enter>", lambda e: self.itemconfigure(self._background, image=self._photos["hover"]))
        self.bind("<Leave>", lambda e: self.itemconfigure(self._background, image=self._photos["normal"]))
        self.bind("<ButtonRelease-1>", self._clicked)

    def _clicked(self, event):
        if not (0 <= event.x < self.chip_width and 0 <= event.y < self.chip_height):
            return
        if self.removable and event.x > self.chip_width - px(30):
            if self.remove_command:
                self.remove_command()
        elif self.command:
            self.command()


class ChipFlow(tk.Frame):
    """Lays out chips left to right and wraps to a new row when the width runs out."""

    def __init__(self, parent, bg, gap=8):
        super().__init__(parent, bg=bg, height=1)
        self.chips = []
        self.gap = px(gap)
        self._laid_out_width = -1
        self.bind("<Configure>", self._on_configure)

    def clear(self):
        for chip in self.chips:
            chip.destroy()
        self.chips = []
        self.configure(height=1)

    def add(self, chip):
        self.chips.append(chip)
        self._laid_out_width = -1  # force a re-layout

    def finish(self):
        """Call after adding a batch of chips."""
        self.reflow()

    def _on_configure(self, event):
        if event.width != self._laid_out_width:
            self.reflow()

    def reflow(self):
        width = self.winfo_width()
        if width <= 1 or not self.chips:
            return
        self._laid_out_width = width
        x = y = row_height = 0
        for chip in self.chips:
            chip_width, chip_height = chip.winfo_reqwidth(), chip.winfo_reqheight()
            if x > 0 and x + chip_width > width:
                x, y, row_height = 0, y + row_height + self.gap, 0
            chip.place(x=x, y=y)
            x += chip_width + self.gap
            row_height = max(row_height, chip_height)
        self.configure(height=max(y + row_height, 1))


# --- Entry -------------------------------------------------------------------------------------
class PillEntry(tk.Canvas):
    """A rounded text field with placeholder text, a teal focus ring and an optional clear button."""

    def __init__(self, parent, placeholder="", width=280, height=40, bg=None, on_change=None, on_submit=None,
                 show_clear=True):
        self.field_width, self.field_height = px(width), px(height)
        super().__init__(parent, width=self.field_width, height=self.field_height, highlightthickness=0, bd=0,
                         bg=bg or parent.cget("bg"))
        radius = self.field_height // 2
        self._shape_normal = imaging.shape_photo(self.field_width, self.field_height, radius, fill=theme.ORBIT_SLATE,
                                                 outline=theme.HAIRLINE, outline_width=max(1, px(1)))
        self._shape_focus = imaging.shape_photo(self.field_width, self.field_height, radius, fill=theme.ORBIT_SLATE,
                                                outline=theme.FOCUS, outline_width=max(2, px(2)))
        self._background = self.create_image(0, 0, anchor="nw", image=self._shape_normal)
        self.placeholder, self.on_change, self.on_submit = placeholder, on_change, on_submit
        self._placeholder_visible = False
        self.entry = tk.Entry(self, bd=0, highlightthickness=0, relief="flat", bg=theme.ORBIT_SLATE,
                              fg=theme.MOON_DUST, insertbackground=theme.CHAMPAGNE_GOLD,
                              selectbackground=theme.ANCIENT_BRONZE, selectforeground=theme.MOON_DUST,
                              font=theme.font(13))
        entry_left = radius // 2 + px(10)
        reserved_right = px(34) if show_clear else px(14)
        self.create_window(entry_left, self.field_height // 2, anchor="w", window=self.entry,
                           width=self.field_width - entry_left - reserved_right)
        self._clear_button = None
        if show_clear:
            self._clear_button = self.create_text(self.field_width - px(20), self.field_height // 2, text="✕",
                                                  font=theme.font(12, "bold"), fill=theme.COSMIC_ASH, state="hidden",
                                                  tags=("clear",))
            self.tag_bind("clear", "<Button-1>", lambda e: self.clear(notify=True))
            self.tag_bind("clear", "<Enter>", lambda e: (self.itemconfigure("clear", fill=theme.CHAMPAGNE_GOLD),
                                                         self.configure(cursor="hand2")))
            self.tag_bind("clear", "<Leave>", lambda e: (self.itemconfigure("clear", fill=theme.COSMIC_ASH),
                                                         self.configure(cursor="")))
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<KeyRelease>", self._key_released)
        self.entry.bind("<Return>", self._submitted)
        self._show_placeholder()

    def _show_placeholder(self):
        self.entry.delete(0, "end")
        self.entry.insert(0, self.placeholder)
        self.entry.configure(fg=theme.COSMIC_ASH)
        self._placeholder_visible = True

    def _focus_in(self, event):
        self.itemconfigure(self._background, image=self._shape_focus)
        if self._placeholder_visible:
            self.entry.delete(0, "end")
            self.entry.configure(fg=theme.MOON_DUST)
            self._placeholder_visible = False

    def _focus_out(self, event):
        self.itemconfigure(self._background, image=self._shape_normal)
        if not self.entry.get():
            self._show_placeholder()

    def _key_released(self, event):
        self._update_clear_button()
        if self.on_change and event.keysym != "Return":
            self.on_change(self.get())

    def _submitted(self, event):
        if self.on_submit:
            self.on_submit(self.get())

    def _update_clear_button(self):
        if self._clear_button is not None:
            self.itemconfigure(self._clear_button, state="normal" if self.get() else "hidden")

    def get(self):
        return "" if self._placeholder_visible else self.entry.get().strip()

    def clear(self, notify=False):
        self.entry.delete(0, "end")
        if self.focus_get() is not self.entry:
            self._show_placeholder()
        self._update_clear_button()
        if notify and self.on_change:
            self.on_change("")

    def focus_entry(self):
        self.entry.focus_set()


# --- Scrolling frame ---------------------------------------------------------------------------
class ScrollFrame(tk.Frame):
    """A vertically scrolling container. Put your widgets inside .inner."""

    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", style="Spectra.Vertical.TScrollbar",
                                 command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window(0, 0, anchor="nw", window=self.inner)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._window, width=e.width))
        self.canvas.pack(side="left", fill="both", expand=True)
        self._bar_visible = False
        register_wheel(self, lambda units: self.canvas.yview_scroll(units, "units")
                       if self._bar_visible else None)

    def _on_scroll(self, first, last):
        needs_bar = not (float(first) <= 0.0 and float(last) >= 0.999)
        if needs_bar != self._bar_visible:
            self._bar_visible = needs_bar
            if needs_bar:
                self.bar.pack(side="right", fill="y", before=self.canvas)
            else:
                self.bar.pack_forget()
        self.bar.set(first, last)

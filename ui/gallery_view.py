"""The main SPECTRA screen: sidebar with tags, header with search and import, and the photo wall.

All data comes from the existing core classes:
  Gallery      -> Get_All_Images, Remove_Image (in the viewer), Save_Gallery, Add_Image (via the import dialog)
  Tag_Manager  -> Get_All_Tags, Get_Tag_Count, Get_Popular_Tags, Search_By_Single_Tag, Advanced_Search_By_Tags
"""
import tkinter as tk
from tkinter import filedialog

from Images import Image  # only for Image.SUPPORTED_FORMATS (the file picker's filter)

from . import dialogs, imaging, theme
from .image_viewer import ImageViewer
from .masonry_grid import MasonryGrid
from .theme import px
from .widgets import ChipFlow, PillEntry, ScrollFrame, SpectraButton, TagChip

SIDEBAR_WIDTH = 270
POPULAR_TAG_COUNT = 8


class EmptyState(tk.Frame):
    """Friendly message shown when there is nothing to display."""

    def __init__(self, parent):
        super().__init__(parent, bg=theme.BG)
        self.center = tk.Frame(self, bg=theme.BG)
        self.center.place(relx=0.5, rely=0.46, anchor="center")
        self.logo = tk.Label(self.center, image=imaging.load_logo(px(110)), bg=theme.BG)
        self.logo.pack()
        self.title = tk.Label(self.center, bg=theme.BG, fg=theme.MOON_DUST, font=theme.font(30, display=True))
        self.title.pack(pady=(px(18), px(6)))
        self.subtitle = tk.Label(self.center, bg=theme.BG, fg=theme.COSMIC_ASH, font=theme.font(14),
                                 wraplength=px(440), justify="center")
        self.subtitle.pack()
        self.button_holder = tk.Frame(self.center, bg=theme.BG)
        self.button_holder.pack(pady=(px(24), 0))
        self.button = None

    def configure_state(self, title, subtitle, button_text, button_command, style="primary"):
        self.title.configure(text=title)
        self.subtitle.configure(text=subtitle)
        if self.button is not None:
            self.button.destroy()
        self.button = SpectraButton(self.button_holder, button_text, button_command, style=style, width=200,
                                    height=46, font_size=14, bg=theme.BG)
        self.button.pack()


class GalleryView(tk.Frame):
    def __init__(self, parent, gallery, tag_manager, thumbs, on_switch_gallery):
        super().__init__(parent, bg=theme.BG)
        self.gallery, self.tag_manager, self.thumbs = gallery, tag_manager, thumbs
        self.on_switch_gallery = on_switch_gallery
        self.active_tags = []        # tags currently used as filters (exact strings from Get_All_Tags)
        self.match_mode = "AND"      # how several selected tags combine: "AND" or "OR"
        self.show_all_tags = False   # sidebar shows only the popular tags until this is switched on
        self.tag_text_filter = ""    # what the user typed into the search box
        self.current_images = []
        self.viewer = None
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_sidebar()
        tk.Frame(self, bg=theme.HAIRLINE, width=1).grid(row=0, column=1, sticky="ns")
        self._build_main()
        self.apply_filters()

    # --- building ----------------------------------------------------------------------------
    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=theme.SIDEBAR, width=px(SIDEBAR_WIDTH))
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.pack_propagate(False)
        pad = px(24)
        brand = tk.Frame(sidebar, bg=theme.SIDEBAR)
        brand.pack(fill="x", padx=pad, pady=(px(28), px(26)))
        tk.Label(brand, image=imaging.load_logo(px(52)), bg=theme.SIDEBAR).pack(side="left")
        wordmark = tk.Frame(brand, bg=theme.SIDEBAR)
        wordmark.pack(side="left", padx=(px(12), 0))
        tk.Label(wordmark, text=" ".join("SPECTRA"), bg=theme.SIDEBAR, fg=theme.MOON_DUST,
                 font=theme.font(22, display=True)).pack(anchor="w")
        tk.Label(wordmark, text="DISCOVER THE UNSEEN", bg=theme.SIDEBAR, fg=theme.ANCIENT_BRONZE,
                 font=theme.font(9, "bold")).pack(anchor="w")
        self.all_photos_button = SpectraButton(sidebar, "✦   All Photos", self.clear_filters, style="primary",
                                               width=SIDEBAR_WIDTH - 48, height=42, font_size=14, bg=theme.SIDEBAR)
        self.all_photos_button.pack(padx=pad)
        header = tk.Frame(sidebar, bg=theme.SIDEBAR)
        header.pack(fill="x", padx=pad, pady=(px(28), px(10)))
        tk.Label(header, text="TAGS", bg=theme.SIDEBAR, fg=theme.COSMIC_ASH, font=theme.font(11, "bold")).pack(side="left")
        self.tag_toggle = tk.Label(header, bg=theme.SIDEBAR, fg=theme.CHAMPAGNE_GOLD, font=theme.font(12), cursor="hand2")
        self.tag_toggle.pack(side="right")
        self.tag_toggle.bind("<Button-1>", lambda e: self._toggle_tag_list())
        footer = tk.Frame(sidebar, bg=theme.SIDEBAR)
        footer.pack(side="bottom", fill="x", padx=pad, pady=(px(10), px(24)))
        tk.Frame(footer, bg=theme.HAIRLINE, height=1).pack(fill="x", pady=(0, px(16)))
        self.gallery_name_label = tk.Label(footer, bg=theme.SIDEBAR, fg=theme.MOON_DUST, font=theme.font(14, "bold"),
                                           anchor="w")
        self.gallery_name_label.pack(fill="x")
        self.gallery_stats_label = tk.Label(footer, bg=theme.SIDEBAR, fg=theme.COSMIC_ASH, font=theme.font(12), anchor="w")
        self.gallery_stats_label.pack(fill="x", pady=(px(2), px(12)))
        SpectraButton(footer, "Switch gallery", self.on_switch_gallery, style="secondary", width=SIDEBAR_WIDTH - 48,
                      height=38, font_size=13, bg=theme.SIDEBAR).pack()
        self.tag_scroller = ScrollFrame(sidebar, theme.SIDEBAR)
        self.tag_scroller.pack(fill="both", expand=True, padx=(pad, px(10)))
        self.tag_flow = ChipFlow(self.tag_scroller.inner, theme.SIDEBAR)
        self.tag_flow.pack(fill="x")
        self.tags_message = tk.Label(self.tag_scroller.inner, bg=theme.SIDEBAR, fg=theme.COSMIC_ASH, font=theme.font(12),
                                     justify="left", anchor="w", wraplength=px(SIDEBAR_WIDTH - 70))

    def _build_main(self):
        main = tk.Frame(self, bg=theme.BG)
        main.grid(row=0, column=2, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)
        header = tk.Frame(main, bg=theme.BG)
        header.grid(row=0, column=0, sticky="ew", padx=px(28), pady=(px(26), px(14)))
        titles = tk.Frame(header, bg=theme.BG)
        titles.pack(side="left")
        tk.Label(titles, text="Your Collection", bg=theme.BG, fg=theme.MOON_DUST, font=theme.font(34, display=True)).pack(anchor="w")
        self.count_label = tk.Label(titles, bg=theme.BG, fg=theme.COSMIC_ASH, font=theme.font(14), anchor="w")
        self.count_label.pack(anchor="w", pady=(px(2), 0))
        SpectraButton(header, "+  Import Images", self.import_images, style="primary", width=170, height=42,
                      font_size=14, bg=theme.BG).pack(side="right", anchor="s")
        self.search_entry = PillEntry(header, placeholder="Search your tags…", width=290, height=42, bg=theme.BG,
                                      on_change=self._search_changed, on_submit=self._search_submitted)
        self.search_entry.pack(side="right", anchor="s", padx=(0, px(14)))
        self.filter_bar = tk.Frame(main, bg=theme.BG)  # shown only while tags are selected
        self.filter_bar.columnconfigure(0, weight=1)
        self.filter_flow = ChipFlow(self.filter_bar, theme.BG)
        self.filter_flow.grid(row=0, column=0, sticky="ew")
        self.filter_controls = tk.Frame(self.filter_bar, bg=theme.BG)
        self.filter_controls.grid(row=0, column=1, sticky="ne", padx=(px(12), 0))
        content = tk.Frame(main, bg=theme.BG)
        content.grid(row=2, column=0, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        self.grid_view = MasonryGrid(content, self.thumbs, self.open_viewer)
        self.empty_state = EmptyState(content)
        self.grid_view.grid(row=0, column=0, sticky="nsew")
        self.empty_state.grid(row=0, column=0, sticky="nsew")
        self.filter_bar_holder = main

    # --- filtering (uses Tag_Manager) --------------------------------------------------------
    def apply_filters(self, reset_scroll=True):
        """Work out which photos to show using Gallery / Tag_Manager, then refresh the screen."""
        all_images = self.gallery.Get_All_Images()
        existing_tags = self.tag_manager.Get_All_Tags(self.gallery)
        self.active_tags = [tag for tag in self.active_tags if tag in existing_tags]  # drop tags that vanished
        if not self.active_tags:
            matches = all_images
        elif len(self.active_tags) == 1:
            matches = self.tag_manager.Search_By_Single_Tag(self.gallery, self.active_tags[0])
        else:
            matches = self.tag_manager.Advanced_Search_By_Tags(self.gallery, list(self.active_tags), self.match_mode)
        self.current_images = list(reversed(matches))  # newest first
        total, shown = len(all_images), len(matches)
        noun = "photo" if total == 1 else "photos"
        self.count_label.configure(text="%d %s" % (total, noun) if shown == total and not self.active_tags
                                   else "%d of %d %s" % (shown, total, noun))
        self._refresh_filter_bar()
        self._refresh_sidebar()
        if total == 0:
            self.empty_state.configure_state(
                "Your universe is waiting",
                "Import your first photographs to begin your collection. Every frame tells a story.",
                "+  Import Images", self.import_images)
            self.empty_state.tkraise()
        elif shown == 0:
            self.empty_state.configure_state(
                "Nothing matches those tags",
                "No photo has all of the selected tags. Try removing a filter or matching any of them.",
                "Clear filters", self.clear_filters, style="secondary")
            self.empty_state.tkraise()
        else:
            self.grid_view.tkraise()
            self.grid_view.set_images(self.current_images, reset_scroll=reset_scroll)

    def toggle_tag(self, tag):
        if tag in self.active_tags:
            self.active_tags.remove(tag)
        else:
            self.active_tags.append(tag)
        self.apply_filters()

    def clear_filters(self):
        self.active_tags = []
        self.search_entry.clear()
        self.tag_text_filter = ""
        self.apply_filters()

    def set_match_mode(self, mode):
        self.match_mode = mode
        self.apply_filters()

    def _search_changed(self, text):
        self.tag_text_filter = text.lower()
        self._refresh_sidebar()

    def _search_submitted(self, text):
        """Enter in the search box selects the best matching tag."""
        wanted = text.strip().lower()
        if not wanted:
            return
        tags = self.tag_manager.Get_All_Tags(self.gallery)
        exact = [t for t in tags if t.lower() == wanted]
        partial = [t for t in tags if wanted in t.lower()]
        match = (exact or partial or [None])[0]
        if match is None:
            self.count_label.configure(text='No tag matches “%s”' % text.strip())
            return
        if match not in self.active_tags:
            self.active_tags.append(match)
        self.search_entry.clear()
        self.tag_text_filter = ""
        self.apply_filters()

    def _toggle_tag_list(self):
        self.show_all_tags = not self.show_all_tags
        self._refresh_sidebar()

    # --- sidebar and filter bar --------------------------------------------------------------
    def _refresh_sidebar(self):
        counts = self.tag_manager.Get_Tag_Count(self.gallery)
        popular = self.tag_manager.Get_Popular_Tags(self.gallery, Top=len(counts) if self.show_all_tags else POPULAR_TAG_COUNT)
        if self.tag_text_filter:  # while searching, look through every tag
            popular = [(tag, count) for tag, count in self.tag_manager.Get_Popular_Tags(self.gallery, Top=max(len(counts), 1))
                       if self.tag_text_filter in tag.lower()]
        self.tag_toggle.configure(text="" if self.tag_text_filter or len(counts) <= POPULAR_TAG_COUNT
                                  else ("Show popular" if self.show_all_tags else "Show all (%d)" % len(counts)))
        self.tag_flow.clear()
        self.tags_message.pack_forget()
        for tag, count in popular:
            self.tag_flow.add(TagChip(self.tag_flow, tag, count=count, selected=tag in self.active_tags,
                                      command=lambda t=tag: self.toggle_tag(t), bg=theme.SIDEBAR))
        self.tag_flow.finish()
        if not popular:
            self.tags_message.configure(text="No tags match your search." if self.tag_text_filter
                                        else "No tags yet. Add some while importing, or open a photo to tag it.")
            self.tags_message.pack(fill="x", pady=(px(4), 0))
        images = self.gallery.Get_All_Images()
        self.gallery_name_label.configure(text=self.gallery.Gallery_File.stem.replace("_", " "))
        self.gallery_stats_label.configure(text="%d %s  ·  %d tags" % (len(images), "photo" if len(images) == 1 else "photos", len(counts)))

    def _refresh_filter_bar(self):
        self.filter_flow.clear()
        for child in self.filter_controls.winfo_children():
            child.destroy()
        if not self.active_tags:
            self.filter_bar.grid_remove()
            return
        self.filter_bar.grid(row=1, column=0, sticky="ew", padx=px(28), pady=(0, px(12)))
        for tag in self.active_tags:
            self.filter_flow.add(TagChip(self.filter_flow, tag, selected=True, removable=True,
                                         command=lambda t=tag: self.toggle_tag(t), remove_command=lambda t=tag: self.toggle_tag(t)))
        self.filter_flow.finish()
        if len(self.active_tags) > 1:
            for mode, text in (("AND", "Match all"), ("OR", "Match any")):
                TagChip(self.filter_controls, text, selected=self.match_mode == mode, compact=True,
                        command=lambda m=mode: self.set_match_mode(m)).pack(side="left", padx=(0, px(6)))
        SpectraButton(self.filter_controls, "Clear", self.clear_filters, style="ghost", width=64, height=26,
                      font_size=12, bg=theme.BG).pack(side="left")

    # --- importing ---------------------------------------------------------------------------
    def import_images(self):
        patterns = " ".join("*" + ext for ext in sorted(Image.SUPPORTED_FORMATS))
        paths = filedialog.askopenfilenames(parent=self.winfo_toplevel(), title="Import photos into SPECTRA",
                                            filetypes=[("Photos", patterns), ("All files", "*.*")])
        if not paths:
            return
        result = dialogs.ImportDialog(self, self.gallery, self.tag_manager, paths).show()
        if result is None:
            return
        self.apply_filters()
        problems = []
        if result["failed"]:
            problems.append("Could not be added (not a valid image, unsupported type, or the file extension "
                            "does not match its content):\n" + "\n".join("• " + n for n in result["failed"][:8])
                            + ("\n• and %d more" % (len(result["failed"]) - 8) if len(result["failed"]) > 8 else ""))
        if result["duplicates"]:
            problems.append("%d already in this gallery and skipped." % len(result["duplicates"]))
        if problems:
            summary = "Added %d photo%s.\n\n" % (result["added"], "" if result["added"] == 1 else "s")
            dialogs.show_message(self, "Import finished", summary + "\n\n".join(problems),
                                 kind="warning" if result["failed"] else "info")

    # --- viewer ------------------------------------------------------------------------------
    def open_viewer(self, image):
        if self.viewer is not None:
            return
        index = self.current_images.index(image)
        self.viewer = ImageViewer(self, self.gallery, self.tag_manager, self.thumbs, self.current_images, index,
                                  on_changed=self._refresh_sidebar, on_close=self._viewer_closed)
        self.viewer.place(x=0, y=0, relwidth=1, relheight=1)

    def _viewer_closed(self):
        self.viewer = None
        self.apply_filters(reset_scroll=False)

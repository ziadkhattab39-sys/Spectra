"""SPECTRA launcher. Run this file to start the app:  python spectra_app.py

It creates the existing core objects (Gallery, Tag_Manager) and hands them to the Tkinter UI.
No core file is imported in a modified way: Gallery, Image and Tag_Manager are used as they are.
"""
import re
import sys
import tkinter as tk
import traceback

from Gallery import Gallery
from Tag_Manager import Tag_Manager

from ui import dialogs, imaging, theme, widgets
from ui.gallery_view import GalleryView
from ui.startup_screen import StartupScreen


class SpectraApp:
    def __init__(self):
        theme.enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.withdraw()
        theme.init(self.root)
        widgets.apply_ttk_styles(self.root)
        widgets.install_wheel_router(self.root)
        self.root.title("SPECTRA")
        self.root.configure(bg=theme.BG)
        self.root.report_callback_exception = self._report_exception
        self.icon = imaging.window_icon()
        self.root.iconphoto(True, self.icon)
        self._size_and_center_window()
        theme.dark_title_bar(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.tag_manager = Tag_Manager()
        self.thumbs = imaging.ThumbnailService(self.root)
        self.screen = None
        self.show_startup()
        self.root.deiconify()

    def _size_and_center_window(self):
        screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        width = min(theme.px(1280), screen_w - 60)
        height = min(theme.px(820), screen_h - 100)
        self.root.minsize(min(theme.px(1000), width), min(theme.px(680), height))
        self.root.geometry("%dx%d+%d+%d" % (width, height, (screen_w - width) // 2, max((screen_h - height) // 2 - 20, 0)))

    def _report_exception(self, exc_type, exc_value, exc_traceback):
        """Programming errors are printed in full and shown to the user, never silently swallowed."""
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
        try:
            dialogs.show_message(self.root, "Something went wrong",
                                 "SPECTRA hit an unexpected error:\n%s: %s\n\nThe details were printed to the "
                                 "console." % (exc_type.__name__, exc_value), kind="error")
        except tk.TclError:
            pass

    # --- screens -----------------------------------------------------------------------------
    def _swap_screen(self, new_screen):
        if self.screen is not None:
            self.screen.destroy()
        self.screen = new_screen
        self.screen.pack(fill="both", expand=True)

    def show_startup(self):
        self._swap_screen(StartupScreen(self.root, self.view_existing_gallery, self.create_new_gallery))

    def show_gallery(self, gallery):
        self._swap_screen(GalleryView(self.root, gallery, self.tag_manager, self.thumbs, self.show_startup))

    # --- startup choices ---------------------------------------------------------------------
    @staticmethod
    def find_gallery_files():
        """Gallery_<number>.json files inside the Galleries folder, oldest first. Empty if there are none."""
        folder = Gallery.Galleries_Folder
        if not folder.is_dir():
            return []
        files = [f for f in folder.iterdir() if f.is_file() and re.fullmatch(r"Gallery_\d+\.json", f.name)]
        return sorted(files, key=lambda f: int(f.stem.split("_")[1]))

    def view_existing_gallery(self):
        """Option A: load a gallery that already exists. Never creates anything."""
        files = self.find_gallery_files()
        if not files:
            dialogs.show_message(self.root, "No gallery found",
                                 "There is no existing gallery to open yet. Choose “Create New Gallery” "
                                 "to start your first one.", kind="error")
            return  # stay on the startup screen
        chosen = files[0] if len(files) == 1 else dialogs.GalleryPickerDialog(self.root, files).show()
        if chosen is None:
            return
        gallery = Gallery()
        gallery.Gallery_File = chosen  # the existing Load_Gallery reads whatever file this points to
        try:
            loaded = gallery.Load_Gallery()
            problem = "The file could not be read as a SPECTRA gallery (it may be damaged or empty)."
        except Exception as error:  # Load_Gallery only catches some errors, e.g. a missing key is not one of them
            loaded = False
            problem = "The file has an unexpected structure (%s: %s)." % (type(error).__name__, error)
        if not loaded:
            dialogs.show_message(self.root, "Couldn't open the gallery", "%s\n\nFile: %s" % (problem, chosen.name),
                                 kind="error")
            return
        self.show_gallery(gallery)

    def create_new_gallery(self):
        """Option B: create a brand-new gallery file with the existing Gallery.Create_Gallery."""
        try:
            Gallery.Galleries_Folder.mkdir(parents=True, exist_ok=True)  # Create_Gallery needs the folder to exist
            gallery = Gallery()
            created = gallery.Create_Gallery()
            problem = "SPECTRA could not create the gallery file. Check that the Galleries folder is writable."
        except OSError as error:
            created = False
            problem = "SPECTRA could not create the gallery file (%s)." % error
        if not created:
            dialogs.show_message(self.root, "Couldn't create a gallery", problem, kind="error")
            return
        self.show_gallery(gallery)

    # --- lifecycle ---------------------------------------------------------------------------
    def quit(self):
        self.thumbs.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    SpectraApp().run()

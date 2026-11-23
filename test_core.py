"""
SPECTRA - Core classes smoke test

Place this file in the same folder as:
    Gallery.py
    Images.py

Then run:
    python test_core.py

The test creates a temporary PNG, creates a temporary Gallery JSON file
inside the project's Galleries folder, tests the main methods, and removes
the temporary files afterward.
"""

import json
import traceback
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image as PILImage

from Images import Image
from Gallery import Gallery


def check(condition, message):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {message}")
    return bool(condition)


def main():
    passed = 0
    failed = 0

    def test(condition, message):
        nonlocal passed, failed
        if check(condition, message):
            passed += 1
        else:
            failed += 1

    print("=" * 58)
    print(" SPECTRA | CORE CLASSES TEST")
    print("=" * 58)

    with TemporaryDirectory(prefix="spectra_test_") as temp_dir:
        temp_path = Path(temp_dir)
        sample_image = temp_path / "test_image.png"

        # Create a real image for Image.Validate_Image().
        PILImage.new("RGB", (320, 200), (120, 160, 200)).save(sample_image)

        print("\n[1] IMAGE CLASS")
        image = Image(str(sample_image), 777, ["Test", "Nature"], "16:10")

        test(image.Img_ID == 777, "Image ID is assigned")
        test(image.Img_Path == sample_image, "Image path is stored as Path")
        test(image.Img_Name == "test_image.png", "Image name is extracted")
        test(image.Img_Format == ".png", "Image extension is extracted")
        test(image.Tags == ["Test", "Nature"], "Tags are initialized")
        test(image.Aspect_Ratio == "16:10", "Aspect ratio is initialized")

        try:
            valid = image.Validate_Image()
            test(valid is True, "Validate_Image accepts a valid PNG")
        except Exception:
            test(False, "Validate_Image raised an exception")
            traceback.print_exc()

        try:
            image.Add_Tag("Landscape")
            test("Landscape" in image.Tags, "Add_Tag adds a tag")
        except Exception:
            test(False, "Add_Tag raised an exception")
            traceback.print_exc()

        try:
            info = image.Get_Image_Info()
            required_keys = {
                "image_id",
                "image_name",
                "image_path",
                "image_format",
                "image_aspect_ratio",
                "image_tags",
            }
            test(isinstance(info, dict), "Get_Image_Info returns a dictionary")
            test(required_keys.issubset(info.keys()), "Image info contains expected keys")
        except Exception:
            test(False, "Get_Image_Info raised an exception")
            traceback.print_exc()

        print("\n[2] GALLERY CLASS - BASIC METHODS")
        gallery = Gallery()

        test(gallery.Images == [], "Gallery starts with an empty image list")
        test(gallery.Next_ID == 1000, "Gallery starts with Next_ID = 1000")
        test(gallery.Gallery_File is None, "Gallery starts without a file path")

        try:
            added = gallery.Add_Image(str(sample_image), ["Test", "Nature"])
            test(added is True, "Add_Image adds a valid image")
            test(len(gallery.Images) == 1, "Images list contains the added image")
            test(gallery.Images[0].Img_ID == 1000, "First added image gets ID 1000")
            test(gallery.Next_ID == 1001, "Next_ID increments after adding")
        except Exception:
            test(False, "Add_Image raised an exception")
            traceback.print_exc()

        try:
            found = gallery.Get_Image(1000)
            test(found is not None and found.Img_ID == 1000, "Get_Image finds an existing image")
            test(gallery.Get_Image(-999) is None, "Get_Image returns None for a missing ID")

            all_images = gallery.Get_All_Images()
            test(all_images == gallery.Images, "Get_All_Images returns the current images")
            test(all_images is not gallery.Images, "Get_All_Images returns a separate list")
        except Exception:
            test(False, "Get_Image or Get_All_Images raised an exception")
            traceback.print_exc()

        print("\n[3] GALLERY FILE - CREATE / SAVE / LOAD")
        gallery_folder = Gallery.Galleries_Folder
        gallery_folder.mkdir(parents=True, exist_ok=True)

        created_file = None
        try:
            created = gallery.Create_Gallery()
            test(created is True, "Create_Gallery creates a JSON file")
            created_file = gallery.Gallery_File

            test(created_file is not None and created_file.exists(),
                 "Gallery_File points to an existing file")

            saved = gallery.Save_Gallery()
            test(saved is True, "Save_Gallery saves the current gallery")

            if created_file and created_file.exists():
                with open(created_file, "r", encoding="utf-8") as file:
                    saved_data = json.load(file)

                test("images" in saved_data, "Saved JSON contains images")
                test("next_image_id" in saved_data, "Saved JSON contains next_image_id")
                test(len(saved_data["images"]) == len(gallery.Images),
                     "Saved JSON image count matches Gallery")

            loaded_gallery = Gallery()
            loaded_gallery.Gallery_File = created_file
            loaded = loaded_gallery.Load_Gallery()
            test(loaded is True, "Load_Gallery loads the saved JSON")
            test(len(loaded_gallery.Images) == len(gallery.Images),
                 "Loaded Gallery has the same number of images")

            if loaded and loaded_gallery.Images:
                restored = loaded_gallery.Images[0]
                original = gallery.Images[0]
                test(restored.Img_ID == original.Img_ID, "Loaded image ID matches")
                test(restored.Tags == original.Tags, "Loaded image tags match")
                test(restored.Aspect_Ratio == original.Aspect_Ratio,
                     "Loaded image aspect ratio matches")
                test(loaded_gallery.Next_ID == gallery.Next_ID,
                     "Loaded Next_ID matches saved Next_ID")

        except Exception:
            test(False, "Create / Save / Load sequence raised an exception")
            traceback.print_exc()
        finally:
            # Remove only the file created by this test.
            if created_file is not None:
                try:
                    created_file.unlink(missing_ok=True)
                    print("\n[CLEANUP] Temporary Gallery JSON removed.")
                except OSError:
                    print("\n[WARNING] Could not remove the temporary Gallery JSON.")

        print("\n[4] REMOVE IMAGE")
        try:
            remove_gallery = Gallery()
            remove_gallery.Images = [Image(str(sample_image), 1234, [], "")]
            removed = remove_gallery.Remove_Image(1234)
            test(removed is True, "Remove_Image removes an existing image")
            test(len(remove_gallery.Images) == 0, "Image list is empty after removal")
            test(remove_gallery.Remove_Image(1234) is False,
                 "Remove_Image returns False for a missing ID")
        except Exception:
            test(False, "Remove_Image raised an exception")
            traceback.print_exc()

    print("\n" + "=" * 58)
    print(f"RESULT: {passed} passed | {failed} failed")
    print("=" * 58)

    if failed:
        print("Some tests failed. Check the FAIL lines and traceback above.")
    else:
        print("All tested operations passed.")


if __name__ == "__main__":
    main()

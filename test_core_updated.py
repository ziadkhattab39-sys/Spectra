"""
SPECTRA - Core classes and integration test

Place this file in the same folder as:
    Images.py
    Gallery.py
    Tag_Manager.py

Run:
    python test_core.py

The script creates temporary PNG files, tests Image and Gallery,
tests Gallery JSON save/load, and tests Tag_Manager both with the
original Gallery and with a Gallery restored from JSON.

Only the JSON file created by this test is removed afterward.
"""

import json
import traceback
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image as PILImage

from Images import Image
from Gallery import Gallery
from Tag_Manager import Tag_Manager


def main():
    passed = 0
    failed = 0

    def test(condition, message):
        nonlocal passed, failed
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] {message}")
        if condition:
            passed += 1
        else:
            failed += 1
        return bool(condition)

    def run_test_group(group_name, function):
        print(f"\n{group_name}")
        try:
            function()
        except Exception:
            test(False, f"{group_name} raised an unexpected exception")
            traceback.print_exc()

    print("=" * 64)
    print(" SPECTRA | CORE CLASSES + INTEGRATION TEST")
    print("=" * 64)

    with TemporaryDirectory(prefix="spectra_test_") as temp_dir:
        temp_path = Path(temp_dir)

        # Create real image files for Image.Validate_Image() and Gallery.Add_Image().
        image_paths = []
        for index in range(1, 6):
            path = temp_path / f"test_image_{index}.png"
            PILImage.new(
                "RGB",
                (320, 200),
                (100 + index * 10, 140 + index * 5, 180)
            ).save(path)
            image_paths.append(path)

        # ---------------------------------------------------------
        # 1. IMAGE CLASS
        # ---------------------------------------------------------
        image = None

        def test_image_class():
            nonlocal image
            image = Image(
                str(image_paths[0]),
                777,
                ["Test", "Nature"],
                "16:10"
            )

            test(image.Img_ID == 777, "Image ID is assigned")
            test(image.Img_Path == image_paths[0], "Image path is stored as Path")
            test(image.Img_Name == "test_image_1.png", "Image name is extracted")
            test(image.Img_Format == ".png", "Image extension is extracted")
            test(image.Tags == ["Test", "Nature"], "Tags are initialized")
            test(image.Aspect_Ratio == "16:10", "Aspect ratio is initialized")

            valid = image.Validate_Image()
            test(valid is True, "Validate_Image accepts a valid PNG")

            image.Add_Tag("Landscape")
            test("Landscape" in image.Tags, "Add_Tag adds a tag")

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
            test(
                required_keys.issubset(info.keys()),
                "Image info contains expected keys"
            )

        run_test_group("[1] IMAGE CLASS", test_image_class)

        # ---------------------------------------------------------
        # 2. GALLERY CLASS
        # ---------------------------------------------------------
        gallery = Gallery()

        def test_gallery_class():
            test(gallery.Images == [], "Gallery starts with an empty image list")
            test(gallery.Next_ID == 1000, "Gallery starts with Next_ID = 1000")
            test(gallery.Gallery_File is None, "Gallery starts without a file path")

            added = gallery.Add_Image(str(image_paths[0]), ["Test", "Nature"])
            test(added is True, "Add_Image adds a valid image")
            test(len(gallery.Images) == 1, "Images list contains the added image")
            test(gallery.Images[0].Img_ID == 1000, "First added image gets ID 1000")
            test(gallery.Next_ID == 1001, "Next_ID increments after adding")

            found = gallery.Get_Image(1000)
            test(
                found is not None and found.Img_ID == 1000,
                "Get_Image finds an existing image"
            )
            test(
                gallery.Get_Image(-999) is None,
                "Get_Image returns None for a missing ID"
            )

            all_images = gallery.Get_All_Images()
            test(
                all_images == gallery.Images,
                "Get_All_Images returns the current images"
            )
            test(
                all_images is not gallery.Images,
                "Get_All_Images returns a separate list"
            )

        run_test_group("[2] GALLERY CLASS - BASIC METHODS", test_gallery_class)

        # ---------------------------------------------------------
        # 3. ADD A TEST DATASET FOR TAG MANAGER INTEGRATION
        # ---------------------------------------------------------
        def add_tag_test_dataset():
            # The first image is already in the Gallery from the Gallery tests.
            # Add four more images with deliberately overlapping tags.
            dataset = [
                (image_paths[1], ["Nature", "Flowers"]),
                (image_paths[2], ["Sunset", "Sky"]),
                (image_paths[3], ["Architecture", "Buildings"]),
                (image_paths[4], ["Nature", "Sunset"]),
            ]

            for path, tags in dataset:
                added = gallery.Add_Image(str(path), tags)
                test(added is True, f"Gallery.Add_Image adds {path.name}")

            test(len(gallery.Images) == 5, "Gallery contains all 5 test images")

        run_test_group("[3] GALLERY + IMAGE INTEGRATION DATASET", add_tag_test_dataset)

        # ---------------------------------------------------------
        # 4. GALLERY FILE - CREATE / SAVE / LOAD
        # ---------------------------------------------------------
        created_file = None
        loaded_gallery = None

        def test_gallery_file():
            nonlocal created_file, loaded_gallery

            gallery_folder = Gallery.Galleries_Folder
            gallery_folder.mkdir(parents=True, exist_ok=True)

            created = gallery.Create_Gallery()
            test(created is True, "Create_Gallery creates a JSON file")

            created_file = gallery.Gallery_File
            test(
                created_file is not None and created_file.exists(),
                "Gallery_File points to an existing file"
            )

            saved = gallery.Save_Gallery()
            test(saved is True, "Save_Gallery saves the current gallery")

            if created_file and created_file.exists():
                with open(created_file, "r", encoding="utf-8") as file:
                    saved_data = json.load(file)

                test("images" in saved_data, "Saved JSON contains images")
                test(
                    "next_image_id" in saved_data,
                    "Saved JSON contains next_image_id"
                )
                test(
                    len(saved_data["images"]) == len(gallery.Images),
                    "Saved JSON image count matches Gallery"
                )

            loaded_gallery = Gallery()
            loaded_gallery.Gallery_File = created_file
            loaded = loaded_gallery.Load_Gallery()

            test(loaded is True, "Load_Gallery loads the saved JSON")
            test(
                len(loaded_gallery.Images) == len(gallery.Images),
                "Loaded Gallery has the same number of images"
            )

            if loaded and loaded_gallery.Images:
                restored = loaded_gallery.Images[0]
                original = gallery.Images[0]

                test(restored.Img_ID == original.Img_ID, "Loaded image ID matches")
                test(restored.Tags == original.Tags, "Loaded image tags match")
                test(
                    restored.Aspect_Ratio == original.Aspect_Ratio,
                    "Loaded image aspect ratio matches"
                )
                test(
                    loaded_gallery.Next_ID == gallery.Next_ID,
                    "Loaded Next_ID matches saved Next_ID"
                )

        try:
            run_test_group("[4] GALLERY FILE - CREATE / SAVE / LOAD", test_gallery_file)
        finally:
            if created_file is not None:
                try:
                    created_file.unlink(missing_ok=True)
                    print("\n[CLEANUP] Temporary Gallery JSON removed.")
                except OSError:
                    print("\n[WARNING] Could not remove the temporary Gallery JSON.")

        # ---------------------------------------------------------
        # 5. TAG MANAGER - CORE FUNCTIONS
        # ---------------------------------------------------------
        tag_manager = Tag_Manager()

        def test_tag_manager_core():
            all_tags = tag_manager.Get_All_Tags(gallery)
            expected_tags = {
                "Test",
                "Nature",
                "Flowers",
                "Sunset",
                "Sky",
                "Architecture",
                "Buildings",
            }

            test(isinstance(all_tags, list), "Get_All_Tags returns a list")
            test(set(all_tags) == expected_tags, "Get_All_Tags returns all unique tags")

            single_results = tag_manager.Search_By_Single_Tag(gallery, "Nature")
            test(
                len(single_results) == 3,
                "Search_By_Single_Tag finds all images with Nature"
            )
            test(
                all("Nature" in img.Tags for img in single_results),
                "Single-tag search results all contain the requested tag"
            )

            and_results = tag_manager.Advanced_Search_By_Tags(
                gallery,
                ["Nature", "Sunset"],
                "AND"
            )
            test(
                len(and_results) == 0,
                "Advanced search AND returns no images when no image has both tags"
            )

            or_results = tag_manager.Advanced_Search_By_Tags(
                gallery,
                ["Nature", "Sunset"],
                "OR"
            )
            test(
                len(or_results) == 4,
                "Advanced search OR returns images containing either tag"
            )
            test(
                all(
                    ("Nature" in img.Tags) or ("Sunset" in img.Tags)
                    for img in or_results
                ),
                "Advanced search OR results match at least one requested tag"
            )

            # Verify AND against the test image that contains both tags.
            and_results = tag_manager.Advanced_Search_By_Tags(
                gallery,
                ["Nature", "Sunset"],
                "AND"
            )
            test(
                len(and_results) == 1,
                "Advanced search AND finds the image containing both tags"
            )
            test(
                all(
                    all(tag in img.Tags for tag in ["Nature", "Sunset"])
                    for img in and_results
                ),
                "Advanced search AND results contain every requested tag"
            )

        run_test_group("[5] TAG MANAGER - CORE FUNCTIONS", test_tag_manager_core)

        # ---------------------------------------------------------
        # 6. TAG MANAGER - ADDITIONAL FUNCTIONS
        # ---------------------------------------------------------
        def test_tag_manager_additional():
            tag_counts = tag_manager.Get_Tag_Count(gallery)

            test(isinstance(tag_counts, dict), "Get_Tag_Count returns a dictionary")
            test(
                tag_counts.get("Nature") == 3,
                "Get_Tag_Count returns the correct Nature count"
            )
            test(
                tag_counts.get("Sunset") == 2,
                "Get_Tag_Count returns the correct Sunset count"
            )
            test(
                tag_counts.get("Sky") == 1,
                "Get_Tag_Count returns the correct Sky count"
            )

            popular_tags = tag_manager.Get_Popular_Tags(gallery, Top=3)

            test(
                isinstance(popular_tags, list),
                "Get_Popular_Tags returns a list"
            )
            test(
                len(popular_tags) == 3,
                "Get_Popular_Tags returns the requested number of entries"
            )
            test(
                popular_tags[0] == ("Nature", 3),
                "Get_Popular_Tags places the most frequent tag first"
            )
            test(
                all(
                    popular_tags[index][1] >= popular_tags[index + 1][1]
                    for index in range(len(popular_tags) - 1)
                ),
                "Popular tags are sorted by count in descending order"
            )

        run_test_group("[6] TAG MANAGER - ADDITIONAL FUNCTIONS", test_tag_manager_additional)

        # ---------------------------------------------------------
        # 7. TAG MANAGER + LOADED GALLERY INTEGRATION
        # ---------------------------------------------------------
        def test_loaded_gallery_integration():
            if loaded_gallery is None:
                test(False, "Loaded Gallery is available for Tag_Manager integration")
                return

            loaded_tags = tag_manager.Get_All_Tags(loaded_gallery)
            original_tags = tag_manager.Get_All_Tags(gallery)

            test(
                set(loaded_tags) == set(original_tags),
                "Tag_Manager reads the same tags from the JSON-restored Gallery"
            )

            loaded_nature_results = tag_manager.Search_By_Single_Tag(
                loaded_gallery,
                "Nature"
            )
            original_nature_results = tag_manager.Search_By_Single_Tag(
                gallery,
                "Nature"
            )

            test(
                len(loaded_nature_results) == len(original_nature_results),
                "Tag_Manager search results match after Gallery save/load"
            )

            loaded_counts = tag_manager.Get_Tag_Count(loaded_gallery)
            original_counts = tag_manager.Get_Tag_Count(gallery)

            test(
                loaded_counts == original_counts,
                "Tag counts match between original and loaded Gallery"
            )

        run_test_group(
            "[7] TAG MANAGER + LOADED GALLERY INTEGRATION",
            test_loaded_gallery_integration
        )

        # ---------------------------------------------------------
        # 8. REMOVE IMAGE
        # ---------------------------------------------------------
        def test_remove_image():
            remove_gallery = Gallery()
            remove_gallery.Images = [
                Image(str(image_paths[0]), 1234, [], "")
            ]

            removed = remove_gallery.Remove_Image(1234)
            test(removed is True, "Remove_Image removes an existing image")
            test(
                len(remove_gallery.Images) == 0,
                "Image list is empty after removal"
            )
            test(
                remove_gallery.Remove_Image(1234) is False,
                "Remove_Image returns False for a missing ID"
            )

        run_test_group("[8] REMOVE IMAGE", test_remove_image)

    print("\n" + "=" * 64)
    print(f"FINAL RESULT: {passed} passed | {failed} failed")
    print("=" * 64)

    if failed:
        print("Some tests failed. Check the FAIL lines and traceback above.")
    else:
        print("ALL TESTS PASSED. Core classes and integration are working.")


if __name__ == "__main__":
    main()

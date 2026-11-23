"""
SPECTRA | TAG MANAGER - INDEPENDENT TEST
----------------------------------------
This script tests Tag_Manager with a fresh, isolated dataset.
It does not use image files or modify the Gallery JSON file.
"""

from types import SimpleNamespace
from Tag_Manager import Tag_Manager


# ------------------------------------------------------------
# TEST DATASET
# ------------------------------------------------------------

Gallery = SimpleNamespace(
    Images=[
        SimpleNamespace(Image_ID=1000, Tags=["Nature", "Trees"]),
        SimpleNamespace(Image_ID=1001, Tags=["Flowers", "Spring"]),
        SimpleNamespace(Image_ID=1002, Tags=["Sunset", "Sky"]),
        SimpleNamespace(Image_ID=1003, Tags=["Nature", "Sunset"]),
    ]
)

Manager = Tag_Manager()

Passed = 0
Failed = 0


def Check(Test_Name, Condition):
    global Passed, Failed

    if Condition:
        Passed += 1
        print(f"[PASS] {Test_Name}")
    else:
        Failed += 1
        print(f"[FAIL] {Test_Name}")


print("=" * 64)
print(" SPECTRA | TAG MANAGER - INDEPENDENT TEST")
print("=" * 64)

print("\n[1] DATASET CHECK")
Check("Dataset contains exactly 4 images", len(Gallery.Images) == 4)
Check(
    "No image contains both Flowers and Sky",
    not any(
        all(tag in img.Tags for tag in ["Flowers", "Sky"])
        for img in Gallery.Images
    ),
)
Check(
    "One image contains both Nature and Sunset",
    sum(
        all(tag in img.Tags for tag in ["Nature", "Sunset"])
        for img in Gallery.Images
    ) == 1,
)

print("\n[2] GET ALL TAGS")
All_Tags = Manager.Get_All_Tags(Gallery)
Expected_Tags = {
    "Nature", "Trees", "Flowers", "Spring",
    "Sunset", "Sky"
}
Check("Get_All_Tags returns a list", isinstance(All_Tags, list))
Check("Get_All_Tags returns all unique tags", set(All_Tags) == Expected_Tags)
Check("Get_All_Tags contains no duplicates", len(All_Tags) == len(set(All_Tags)))

print("\n[3] SINGLE-TAG SEARCH")
Nature_Results = Manager.Search_By_Single_Tag(Gallery, "Nature")
Check("Nature search returns 2 images", len(Nature_Results) == 2)
Check(
    "Every Nature result actually has the Nature tag",
    all("Nature" in img.Tags for img in Nature_Results),
)

print("\n[4] ADVANCED SEARCH - AND")
# Critical case: no image has BOTH requested tags.
AND_No_Match = Manager.Advanced_Search_By_Tags(
    Gallery, ["Flowers", "Sky"], "AND"
)
Check(
    "AND returns an empty list when no image has both tags",
    AND_No_Match == [],
)

# Positive case: exactly one image has both requested tags.
AND_One_Match = Manager.Advanced_Search_By_Tags(
    Gallery, ["Nature", "Sunset"], "AND"
)
Check("AND finds the one image containing both tags", len(AND_One_Match) == 1)
Check(
    "Every AND result contains all requested tags",
    all(
        all(tag in img.Tags for tag in ["Nature", "Sunset"])
        for img in AND_One_Match
    ),
)

print("\n[5] ADVANCED SEARCH - OR")
OR_Results = Manager.Advanced_Search_By_Tags(
    Gallery, ["Flowers", "Sky"], "OR"
)
Check("OR returns 2 images", len(OR_Results) == 2)
Check(
    "Every OR result contains at least one requested tag",
    all(
        any(tag in img.Tags for tag in ["Flowers", "Sky"])
        for img in OR_Results
    ),
)

print("\n[6] TAG COUNTS")
Tag_Count = Manager.Get_Tag_Count(Gallery)
Check("Get_Tag_Count returns a dictionary", isinstance(Tag_Count, dict))
Check("Nature count is 2", Tag_Count.get("Nature") == 2)
Check("Sunset count is 2", Tag_Count.get("Sunset") == 2)
Check("Flowers count is 1", Tag_Count.get("Flowers") == 1)
Check("Sky count is 1", Tag_Count.get("Sky") == 1)

print("\n[7] POPULAR TAGS")
Popular_Tags = Manager.Get_Popular_Tags(Gallery, Top=3)
Check("Get_Popular_Tags returns a list", isinstance(Popular_Tags, list))
Check("Popular tags returns 3 entries", len(Popular_Tags) == 3)
Check(
    "Popular tags are sorted by descending count",
    all(
        Popular_Tags[i][1] >= Popular_Tags[i + 1][1]
        for i in range(len(Popular_Tags) - 1)
    ),
)
Check(
    "The most popular tags have count 2",
    Popular_Tags[0][1] == 2 and Popular_Tags[1][1] == 2,
)

print("\n" + "=" * 64)
print(f"FINAL RESULT: {Passed} passed | {Failed} failed")
print("=" * 64)

if Failed == 0:
    print("All Tag_Manager tests passed.")
else:
    print("Some tests failed. Review the FAIL lines above.")

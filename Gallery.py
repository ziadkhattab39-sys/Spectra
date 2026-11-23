from Images import Image
from pathlib import Path
from PIL import Image as PILImage, ImageOps
import json 

class Gallery:
    Project_Path = Path(__file__).parent
    Galleries_Folder = Project_Path / "Galleries"
    def __init__ (self):
        self.Images = []
        self.Next_ID = 1000
        self.Gallery_File = None

    def Add_Image (self, image_path, Tag_List = None):
        if Tag_List is not None and not isinstance(Tag_List, list):
            return False
        img = Image(image_path, self.Next_ID)
        if img.Validate_Image():
            if Tag_List is not None:
                for Tag in Tag_List:
                    img.Add_Tag(Tag)
            try:
                with PILImage.open(image_path) as Raw_Image:
                    Width, Height = ImageOps.exif_transpose(Raw_Image).size
                img.Set_Aspect_Ratio(Width, Height)
            except (OSError, ValueError):
                pass
            self.Images.append(img)
            self.Next_ID += 1
            self.Save_Gallery()
            return True
        else:
            return False

    def Remove_Image (self, image_id):
        Image_Exists = False
        Image_Index = 0
        for i in range(len(self.Images)):
            if self.Images[i].Img_ID == image_id:
                Image_Exists = True
                Image_Index = i
                break
        if Image_Exists:
            self.Images.pop(Image_Index)
            self.Save_Gallery()
            return True
        else:
            return False 

    def Get_Image (self, image_id):
        for img in self.Images:
            if img.Img_ID == image_id:
                return img
        return None

    def Get_All_Images (self):
        return self.Images.copy()

    def Create_Gallery(self):
        Next_Num = self.Get_Next_Gallery_Num()
        self.Gallery_File = Gallery.Galleries_Folder / f"Gallery_{Next_Num}.json"
        try:
            with open(self.Gallery_File, "x") as File:
                json.dump({
                        "next_image_id": self.Next_ID,
                        "images": []
                    }, File)
            return True
        except (FileNotFoundError, OSError, TypeError, ValueError):
            return False

    def Get_Next_Gallery_Num(self):
        Gallery_Numbers = []
        for File in Gallery.Galleries_Folder.iterdir():
            if File.is_file() and File.stem.startswith("Gallery_"):
                try:
                    Number = int(File.stem.removeprefix("Gallery_"))
                    Gallery_Numbers.append(Number)
                except ValueError:
                    continue
        return max(Gallery_Numbers, default=0) + 1

    def Save_Gallery(self):
        Image_Data = []
        for img in self.Images:
            Image_Data.append(img.Get_Image_Info())
        try:
            with open(self.Gallery_File, "w") as File:
                json.dump({
                    "next_image_id": self.Next_ID,
                    "images": Image_Data
                }, File)
            return True
        except (FileNotFoundError, OSError, TypeError, ValueError):
            return False

    def Load_Gallery (self):
        Images = []
        try:
            with open(self.Gallery_File, "r") as File:
                Data = json.load(File)
                Image_Data = Data["images"]
                self.Next_ID = Data["next_image_id"]
                for img in Image_Data:
                    image = Image(img["image_path"], img["image_id"], img["image_tags"], img["image_aspect_ratio"])
                    self.Images.append(image)
                return True
        except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
            return False
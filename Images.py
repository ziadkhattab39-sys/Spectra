from PIL import Image as PILImage
from pathlib import Path
from math import gcd 

class Image:
    DEFAULT_TAGS = ["Nature", "Architecture", "Portrait", "Landscape", "Street", "Wildlife", "Technology", "Travel"]
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".ico"}
    
    def __init__(self, path, ID, Tags=None, Ratio=""):
        self.Img_ID = ID
        self.Img_Path = Path(path)
        self.Img_Name = self.Img_Path.name
        self.Img_Format = self.Img_Path.suffix.lower()
        self.Tags = Tags.copy() if Tags is not None else []
        self.Aspect_Ratio = Ratio
    
    def Validate_Image(self):
        if self.Img_Format not in self.SUPPORTED_FORMATS:
            return False
        try:
            with PILImage.open(self.Img_Path) as Img:
                Expected_Format = PILImage.registered_extensions().get(self.Img_Format)
                if Expected_Format != Img.format:
                    return False
                Img.verify()
            with PILImage.open(self.Img_Path) as Img:
                Img.load()
            return True
        except (OSError, ValueError, SyntaxError, PILImage.DecompressionBombError):
            return False
    
    def Add_Tag(self, Tag):
        if not isinstance(Tag, str):
            return False
        Tag = Tag.strip()
        if not Tag:
            return False
        if Tag.lower() in [Existing_Tag.lower() for Existing_Tag in self.Tags]:
            return False
        self.Tags.append(Tag)
        return True
    
    def Remove_Tag(self, Tag):
        if not isinstance(Tag, str):
            return False
        Tag = Tag.strip()
        if not Tag:
            return False
        for Existing_Tag in self.Tags:
            if Existing_Tag.lower() == Tag.lower():
                self.Tags.remove(Existing_Tag)
                return True
        return False
    
    def Set_Aspect_Ratio(self, Width, Height):
        if not isinstance(Width, int) or not isinstance(Height, int):
            return False
        if Width <= 0 or Height <= 0:
            return False
        Divisor = gcd(Width, Height)
        self.Aspect_Ratio = f"{Width // Divisor}:{Height // Divisor}"
        return True
    
    def Get_Image_Info (self):
        Info = {
            "image_id": self.Img_ID,
            "image_name": self.Img_Name,
            "image_path": str(self.Img_Path),
            "image_format": self.Img_Format,
            "image_aspect_ratio": self.Aspect_Ratio,
            "image_tags": self.Tags.copy()
        }
        return Info
class Tag_Manager :
    def __init__ (self):
        self.All_Tags = []

    def Get_All_Tags(self, gallery):
        images = gallery.Images
        tags = []
        for img in images:
            for tag in img.Tags:
                if tag not in tags:
                    tags.append(tag)
        return tags

    def Search_By_Single_Tag (self, gallery, Key_tag):
        images = gallery.Images
        Result = []
        for img in images:
            if Key_tag in img.Tags:
                Result.append(img)
        return Result

    def Advanced_Search_By_Tags(self, gallery, Tags, Search_Mode):
        Images = gallery.Images
        Result = []
        for img in Images:
            if Search_Mode == "AND":
                if all(tag in img.Tags for tag in Tags):
                    Result.append(img)
            elif Search_Mode == "OR":
                if any(tag in img.Tags for tag in Tags):
                    Result.append(img)
        return Result

    def Get_Tag_Count(self, gallery):
        self.All_Tags = self.Get_All_Tags(gallery)
        Tags_Count = {tag: 0 for tag in self.All_Tags}
        for img in gallery.Images:
            for tag in img.Tags:
                Tags_Count[tag] += 1
        return Tags_Count

    def Get_Popular_Tags(self, gallery, Top = 5):
        Tag_Count = self.Get_Tag_Count(gallery)
        Tags_List = list(Tag_Count.items())
        Tags_List = sorted(Tags_List, key= lambda tag: tag[1], reverse=True)
        Result = Tags_List[0:Top]
        return Result
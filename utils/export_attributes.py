class ExportAttributesCache:
    current_obj_name = None
    # current_mesh = None

    @classmethod
    def set_obj_name(cls, obj_name=None):
        cls.current_obj_name = obj_name
import bpy
from ..base import LuxCoreNodeTexture

from ...utils.export_attributes import ExportAttributesCache
from ...utils import sanitize_luxcore_name

class LuxCoreNodeAttribute(LuxCoreNodeTexture, bpy.types.Node):
    bl_label = "Attribute"

    attribute_name : bpy.props.StringProperty(
        name="Name",
        description="Name of the attribute to retrieve",
        default="",
    )

    attribute_type: bpy.props.EnumProperty(
        name="Attribute Type",
        description="Type of the attribute to retrieve",
        items=[("geometry", "Geometry", ""),
               ("object", "Object", ""),
               ("viewlayer", "View Layer", ""),
               ("instancer", "Instancer", "")],
        default="geometry",
    )

    color_value: bpy.props.FloatVectorProperty(
        name="Color Value",
        subtype='COLOR',
        size=3,
        default=(0.8, 0.8, 0.8),
        min=0.0,
        max=1.0,
    )

    def update_color_value(self, obj_name=None):
        attr_name = self.attribute_name.strip()
        if attr_name == "":
            # Default color if no attribute name is given
            self.color_value = (0.8, 0.8, 0.8)
        else:
            # check if the attribute is a custom object porperty
            obj = bpy.data.objects[obj_name]
            if attr_name in obj:
                val = obj[attr_name]
                if isinstance(val, (int, float)):
                    self.color_value = (val, val, val)
                elif len(val) == 3:
                    self.color_value = (val[0], val[1], val[2])
                else:
                    self.color_value = (0.0, 0.0, 1.0)
            else:
                # Attribute not found, use a default color
                self.color_value = (1.0, 0.0, 0.0)

    def init(self, context):
        self.outputs.new("LuxCoreSocketColor", "Color")
        self.outputs.new("LuxCoreSocketVector", "Vector")
        self.outputs.new("LuxCoreSocketFloatUnbounded", "Fac")
        self.outputs.new("LuxCoreSocketFloat0to1", "Alpha")

    def draw_buttons(self, context, layout):
        layout.prop(self, "attribute_type")
        layout.prop(self, "attribute_name")

    def sub_export(self, exporter, depsgraph, props, luxcore_name=None, output_socket=None):
        obj_name = ExportAttributesCache.current_obj_name
        # object name must be included in this key as well because self.create_props
        # will otherwise return the same string for different objects
        luxcore_name = sanitize_luxcore_name(obj_name + luxcore_name)
        self.update_color_value(obj_name=obj_name)
        definitions = {
            "type": "constfloat3",
            "value": list(self.color_value),
        }
        return self.create_props(props, definitions, luxcore_name)

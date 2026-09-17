import os

import bmesh
import bpy


def _export_mesh_by_material(obj, directory, apply_modifiers=True, apply_world_transform=False):
    """Export obj's mesh as one PLY file per used material slot.

    Filenames follow "<obj.name><material_index:03d>.ply", the naming scheme
    BlendLuxCore's proxy auto-detection expects (export/mesh_converter.py).
    """
    base_name = obj.name

    eval_obj = None
    if apply_modifiers:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
    else:
        mesh = obj.data

    if apply_world_transform:
        mesh.transform(obj.matrix_world)

    used_indices = sorted({poly.material_index for poly in mesh.polygons})
    if not used_indices:
        used_indices = [0]

    exported_files = []
    original_selection = list(bpy.context.selected_objects)
    original_active = bpy.context.view_layer.objects.active

    try:
        for mat_index in used_indices:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.faces.ensure_lookup_table()

            keep_verts = set()
            for f in bm.faces:
                if f.material_index == mat_index:
                    keep_verts.update(f.verts)

            verts_to_delete = [v for v in bm.verts if v not in keep_verts]
            bmesh.ops.delete(bm, geom=verts_to_delete, context="VERTS")

            if len(bm.faces) == 0:
                bm.free()
                continue

            temp_mesh = bpy.data.meshes.new(f"{base_name}_tmp_{mat_index:03d}")
            bm.to_mesh(temp_mesh)
            bm.free()

            temp_obj = bpy.data.objects.new(f"{base_name}_tmp_{mat_index:03d}", temp_mesh)
            bpy.context.collection.objects.link(temp_obj)

            bpy.ops.object.select_all(action="DESELECT")
            temp_obj.select_set(True)
            bpy.context.view_layer.objects.active = temp_obj

            filepath = os.path.join(directory, f"{base_name}{mat_index:03d}.ply")

            if hasattr(bpy.ops.wm, "ply_export"):
                bpy.ops.wm.ply_export(
                    filepath=filepath,
                    export_selected_objects=True,
                    export_normals=True,
                    export_uv=True,
                    export_colors="SRGB",
                )
            else:
                bpy.ops.export_mesh.ply(
                    filepath=filepath,
                    use_selection=True,
                    use_normals=True,
                    use_uv_coords=True,
                    use_colors=True,
                )

            exported_files.append(filepath)

            bpy.data.objects.remove(temp_obj, do_unlink=True)
            bpy.data.meshes.remove(temp_mesh)
    finally:
        if eval_obj is not None:
            eval_obj.to_mesh_clear()
        bpy.ops.object.select_all(action="DESELECT")
        for o in original_selection:
            o.select_set(True)
        bpy.context.view_layer.objects.active = original_active

    return exported_files


class LUXCORE_OT_generate_proxy(bpy.types.Operator):
    bl_idname = "luxcore.generate_proxy"
    bl_label = "Generate Proxy"
    bl_description = (
        "Export this object's mesh, split into one PLY file per material, into "
        "proxy/<object name>/meshes/ next to the .blend file, and set it up as proxy"
    )
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({"ERROR"}, "Save the .blend file first (proxy files are saved next to it)")
            return {"CANCELLED"}

        obj = context.object
        directory = bpy.path.abspath(f"//proxy/{obj.name}/meshes/")
        os.makedirs(directory, exist_ok=True)

        files = _export_mesh_by_material(
            obj, directory, apply_modifiers=obj.luxcore.proxy_apply_modifiers
        )

        if not files:
            self.report({"ERROR"}, "No geometry exported (empty mesh?)")
            return {"CANCELLED"}

        obj.luxcore.scene_shape = files[0]
        obj.luxcore.use_proxy = True

        self.report({"INFO"}, f"Generated {len(files)} proxy file(s) in {directory}")
        return {"FINISHED"}

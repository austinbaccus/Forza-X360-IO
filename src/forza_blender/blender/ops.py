import bpy # type: ignore
from pathlib import Path
from mathutils import Matrix # type: ignore
from bpy.types import Operator # type: ignore
from bpy.props import StringProperty # type: ignore
from forza_blender.forza.models.model_util import generate_meshes_from_pvs
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.utils.mesh_util import convert_forzamesh_into_blendermesh
from forza_blender.forza.textures.read_bix import Bix
from forza_blender.forza.textures.texture_util import *

indexed_textures = {}

class FORZA_OT_track_import(Operator):
    bl_idname = "forza.import_track"
    bl_label = "Import Track Models"
    
    def execute(self, context):
        if context.scene.forza_selection == "FM3":
            _import_fm3(context, context.scene.forza_last_track_folder)
        return {'FINISHED'}
    
class FORZA_OT_generate_textures(Operator):
    bl_idname = "forza.generate_textures"
    bl_label = "Generate Textures"
    
    def execute(self, context):
        if context.scene.forza_selection == "FM3":
            path_bin: Path = Path(context.scene.forza_last_track_folder) / "bin"
            path_textures: Path = list(path_bin.glob("*.bix"))
            _populate_indexed_textures_from_track(path_textures, save_files=True)
        return {'FINISHED'}

class FORZA_OT_pick_track_folder(Operator):
    """Choose a folder and return its path"""
    bl_idname = "forza.pick_track_folder"
    bl_label = "Pick Track Folder"
    bl_description = "Open a file browser to select a folder"
    directory: StringProperty(name="Folder", description="Folder to process", subtype='DIR_PATH') # type: ignore

    def execute(self, context):
        dir_path = Path(bpy.path.abspath(self.directory)).resolve()

        if not dir_path.exists() or not dir_path.is_dir():
            self.report({'ERROR'}, "Please pick a valid folder")
            return {'CANCELLED'}

        context.scene.forza_last_track_folder = str(dir_path)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
class FORZA_OT_pick_texture_folder(Operator):
    """Choose a folder and return its path"""
    bl_idname = "forza.pick_texture_folder"
    bl_label = "Pick Texture Folder"
    bl_description = "Open a file browser to select a folder"
    directory: StringProperty(name="Folder", description="Folder to process", subtype='DIR_PATH') # type: ignore

    def execute(self, context):
        dir_path = Path(bpy.path.abspath(self.directory)).resolve()

        if not dir_path.exists() or not dir_path.is_dir():
            self.report({'ERROR'}, "Please pick a valid folder")
            return {'CANCELLED'}

        context.scene.forza_last_texture_folder = str(dir_path)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

classes = (FORZA_OT_pick_track_folder,FORZA_OT_pick_texture_folder,FORZA_OT_track_import,FORZA_OT_generate_textures)


def register():
    for c in classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes): bpy.utils.unregister_class(c)

def _import_fm3(context, track_path: Path):
    if type(track_path) is not Path:
        track_path = Path(track_path)

    # get paths to important folders and files
    path_bin: Path = track_path / "bin"
    path_shaders: Path = path_bin / "shaders"
    path_textures: Path = list(path_bin.glob("*.bix"))
    path_ribbon: Path = track_path / "Ribbon_00"
    path_ribbon_pvs: Path = list(path_ribbon.glob("*.pvs"))[0]
    
    # textures
    if not context.scene.use_pregenerated_textures:
        raise RuntimeError("Importing tracks without pre-generated textures is not implemented yet.")
        #textures = _get_textures_from_track(path_textures)

    # meshes
    meshes: list[ForzaMesh] = _get_meshes_from_track(path_bin, path_ribbon_pvs, context)
    i = 0
    for instance_mesh in meshes:
        if context.scene.generate_lods: _add_mesh_to_scene(context, instance_mesh, path_bin)
        elif "LOD01" not in instance_mesh.name and "LOD02" not in instance_mesh.name: _add_mesh_to_scene(context, instance_mesh, path_bin) # TODO needs a more elegant solution  
        i = i + 1
        print(f"[{i}/{len(meshes)}]")

def _populate_indexed_textures_from_track(path_textures, save_files: bool = False):
    i = 0
    for path_texture in path_textures:
        filename = str(path_texture.resolve())
        if not filename.endswith("_B.bix"):
            img = Bix.get_image_from_bix(path_texture.resolve(), save_image=save_files)
            texture_idx = int(convert_texture_name_to_decimal(str(path_texture.stem)))
            indexed_textures[texture_idx] = img
        i = i + 1
        print(f"[{i}/{len(path_textures)}]")

def _get_meshes_from_track(path_bin: Path, path_ribbon_pvs: Path, context) -> list[ForzaMesh]:
    return generate_meshes_from_pvs(path_bin, path_ribbon_pvs, context)

def _add_mesh_to_scene(context, forza_mesh, path_bin: Path):
    blender_mesh = convert_forzamesh_into_blendermesh(forza_mesh)
    obj = bpy.data.objects.new(forza_mesh.name, blender_mesh)

    # material
    if context.scene.generate_mats:
        if context.scene.use_pregenerated_textures:
            mat = generate_material_from_texture_indices(forza_mesh.name, forza_mesh.textures, context.scene.forza_last_texture_folder)
        else:
            raise RuntimeError("Importing materials without pre-generated textures is not implemented yet.")
            mat = generate_material_from_textures(forza_mesh.name, forza_mesh.textures, path_bin)
        if obj.data.materials: obj.data.materials[0] = mat
        else: obj.data.materials.append(mat)
    
    # convert mesh to Blender coordinate system
    m = Matrix(forza_mesh.transform)
    m = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))) @ m # Forza->Blender coordinate system
    obj.matrix_world = m

    # --- UVs ---
    mesh = obj.data
    # Create or fetch a UV layer
    uv_layer = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.active = uv_layer

    # Many DirectX pipelines (Forza likely included) treat (0,0) at the TOP-left,
    # while Blender uses BOTTOM-left. Flip V if your textures look upside-down.
    FLIP_V = False

    # Prebuild a vertex->uv lookup (Vector2)
    # texture0 is expected to already be normalized [0,1] (you’re using _ushort_n)
    vert_uv = []
    for v in forza_mesh.vertices:
        u, v0 = float(v.texture0.x), float(v.texture0.y)
        if FLIP_V:
            v0 = 1.0 - v0
        vert_uv.append((u, v0))

    # Assign per-loop: loop.vertex_index tells which vertex this corner uses
    # No mode switch needed as we’re writing datablock arrays.
    for li, loop in enumerate(mesh.loops):
        vi = loop.vertex_index
        # Safety check in case of vertex reindexing or deduplication
        if 0 <= vi < len(vert_uv):
            uv_layer.data[li].uv = vert_uv[vi]
        else:
            # Fallback: write 0,0 if something’s off
            uv_layer.data[li].uv = (0.0, 0.0)

    mesh.update()

    bpy.context.collection.objects.link(obj)
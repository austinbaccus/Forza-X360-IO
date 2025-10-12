import bpy # type: ignore
from pathlib import Path
from mathutils import Matrix # type: ignore
from bpy.types import Operator # type: ignore
from bpy.props import StringProperty # type: ignore
from forza_blender.forza.models.model_util import generate_meshes_from_pvs
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.utils.mesh_util import convert_forzamesh_into_blendermesh
from forza_blender.forza.uv.uv_util import generate_and_assign_uv_layers_to_object
from forza_blender.forza.textures.read_bix import Bix
from forza_blender.forza.textures.texture_util import *
from forza_blender.forza.shaders.shaders import *

indexed_textures = {}

class FORZA_OT_track_import(Operator):
    bl_idname = "forza.import_track"
    bl_label = "Import Track Models"
    
    def execute(self, context):
        if context.scene.forza_selection == "FM3":
            _import_fm3(context, context.scene.forza_last_track_folder, context.scene.forza_last_ribbon_folder)
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
    
class FORZA_OT_pick_ribbon_folder(Operator):
    """Choose a folder and return its path"""
    bl_idname = "forza.pick_ribbon_folder"
    bl_label = "Pick Ribbon Folder"
    bl_description = "Open a file browser to select a folder"
    directory: StringProperty(name="Folder", description="Folder to process", subtype='DIR_PATH') # type: ignore

    def execute(self, context):
        dir_path = Path(bpy.path.abspath(self.directory)).resolve()

        if not dir_path.exists() or not dir_path.is_dir():
            self.report({'ERROR'}, "Please pick a valid folder")
            return {'CANCELLED'}

        context.scene.forza_last_ribbon_folder = str(dir_path)
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

classes = (FORZA_OT_pick_track_folder,FORZA_OT_pick_ribbon_folder,FORZA_OT_pick_texture_folder,FORZA_OT_track_import,FORZA_OT_generate_textures)


def register():
    for c in classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes): bpy.utils.unregister_class(c)

def _import_fm3(context, track_path: Path, path_ribbon: Path):
    if type(track_path) is not Path:
        track_path = Path(track_path)
    if type(path_ribbon) is not Path:
        path_ribbon = Path(path_ribbon)

    # get paths to important folders and files
    path_bin: Path = track_path / "bin"
    path_shaders: Path = path_bin / "shaders"
    path_textures: Path = list(path_bin.glob("*.bix"))
    if not path_ribbon.exists():
        path_ribbon: Path = track_path / "Ribbon_01"
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
            mats = generate_blender_materials_for_mesh(forza_mesh, context.scene.forza_last_texture_folder)
        else:
            raise RuntimeError("Importing materials without pre-generated textures is not implemented yet.")
            mat = generate_material_from_textures(forza_mesh.name, forza_mesh.textures, path_bin)
        for mat in mats:
            obj.data.materials.append(mat)
    
    # convert mesh to blender coordinate system
    m = Matrix(forza_mesh.transform)
    m = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))) @ m # Forza->Blender coordinate system
    obj.matrix_world = m

    # uv
    generate_and_assign_uv_layers_to_object(obj, forza_mesh)

    bpy.context.collection.objects.link(obj)


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

class FORZA_OT_import(Operator):
    bl_idname = "forza.import"
    bl_label = "Import"
    
    def execute(self, context):
        if context.scene.forza_selection == "FM3":
            import_fm3(context, context.scene.forza_last_folder)
        return {'FINISHED'}

class FORZA_OT_pick_folder(Operator):
    """Choose a folder and return its path"""
    bl_idname = "forza.pick_folder"
    bl_label = "Pick Folder"
    bl_description = "Open a file browser to select a folder"
    directory: StringProperty(name="Folder", description="Folder to process", subtype='DIR_PATH') # type: ignore

    def execute(self, context):

        dir_path = Path(bpy.path.abspath(self.directory)).resolve()

        if not dir_path.exists() or not dir_path.is_dir():
            self.report({'ERROR'}, "Please pick a valid folder")
            return {'CANCELLED'}

        context.scene.forza_last_folder = str(dir_path)

        print(f"[FORZA] Folder selected: {dir_path} | FM mode: {context.scene.forza_selection}")
        self.report({'INFO'}, f"Folder: {dir_path.name}")
        self.report({'INFO'}, f"Folder: {dir_path.name} (Mode: {context.scene.forza_selection})")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

classes = (FORZA_OT_pick_folder,FORZA_OT_import)

path_decompressed_textures: Path = Path("X:/3d/games/forza/tracks/amalfi_coast/amalfi_huge/textures/bmp")

def register():
    for c in classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes): bpy.utils.unregister_class(c)

def import_fm3(context, track_path: Path):
    if type(track_path) is not Path:
        track_path = Path(track_path)

    # get paths to important folders and files
    path_bin: Path = track_path / "bin"
    path_shaders: Path = path_bin / "shaders"
    path_textures: Path = list(path_bin.glob("*.bix"))
    path_ribbon: Path = track_path / "Ribbon_00"
    path_ribbon_pvs: Path = list(path_ribbon.glob("*.pvs"))[0]
    
    # textures
    if context.scene.generate_textures: 
        textures = _get_textures_from_track(path_textures)

    # meshes
    meshes: list[ForzaMesh] = _get_meshes_from_track(path_bin, path_ribbon_pvs, context)
    i = 0
    for instance_mesh in meshes:
        if context.scene.generate_lods: _add_mesh_to_scene(context, instance_mesh, path_bin)
        elif "LOD01" not in instance_mesh.name and "LOD02" not in instance_mesh.name: _add_mesh_to_scene(context, instance_mesh, path_bin) # TODO needs a more elegant solution  
        i = i + 1
        print(f"[{i}/{len(meshes)}]")
        

def _get_textures_from_track(path_textures):
    textures = []
    i = 0
    for path_texture in path_textures:
        filename = str(path_texture.resolve())
        if not filename.endswith("_B.bix"):
            img = Bix.get_image_from_bix(path_texture.resolve())
            textures.append(img)
        i = i + 1
        print(f"[{i}/{len(path_textures)}]")
    return textures

def _get_meshes_from_track(path_bin: Path, path_ribbon_pvs: Path, context) -> list[ForzaMesh]:
    return generate_meshes_from_pvs(path_bin, path_ribbon_pvs, context)

def _add_mesh_to_scene(context, forza_mesh, path_bin: Path):
    blender_mesh = convert_forzamesh_into_blendermesh(forza_mesh)
    obj = bpy.data.objects.new(forza_mesh.name, blender_mesh)

    if context.scene.generate_mats:
        mat = generate_material_from_textures(forza_mesh.name, forza_mesh.textures, path_bin)
        if obj.data.materials: obj.data.materials[0] = mat
        else: obj.data.materials.append(mat)
    
    m = Matrix(forza_mesh.transform)
    m = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))) @ m # Forza->Blender coordinate system
    obj.matrix_world = m

    bpy.context.collection.objects.link(obj)
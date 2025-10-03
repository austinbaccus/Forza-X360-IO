from pathlib import Path
import bpy # type: ignore
import math
from bpy.types import Operator # type: ignore
from bpy.props import StringProperty # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.utils.mesh_utils import convert_forzamesh_into_blendermesh
from forza_blender.forza.pvs.read_pvs import PVS
from forza_blender.forza.pvs.pvs_util import BinaryStream
from forza_blender.forza.textures.read_bix import Bix
from forza_blender.forza.textures.texture_util import *

class FORZA_OT_import(Operator):
    bl_idname = "forza.import"
    bl_label = "Import"
    
    def execute(self, context):
        if context.scene.forza_selection == "FM3":
            import_fm3(context, context.scene.forza_last_folder)
        if context.scene.forza_selection == "FM4":
            import_fm4(context, context.scene.forza_last_folder)
        return {'FINISHED'}

class FORZA_OT_pick_folder(Operator):
    """Choose a folder and return its path"""
    bl_idname = "forza.pick_folder"
    bl_label = "Pick Folder"
    bl_description = "Open a file browser to select a folder"
    directory: StringProperty(name="Folder", description="Folder to process", subtype='DIR_PATH')

    def execute(self, context):

        dir_path = Path(bpy.path.abspath(self.directory)).resolve()

        if not dir_path.exists() or not dir_path.is_dir():
            self.report({'ERROR'}, "Please pick a valid folder")
            return {'CANCELLED'}

        context.scene.forza_last_folder = str(dir_path)
        #forza_selection = context.scene.forza_selection # getattr(context.scene, "forza_selection", "FM3")

        # TODO: replace with your processing
        print(f"[FORZA] Folder selected: {dir_path} | FM mode: {context.scene.forza_selection}")
        self.report({'INFO'}, f"Folder: {dir_path.name}")
        self.report({'INFO'}, f"Folder: {dir_path.name} (Mode: {context.scene.forza_selection})")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

classes = (FORZA_OT_pick_folder,FORZA_OT_import)

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
    textures = _get_textures(path_textures) # this takes a long time to finish. comment this line out unless you really need textures

    # meshes
    track_meshes = _get_meshes(context, path_bin)
    
    # pvs
    pvs = PVS.from_stream(BinaryStream.from_path(path_ribbon_pvs.resolve(), ">"))

    # TODO
    # assign textures to models using pvs
    # map track_meshes which model_indexes
    # duplicate instances
    models_indexes = list(set([model_instance.model_index for model_instance in pvs.models_instances]))
    models_indexes = sorted(models_indexes)
    j = 0
    for i in range(len(pvs.models)):
        if models_indexes[j] != i:
            print(i)
            continue
        j += 1

    # add all objects to the scene
    _add_meshes_to_scene(track_meshes)

def _get_textures(path_textures):
    textures = []
    for path_texture in path_textures:
        filename = str(path_texture.resolve())
        if not filename.endswith("_B.bix"):
            img = Bix.get_image_from_bix(path_texture.resolve())
            textures.append(img)
    return textures

def _get_meshes(context, path_bin):
    from ..forza.models.read_rmbbin import RmbBin
    track_meshes = []
    for path_trackbin in path_bin.glob("*.rmb.bin"):
        track_bin = RmbBin(path_trackbin)
        track_bin.populate_objects_from_rmbbin()
        if track_bin.forza_version.name != context.scene.forza_selection:
            raise RuntimeError("Forza version mismatch!")
        for track_section in track_bin.track_sections:
            for track_subsection in track_section.subsections: # each subsection is a mesh
                meshName: str = path_bin.name + "_" + track_section.name + "_" + track_subsection.name
                forza_mesh = ForzaMesh(meshName, track_subsection.name, track_subsection.indices, track_subsection.vertices)
                track_meshes.append(forza_mesh)
    return track_meshes

def _add_meshes_to_scene(track_meshes):
    for forza_mesh in track_meshes:
        blender_mesh = convert_forzamesh_into_blendermesh(forza_mesh)
        obj = bpy.data.objects.new(forza_mesh.name, blender_mesh)
        obj.rotation_euler = (math.radians(90), 0, 0)
        bpy.context.collection.objects.link(obj)
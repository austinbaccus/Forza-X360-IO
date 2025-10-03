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
from ..forza.models.read_rmbbin import RmbBin

class FORZA_OT_import(Operator):
    bl_idname = "forza.import"
    bl_label = "Import"
    
    def execute(self, context):
        if context.scene.forza_selection == "FM3":
            import_fm3(context, context.scene.forza_last_folder)
        #if context.scene.forza_selection == "FM4":
            #import_fm4(context, context.scene.forza_last_folder)
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
    #textures = _get_textures(path_textures) # this takes a long time to finish. comment this line out unless you really need textures

    # meshes
    meshes: list[ForzaMesh] = _get_instanced_meshes(path_bin, path_ribbon_pvs, context)
    for instance_mesh in meshes: _add_mesh_to_scene(instance_mesh)


def _get_textures(path_textures):
    textures = []
    for path_texture in path_textures:
        filename = str(path_texture.resolve())
        if not filename.endswith("_B.bix"):
            img = Bix.get_image_from_bix(path_texture.resolve())
            textures.append(img)
    return textures

def _get_all_meshes_from_folder(context, path_bin):
    track_meshes = []

    for path_trackbin in path_bin.glob("*.rmb.bin"):
        if path_trackbin.name.endswith(".sky.rmb.bin"):
            continue # ignore for now - this has special logic
        else:
            track_model_index = int(str(path_trackbin.name).split('.')[1]) # get .rmb.bin model_int out of filename
            #if track_model_index not in model_indexes:
                #continue # if it's not in the model indexes... ignore it
            
        # continue here...
        # track_model_index 13 --> Amalfiout.00013.rmb.bin

        # great! now you have the pvs_model loaded

        # loop through each model_instance, 
        #   get the position+rotation data for it
        #   get the model mesh associated with it
        #   duplicate it!
        pvs_model_instances = []
        # ...

        track_meshes.extend(_get_meshes_from_rmbbin(path_trackbin, path_bin, context))
    return track_meshes

def _get_meshes_from_rmbbin(path_trackbin: Path, path_bin: Path, context, translation = None):
    track_bin = RmbBin(path_trackbin)
    rmbbin_meshes = []
    track_bin.populate_objects_from_rmbbin()

    if track_bin.forza_version.name != context.scene.forza_selection:
        raise RuntimeError("Forza version mismatch!")
    for track_section in track_bin.track_sections:
        for track_subsection in track_section.subsections:
            meshName: str = path_bin.name + "_" + track_section.name + "_" + track_subsection.name
            forza_mesh = ForzaMesh(meshName, track_subsection.name, track_subsection.indices, track_subsection.vertices, position=translation)
            rmbbin_meshes.append(forza_mesh)

    return rmbbin_meshes

def _get_instanced_meshes(path_bin, path_ribbon_pvs, context) -> list[ForzaMesh]:
    # generate file_paths for all .rmb.bins
    rmbbin_files = {}
    for path_rmbbin in path_bin.glob("*.rmb.bin"):
        if path_rmbbin.name.endswith(".sky.rmb.bin"):
            continue # ignore for now - this has special logic
        else:
            rmbbin_index = int(str(path_rmbbin.name).split('.')[1]) # get .rmb.bin model_int out of filename
            rmbbin_files[rmbbin_index] = path_rmbbin

    instance_meshes = []
    pvs = PVS.from_stream(BinaryStream.from_path(path_ribbon_pvs.resolve(), ">"))
    i = 0
    z = len(pvs.models_instances)
    for pvs_model_instance in pvs.models_instances:
        try:
            path_to_rmbbin = rmbbin_files[pvs_model_instance.model_index]
            pvs_model_meshes = _get_meshes_from_rmbbin(path_to_rmbbin, path_bin, context, pvs_model_instance.position)
            instance_meshes.extend(pvs_model_meshes)
        except:
            print("Problem getting mesh from " + path_to_rmbbin.name)
        
        i = i + 1
        print(f"[{i}/{z}]")
        
    return instance_meshes

def _add_mesh_to_scene(forza_mesh):
    blender_mesh = convert_forzamesh_into_blendermesh(forza_mesh)
    obj = bpy.data.objects.new(forza_mesh.name, blender_mesh)
    
    if forza_mesh.position != None:
        obj.location = forza_mesh.position
    if forza_mesh.rotation != None:
        obj.rotation_euler = forza_mesh.rotation
    if forza_mesh.scale != None:
        obj.scale = forza_mesh.scale

    bpy.context.collection.objects.link(obj)
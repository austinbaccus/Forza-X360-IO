from pathlib import Path
import bpy # type: ignore
import math
from bpy.types import Operator # type: ignore
from bpy.props import StringProperty # type: ignore
from mathutils import Matrix # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.utils.mesh_utils import convert_forzamesh_into_blendermesh
from forza_blender.forza.pvs.read_pvs import PVS, PVSTexture
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
    #textures = _get_textures(path_textures)

    # meshes
    meshes: list[ForzaMesh] = _get_instanced_meshes(path_bin, path_ribbon_pvs, context)
    for instance_mesh in meshes: _add_mesh_to_scene(instance_mesh, path_bin)


def _get_textures(path_textures):
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

def _get_meshes_from_rmbbin(path_trackbin: Path, path_bin: Path, context, transform, textures):
    track_bin = RmbBin(path_trackbin)
    rmbbin_meshes = []
    track_bin.populate_objects_from_rmbbin()

    if track_bin.forza_version.name != context.scene.forza_selection:
        raise RuntimeError("Forza version mismatch!")
    for track_section in track_bin.track_sections:
        for track_subsection in track_section.subsections:
            meshName: str = path_trackbin.name.split('.')[1] + " " + track_section.name + " " + track_subsection.name
            forza_mesh = ForzaMesh(meshName, track_subsection.name, track_subsection.indices, track_subsection.vertices, transform=transform, model_index=int(path_trackbin.name.split('.')[1]), textures=textures)
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
    pvs: PVS = PVS.from_stream(BinaryStream.from_path(path_ribbon_pvs.resolve(), ">"))

    i = 0
    for pvs_model_instance in pvs.models_instances:
        try:
            pvs_model = pvs.models[pvs_model_instance.model_index]
            pvs_texture_filenames = []
            for texture_idx in pvs_model.textures:
                pvs_texture_filenames.append(pvs.textures[texture_idx]) # this may be in decimal or hex, not sure yet


            path_to_rmbbin = rmbbin_files[pvs_model_instance.model_index]
            pvs_model_meshes = _get_meshes_from_rmbbin(path_to_rmbbin, path_bin, context, pvs_model_instance.transform, pvs_texture_filenames)
            instance_meshes.extend(pvs_model_meshes)
        except:
            print("Problem getting mesh from " + path_to_rmbbin.name)
        
        i = i + 1
        print(f"[{i}/{len(pvs.models_instances)}]")
        
    return instance_meshes

def _create_material_from_textures(mat_name, textures: PVSTexture, path_bin: Path):
    # get texture
    images = []
    for texture in textures:
        filepath = path_bin / Path(texture.texture_file_name) / ".bix"
        img = Bix.get_image_from_bix(filepath.resolve())
        images.append(img)

    # create material
    mat = bpy.data.materials.new(mat_name)

    # TODO: add texture to material

    return mat

def _add_mesh_to_scene(forza_mesh, path_bin: Path):
    blender_mesh = convert_forzamesh_into_blendermesh(forza_mesh)
    obj = bpy.data.objects.new(forza_mesh.name, blender_mesh)

    obj.data.materials.append(_create_material_from_textures(forza_mesh.name, forza_mesh.textures))
    
    m = Matrix(forza_mesh.transform)
    m = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))) @ m # Forza->Blender coordinate system
    obj.matrix_world = m

    bpy.context.collection.objects.link(obj)

    # ....

    
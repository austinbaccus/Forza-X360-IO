import bpy # type: ignore
from pathlib import Path
from forza_blender.forza.pvs.pvs_util import BinaryStream
from forza_blender.forza.pvs.read_pvs import PVS
from forza_blender.forza.shaders.read_shader import FXLShader
from mathutils import Matrix # type: ignore
from bpy.types import Operator # type: ignore
from bpy.props import StringProperty # type: ignore
from forza_blender.forza.models.model_util import generate_meshes_from_pvs, generate_meshes_from_pvs_model_instance, get_rmbbin_files, get_shaders
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
    
class FORZA_OT_track_import_modal(Operator):
    bl_idname = "forza.import_track_modal"
    bl_label = "Import Track"
    bl_options = {'REGISTER', 'INTERNAL'}

    def _step(self, context):
        """Do a small chunk of work and return True if more remains."""
        if self.idx < len(self.pvs.models_instances):
            item = self.pvs.models_instances[self.idx]
            instance_meshes = generate_meshes_from_pvs_model_instance(item, self.pvs, self.rmbbin_files, self.shaders, context)
            if instance_meshes is not None:
                for instance_mesh in instance_meshes:
                    if instance_mesh is not None:
                        _add_mesh_to_scene(context, instance_mesh, self.path_bin)

            # update status/progress
            context.workspace.status_text_set(f"Processing {self.idx+1}/{len(self.pvs.models_instances)}: {item}")
            bpy.context.window_manager.progress_update(self.idx + 1)
            self.idx += 1
            return True
        return False

    def modal(self, context, event):
        if event.type == 'TIMER':
            steps_this_tick = 50
            for _ in range(steps_this_tick):
                if not self._step(context):
                    self._finish(context, ok=True)
                    return {'FINISHED'}
            return {'PASS_THROUGH'}

        elif event.type in {'ESC'}:
            self._finish(context, ok=False)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def _finish(self, context, ok=True):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        wm.progress_end()
        context.workspace.status_text_set(None)
        if ok:
            self.report({'INFO'}, "Import finished")
        else:
            self.report({'WARNING'}, "Import cancelled")

    def invoke(self, context, event):
        track_path = context.scene.forza_last_track_folder
        path_ribbon = context.scene.forza_last_ribbon_folder
        if type(track_path) is not Path: track_path = Path(track_path)
        if type(path_ribbon) is not Path: path_ribbon = Path(path_ribbon)
        self.path_bin: Path = track_path / "bin"
        path_ribbon_pvs: Path = list(path_ribbon.glob("*.pvs"))[0]

        # prepare workload
        self.rmbbin_files = get_rmbbin_files(self.path_bin)
        self.pvs: PVS = PVS.from_stream(BinaryStream.from_path(path_ribbon_pvs.resolve(), ">"))
        self.shaders: dict[str, FXLShader] = get_shaders(self.path_bin, self.pvs)
        
        #for instance_mesh in generate_meshes_from_pvs(path_bin, path_ribbon_pvs, context):
        #    _add_mesh_to_scene(context, instance_mesh, path_bin)

        self.idx = 0

        # Progress bar
        bpy.context.window_manager.progress_begin(0, len(self.pvs.models_instances))

        # Timer to drive modal steps
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.02, window=context.window)  # 50 FPS-ish
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

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

classes = (FORZA_OT_pick_track_folder,FORZA_OT_pick_ribbon_folder,FORZA_OT_pick_texture_folder,FORZA_OT_track_import,FORZA_OT_generate_textures,FORZA_OT_track_import_modal)


def register():
    for c in classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes): bpy.utils.unregister_class(c)

def _import_fm3(context, track_path: Path, path_ribbon: Path):
    if type(track_path) is not Path: track_path = Path(track_path)
    if type(path_ribbon) is not Path: path_ribbon = Path(path_ribbon)
    path_bin: Path = track_path / "bin"
    path_ribbon_pvs: Path = list(path_ribbon.glob("*.pvs"))[0]

    # meshes
    pvs, pvs_model_instances, models_to_load, model_meshes = _get_meshes_from_track(path_bin, path_ribbon_pvs, context)

    master_collection = bpy.data.collections.new("Models")
    model_collections = [None] * len(model_meshes)
    for i, (model_index, _, model_filename) in enumerate(models_to_load):
        if model_meshes[model_index] is None:
            continue
        collection = bpy.data.collections.new(F"{model_filename} {model_meshes[model_index][0].track_section.name}")
        for mesh in model_meshes[model_index]:
            _add_mesh_to_scene(context, mesh, path_bin, collection)
        master_collection.children.link(collection)
        model_collections[model_index] = collection
        print(f"[{i + 1}/{len(models_to_load)}]")
        bpy.context.workspace.status_text_set(f"[{i + 1}/{len(models_to_load)}] meshes imported")

    root_layer_collection = bpy.context.view_layer.layer_collection
    track_collection = bpy.data.collections.new(pvs.prefix)
    root_layer_collection.collection.children.link(track_collection)
    track_layer_collection = next(layer_collection for layer_collection in root_layer_collection.children if layer_collection.collection == track_collection)
    for pvs_model_instance in pvs_model_instances:
        if model_collections[pvs_model_instance.model_index] is None:
            continue
        collection_instance = bpy.data.objects.new(model_collections[pvs_model_instance.model_index].name, object_data=None)
        collection_instance.instance_type = "COLLECTION"
        collection_instance.instance_collection = model_collections[pvs_model_instance.model_index]

        # convert mesh to blender coordinate system
        m = Matrix(pvs_model_instance.transform)
        m = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))) @ m # Forza->Blender coordinate system
        collection_instance.matrix_world = m

        track_layer_collection.collection.objects.link(collection_instance)
    track_layer_collection.collection.children.link(master_collection)
    master_layer_collection = next(layer_collection for layer_collection in track_layer_collection.children if layer_collection.collection == master_collection)
    master_layer_collection.exclude = True

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
        bpy.context.workspace.status_text_set(f"[{i}/{len(path_textures)}] textures generated")

def _get_meshes_from_track(path_bin: Path, path_ribbon_pvs: Path, context):
    return generate_meshes_from_pvs(path_bin, path_ribbon_pvs, context)

def _add_mesh_to_scene(context, forza_mesh, path_bin: Path, collection):
    blender_mesh = convert_forzamesh_into_blendermesh(forza_mesh)
    obj = bpy.data.objects.new(forza_mesh.name, blender_mesh)

    # material
    if context.scene.generate_mats:
        if context.scene.use_pregenerated_textures:
            mats = generate_blender_materials_for_mesh(forza_mesh, context.scene.forza_last_track_folder)
        else:
            raise RuntimeError("Importing materials without pre-generated textures is not implemented yet.")
        for mat in mats:
            obj.data.materials.append(mat)

    # uv
    generate_and_assign_uv_layers_to_object(obj, forza_mesh)

    collection.objects.link(obj)


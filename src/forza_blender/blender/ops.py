import bpy # type: ignore
import math
from pathlib import Path
from forza_blender.forza.pvs.pvs_util import BinaryStream
from forza_blender.forza.pvs.read_pvs import PVS
from forza_blender.forza.shaders.read_shader import FXLShader
from forza_blender.forza.textures.read_bin import CAFF
from mathutils import Matrix # type: ignore
from bpy.types import Operator # type: ignore
from bpy.props import StringProperty # type: ignore
from forza_blender.forza.models.model_util import generate_meshes_from_pvs, generate_meshes_from_pvs_model_instance, generate_meshes_from_rmbbin, get_rmbbin_files, get_shaders
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
                        _add_mesh_to_scene(context, instance_mesh, None) # TODO: this needs a collection arg now

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
    
class FORZA_OT_generate_bin_textures(Operator):
    bl_idname = "forza.generate_bin_textures"
    bl_label = "Generate .BIN Textures"
    
    def execute(self, context):
        if context.scene.forza_selection == "FM3":
            path_bin: Path = Path(context.scene.forza_last_track_folder) / "bin"
            path_bin_textures: Path = list(path_bin.glob("*.bin"))

            filtered_path_bin_textures = [
                f for f in path_bin_textures 
                if not f.name.endswith('rmb.bin')
            ]

            _populate_indexed_bin_textures_from_track(filtered_path_bin_textures, Path(context.scene.forza_last_track_folder), context.scene.forza_last_ribbon_folder)
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

classes = (FORZA_OT_track_import,FORZA_OT_pick_track_folder,FORZA_OT_pick_ribbon_folder,FORZA_OT_pick_texture_folder,FORZA_OT_generate_textures,FORZA_OT_generate_bin_textures,FORZA_OT_track_import_modal)


def register():
    for c in classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes): bpy.utils.unregister_class(c)

def _import_fm3(context, track_path: Path, path_ribbon: Path):
    path_bin: Path = Path(track_path) / "bin"
    path_textures: Path = path_bin / "textures"
    path_ribbon_pvs: Path = list(Path(path_ribbon).glob("*.pvs"))[0]

    # get pvs & shaders instances
    pvs: PVS = PVS.from_stream(BinaryStream.from_path(path_ribbon_pvs.resolve(), ">"))
    shaders: dict[str, FXLShader] = get_shaders(path_bin, pvs)

    # scan texture files
    existing_textures = set(p.name[3:11] for p in path_textures.glob("_0x????????.dds"))

    texture_files = [None] * len(pvs.textures)
    for i, pvs_texture in enumerate(pvs.textures):
        # TODO: replace by image file object
        file_index = pvs_texture.texture_file_name
        is_stx = False
        if F"{file_index:08X}" not in existing_textures:
            tmp_file_index = pvs_texture.index_in_stx_bin | 0x80000000
            if F"{tmp_file_index:08X}" in existing_textures:
                file_index = tmp_file_index
                is_stx = True
        texture_files[i] = (pvs_texture, file_index, is_stx)

    # figure out which models need to be loaded
    pvs_model_instances = [model_instance for model_instance in pvs.models_instances if context.scene.generate_lods or (model_instance.flags & (6 << 11)) == 0 or (model_instance.flags & (1 << 11)) != 0]
    pvs_model_instances.extend([model_instance for model_instance in pvs.lone_models_instances])
    unique_model_indexes = set([model_instance.model_index for model_instance in pvs_model_instances])
    models_to_load = [(model_index, pvs.models[model_index], F"{model_index:05d}") for model_index in unique_model_indexes]
    model_meshes: list[list[ForzaMesh] | None] = [None] * len(pvs.models)

    # add the skybox to the list of models to load (if it exists)
    if pvs.sky_model is not None:
        pvs.sky_model_instance.model_index = len(model_meshes)
        pvs_model_instances.append(pvs.sky_model_instance)
        models_to_load.append((pvs.sky_model_instance.model_index, pvs.sky_model, "sky"))
        model_meshes.append(None)

    # collect inherited textures
    models_inherited_textures = [list() for _ in range(len(model_meshes))]
    for i, pvs_model_instance in enumerate(pvs_model_instances):
        model_inherited_textures = models_inherited_textures[pvs_model_instance.model_index]
        _, file_index, _ = texture_files[pvs_model_instance.texture]
        if file_index not in model_inherited_textures:
            model_inherited_textures.append(file_index)

    # for each model in models_to_load, load the mesh and add it to model_meshes
    for i, (model_index, pvs_model, model_filename) in enumerate(models_to_load):
        model_textures = [texture_files[texture_idx] for texture_idx in pvs_model.textures]
        # TODO: check if all textures for a track section are being passed to the track subsection
        path_to_rmbbin = path_bin / F"{pvs.prefix}.{model_filename}.rmb.bin"
        try: model_meshes[model_index] = generate_meshes_from_rmbbin(path_to_rmbbin, context, model_textures, shaders, models_inherited_textures[model_index])
        except: print("Problem getting mesh from model index", model_index)
        if (i + 1) % 100 == 0:
            msg: str = f"[{i + 1}/{len(models_to_load)}] meshes imported"
            print(msg); bpy.context.workspace.status_text_set(msg)

    master_collection = bpy.data.collections.new("Models")
    model_collections = [None] * len(model_meshes)

    # for each mesh in model_meshes, add it to the scene
    for i, (model_index, _, model_filename) in enumerate(models_to_load):
        if model_meshes[model_index] is None:
            continue
        collection = bpy.data.collections.new(F"{model_filename} {model_meshes[model_index][0].track_section.name}")
        for mesh in model_meshes[model_index]:
            _add_mesh_to_scene(context, mesh, collection)
        master_collection.children.link(collection)
        model_collections[model_index] = collection
        if (i + 1) % 100 == 0:
            print(f"[{i + 1}/{len(models_to_load)}]")
            bpy.context.workspace.status_text_set(f"[{i + 1}/{len(models_to_load)}] meshes imported")

    # collections
    root_layer_collection = bpy.context.view_layer.layer_collection
    track_collection = bpy.data.collections.new(pvs.prefix)
    root_layer_collection.collection.children.link(track_collection)
    track_layer_collection = next(layer_collection for layer_collection in root_layer_collection.children if layer_collection.collection == track_collection)

    # generate models from pvs
    instances_parent = bpy.data.objects.new("Models Instances", object_data=None)
    for pvs_model_instance in pvs_model_instances:
        if model_collections[pvs_model_instance.model_index] is None:
            continue
        collection_instance = bpy.data.objects.new(model_collections[pvs_model_instance.model_index].name, object_data=None)
        collection_instance.instance_type = "COLLECTION"
        collection_instance.instance_collection = model_collections[pvs_model_instance.model_index]
        collection_instance.show_instancer_for_viewport = False
        collection_instance.parent = instances_parent

        pvs_texture, texture_file_index, is_stx = texture_files[pvs_model_instance.texture]
        collection_instance["texture"] = models_inherited_textures[pvs_model_instance.model_index].index(texture_file_index)
        if is_stx:
            collection_instance["uv_scale"] = (pvs_texture.u_scale, pvs_texture.v_scale)
            collection_instance["uv_translate"] = (pvs_texture.u_translate, -(pvs_texture.v_scale + pvs_texture.v_translate))
        else:
            collection_instance["uv_scale"] = (1, 1)
            collection_instance["uv_translate"] = (0, 0)

        # convert mesh to blender coordinate system
        m = Matrix(pvs_model_instance.transform)
        m = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))) @ m # Forza->Blender coordinate system
        # collection_instance.matrix_world = m # no shear support
        collection_instance.matrix_parent_inverse = m

        track_layer_collection.collection.objects.link(collection_instance)

    # collection stuff
    track_layer_collection.collection.objects.link(instances_parent)
    instances_parent.hide_set(True)
    track_layer_collection.collection.children.link(master_collection)
    master_layer_collection = next(layer_collection for layer_collection in track_layer_collection.children if layer_collection.collection == master_collection)
    master_layer_collection.exclude = True

def _populate_indexed_textures_from_track(path_textures, save_files: bool = False):
    for i, path_texture in enumerate(path_textures):
        filename = str(path_texture.resolve())
        if not filename.endswith("_B.bix"):
            img = Bix.get_image_from_bix(path_texture.resolve(), save_image=save_files)
            texture_idx = int(convert_texture_name_to_decimal(str(path_texture.stem)))
            indexed_textures[texture_idx] = img
        if (i + 1) % 100 == 0:
            print(f"[{i + 1}/{len(path_textures)}]")
            bpy.context.workspace.status_text_set(f"[{i + 1}/{len(path_textures)}] textures generated")

def _populate_indexed_bin_textures_from_track(path_bin_textures, track_path, path_ribbon: str):
    path_bin: Path = Path(track_path) / "bin" / "textures"
    path_ribbon_pvs: Path = next(Path(path_ribbon).glob("*.pvs"))
    pvs: PVS = PVS.from_stream(BinaryStream.from_path(path_ribbon_pvs.resolve(), ">"))

    known_stx_indexes = set()
    dds_stx = CAFF.get_image_from_bin(next(p for p in path_bin_textures if p.name.endswith(".stx.bin")).resolve())
    for i, pvs_texture in enumerate(pvs.textures):
        file_name = F"_0x{pvs_texture.texture_file_name:08X}"
        path_texture = next((p for p in path_bin_textures if p.name == F"{file_name}.bin"), None)
        if path_texture is not None:
            dds = CAFF.get_image_from_bin(path_texture.resolve())[0]
        else:
            stx_index = pvs_texture.index_in_stx_bin
            if stx_index in known_stx_indexes:
                continue
            known_stx_indexes.add(stx_index)
            file_name = F"_0x{stx_index | 0x80000000:08X}"
            dds = dds_stx[stx_index]

        # save dds as .dds file
        if dds is not None:
            image_filename = F"{file_name}.dds"
            image_filepath = path_bin / image_filename
            with open(image_filepath.resolve(), 'wb') as f: 
                f.write(dds)
        else:
            print("Could not extract texture from .bin")

        if (i + 1) % 100 == 0:
            print(f"[{i + 1}/{len(pvs.textures)}]")
            bpy.context.workspace.status_text_set(f"[{i + 1}/{len(pvs.textures)}] textures generated")

def _add_mesh_to_scene(context, forza_mesh, collection):
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


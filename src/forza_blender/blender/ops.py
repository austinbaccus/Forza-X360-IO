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
    
class FORZA_OT_track_import_modal(Operator):
    bl_idname = "forza.import_track_modal"
    bl_label = "Import Track"
    bl_options = {'REGISTER', 'INTERNAL'}

    def _step(self, context):
        """Do a small chunk of work and return True if more remains."""
        # Example: process 1 item per call
        if self.idx < len(self.items):
            item = self.items[self.idx]
            # ... do work for `item` here ...
            # update status/progress
            context.workspace.status_text_set(f"Processing {self.idx+1}/{len(self.items)}: {item}")
            bpy.context.window_manager.progress_update(self.idx + 1)
            self.idx += 1
            return True
        return False

    def modal(self, context, event):
        if event.type == 'TIMER':
            steps_this_tick = 5
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
        if type(track_path) is not Path: track_path = Path(track_path)
        if type(path_ribbon) is not Path: path_ribbon = Path(path_ribbon)
        path_bin: Path = track_path / "bin"
        path_ribbon_pvs: Path = list(path_ribbon.glob("*.pvs"))[0]

        # Prepare your workload
        meshes: list[ForzaMesh] = _get_meshes_from_track(path_bin, path_ribbon_pvs, context)
        for instance_mesh in meshes:
             _add_mesh_to_scene(context, instance_mesh, path_bin)


        self.items = [f"item_{i}" for i in range(1000)]
        self.idx = 0

        # Progress bar
        bpy.context.window_manager.progress_begin(0, len(self.items))

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
    meshes: list[ForzaMesh] = _get_meshes_from_track(path_bin, path_ribbon_pvs, context)
    i = 0
    for instance_mesh in meshes:
        _add_mesh_to_scene(context, instance_mesh, path_bin)
        i = i + 1
        print(f"[{i}/{len(meshes)}]")
        bpy.context.workspace.status_text_set(f"[{i}/{len(meshes)}] meshes imported")

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


from pathlib import Path
import bpy
from bpy.types import Operator
from bpy.props import StringProperty
 
class FORZA_OT_import(Operator):
    bl_idname = "forza.import"
    bl_label = "Import"
    
    def execute(self, context):
        if context.scene.forza_selection == "FM3":
            import_fm3(context, context.scene.forza_last_folder)
        if context.scene.forza_selection == "FM4":
            import_fm4(context, context.scene.forza_last_folder)

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
    from forza.models.read_rmbbin import RmbBin

    # get paths to important folders and files
    path_bin: Path = track_path / "bin"
    path_shaders: Path = path_bin / "shaders"
    path_ribbon: Path = track_path / "Ribbon_00"
    path_ribbon_pvs: Path = list(path_ribbon.glob("*.pvs"))[0]

    # Amalfi
    # |-- ForzaTrackBin
    # |---|-- ForzaTrackSection
    # |---|---|-- ForzaTrackSubSection
    # |---|---|---|-- ForzaMesh
    # |---|---|---|-- ForzaMesh
    # |---|---|-- ForzaTrackSubSection
    # |---|---|---|-- ForzaMesh
    # |---|---|---|-- ForzaMesh
    # |---|-- ForzaTrackSection
    # |---|---|-- ForzaTrackSubSection
    # |---|---|---|-- ForzaMesh
    # |---|---|---|-- ForzaMesh
    # |---|---|-- ForzaTrackSubSection
    # |---|---|---|-- ForzaMesh
    # |---|---|---|-- ForzaMesh
    # |-- ForzaTrackBin
    # |---|-- ForzaTrackSection
    # |---|---|-- ForzaTrackSubSection
    # |---|---|---|-- ForzaMesh
    # |---|---|---|-- ForzaMesh
    # |---|---|-- ForzaTrackSubSection
    # |---|---|---|-- ForzaMesh
    # |---|---|---|-- ForzaMesh
    # |---|-- ForzaTrackSection
    # |---|---|-- ForzaTrackSubSection
    # |---|---|---|-- ForzaMesh
    # |---|---|---|-- ForzaMesh
    # |---|---|-- ForzaTrackSubSection
    # |---|---|---|-- ForzaMesh
    # |---|---|---|-- ForzaMesh

    track_meshes = []

    # get all .rmb.bin files
    path_trackbins = list(path_ribbon.glob("*.rmb.bin"))

    # foreach .rmb.bin file, create a ForzaTrackBin object
    for path_trackbin in path_trackbins:
        track_bin = RmbBin(path_trackbin.name)
        track_bin.populate_objects_from_rmbbin()

        if track_bin.forza_version.name != context.scene.forza_selection:
            raise ValueError("Forza version mismatch!")
        
        # foreach ForzaTrackBin object, populate the ForzaTrackSection objects

        # foreach ForzaTrackSection objects, populate the ForzaTrackSubSection objects

        # foreach ForzaTrackSunSection objects, populate the ForzaMesh objects

    print(len(track_meshes))

def import_fm4(context, track_path: Path):
    print()
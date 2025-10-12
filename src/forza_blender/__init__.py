bl_info = {
    "name": "Forza",
    "author": "Austin Baccus, Doliman100, Warshack4874, Spencer Leagra",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "3D Viewport > Sidebar (N) > Forza",
    "description": "Adds a panel with a button that prints to the console",
    "category": "3D View",
}

import importlib
import bpy # type: ignore
from bpy.props import EnumProperty, StringProperty, BoolProperty # type: ignore
from forza_blender.blender import ui, ops

def reload(module):
    importlib.reload(module)

def register():
    if not hasattr(bpy.types.Scene, "forza_selection"):
        bpy.types.Scene.forza_selection = EnumProperty(
            name="Forza Mode",
            description="Select which Forza game you are importing",
            items=[
                ('FM3', 'FM3', 'Mode FM3'),
                ('FM4', 'FM4', 'Mode FM4'),
            ],
            default='FM3',
        )
    bpy.types.Scene.use_pregenerated_textures = BoolProperty(
        name="Generate textures",
        description="",
        default=True,
    )
    bpy.types.Scene.generate_mats = BoolProperty(
        name="Generate materials",
        description="",
        default=True,
    )
    bpy.types.Scene.generate_lods = BoolProperty(
        name="Generate LODs",
        description="",
        default=True,
    )

    bpy.types.Scene.forza_last_track_folder = StringProperty(
        name="Selected Track Folder",
        subtype='DIR_PATH',
        default=""
    )

    bpy.types.Scene.forza_last_ribbon_folder = StringProperty(
        name="Selected Ribbon Folder",
        subtype='DIR_PATH',
        default=""
    )

    bpy.types.Scene.forza_last_texture_folder = StringProperty(
        name="Selected Texture Folder",
        subtype='DIR_PATH',
        default=""
    )

    reload(ui); reload(ops)
    ui.register()
    ops.register()

def unregister():
    ui.unregister()
    ops.unregister()
    if hasattr(bpy.types.Scene, "forza_last_track_folder"):
        del bpy.types.Scene.forza_last_track_folder
    if hasattr(bpy.types.Scene, "forza_last_ribbon_folder"):
        del bpy.types.Scene.forza_last_ribbon_folder
    if hasattr(bpy.types.Scene, "forza_last_texture_folder"):
        del bpy.types.Scene.forza_last_texture_folder
    if hasattr(bpy.types.Scene, "forza_selection"):
        del bpy.types.Scene.forza_selection
    if hasattr(bpy.types.Scene, "generate_textures"):
        del bpy.types.Scene.generate_textures
    if hasattr(bpy.types.Scene, "generate_mats"):
        del bpy.types.Scene.generate_mats
    if hasattr(bpy.types.Scene, "generate_lods"):
        del bpy.types.Scene.generate_lods
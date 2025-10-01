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
import bpy
from bpy.props import EnumProperty, StringProperty
from forza_blender.blender import ui, ops

def reload(module):
    importlib.reload(module)

def register():
    if not hasattr(bpy.types.Scene, "forza_selection"):
        bpy.types.Scene.forza_selection = EnumProperty(
            name="Forza Mode",
            description="Select which Forza game you are importing",
            items=[
                ('FM1', 'FM1', 'Mode FM1'),
                ('FM2', 'FM2', 'Mode FM2'),
                ('FM3', 'FM3', 'Mode FM3'),
                ('FM4', 'FM4', 'Mode FM4'),
                ('FM5', 'FM5', 'Mode FM5'),
                ('FM6', 'FM6', 'Mode FM6'),
                ('FM7', 'FM7', 'Mode FM7'),
                ('FM8', 'FM8', 'Mode FM8'),
                ('FH1', 'FH1', 'Mode FH1'),
                ('FH2', 'FH2', 'Mode FH2'),
                ('FH3', 'FH3', 'Mode FH3'),
                ('FH4', 'FH4', 'Mode FH4'),
                ('FH5', 'FH5', 'Mode FH5'),
                ('FH6', 'FH6', 'Mode FH6'),
            ],
            default='FM3',
        )

    bpy.types.Scene.forza_last_folder = StringProperty(
        name="Selected Folder",
        subtype='DIR_PATH',
        default=""
    )

    reload(ui); reload(ops)
    ui.register()
    ops.register()

def unregister():
    ui.unregister()
    ops.unregister()
    if hasattr(bpy.types.Scene, "forza_last_folder"):
        del bpy.types.Scene.forza_last_folder
    if hasattr(bpy.types.Scene, "forza_selection"):
        del bpy.types.Scene.forza_selection
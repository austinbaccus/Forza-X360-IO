import bpy # type: ignore

class FORZA_PT_main(bpy.types.Panel):
    bl_label = "Forza"
    bl_idname = "FORZA_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Forza"

    def draw(self, context):
        layout = self.layout

        # checkboxes
        layout.prop(context.scene, "generate_mats", text="Generate materials")
        layout.prop(context.scene, "generate_lods", text="Generate LODs")

        # forza game picker
        _draw_forza_game_picker(context, layout)

        # forza models
        _draw_track_import_box(context, layout)
        
        # import track button
        is_import_btn_enabled: bool = True
        is_track_folder_null_or_empty = context.scene.forza_last_track_folder is None or context.scene.forza_last_track_folder == ''

        is_import_btn_enabled = not is_track_folder_null_or_empty
            
        _draw_generate_textures_button(context, layout, is_import_btn_enabled)
        _draw_generate_bin_textures_button(context, layout, is_import_btn_enabled)
        _draw_import_button(context, layout, is_import_btn_enabled)

def _draw_forza_game_picker(context, layout):
    layout.separator()
    col = layout.column(align=True)
    col.label(text="Which Forza?")
    enum_items = context.scene.bl_rna.properties["forza_selection"].enum_items
    for item in enum_items:
        col.prop_enum(context.scene, "forza_selection", item.identifier)

def _draw_track_import_box(context, layout):
    layout.separator()
    box_models = layout.box()
    box_models.label(text="Track Folder")
    box_models_row_1 = box_models.row(align=True)
    box_models_row_1.operator("forza.pick_track_folder", icon="FILE_FOLDER")
    folder_track_path = context.scene.forza_last_track_folder
    # track
    if folder_track_path:
        box_models_row_2 = box_models.row()
        box_models_row_2.prop(context.scene, "forza_last_track_folder", text="", emboss=False, icon='FILE_FOLDER')
    else:
        box_models.label(text="No track folder selected", icon='INFO')

    # ribbon
    box_models_row_2 = box_models.row(align=True)
    box_models_row_2.operator("forza.pick_ribbon_folder", icon="FILE_FOLDER")
    
    folder_ribbon_path = context.scene.forza_last_ribbon_folder
    if folder_ribbon_path:
        box_models_row_2 = box_models.row()
        box_models_row_2.prop(context.scene, "forza_last_ribbon_folder", text="", emboss=False, icon='FILE_FOLDER')
    else:
        box_models.label(text="No ribbon folder selected", icon='INFO')

def _draw_generate_textures_button(context, layout, enabled: bool):
    layout.separator()
    import_row = layout.row()
    import_row.operator("forza.generate_textures", icon="CUBE")
    import_row.enabled = enabled

def _draw_generate_bin_textures_button(context, layout, enabled: bool):
    layout.separator()
    import_row = layout.row()
    import_row.operator("forza.generate_bin_textures", icon="CUBE")
    import_row.enabled = enabled

def _draw_import_button(context, layout, enabled: bool):
    layout.separator()
    import_row = layout.row()
    import_row.operator("forza.import_track", icon="CUBE")
    import_row.enabled = enabled

classes = (FORZA_PT_main,)

def register():
    for c in classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes): bpy.utils.unregister_class(c)
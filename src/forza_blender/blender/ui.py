import bpy # type: ignore

class FORZA_PT_main(bpy.types.Panel):
    bl_label = "Forza"
    bl_idname = "FORZA_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Forza"

    def draw(self, context):
        layout = self.layout

        layout.prop(context.scene, "generate_textures", text="Generate textures")
        layout.prop(context.scene, "generate_mats", text="Generate materials")
        layout.prop(context.scene, "generate_lods", text="Generate LODs")

        col = layout.column(align=True)
        col.label(text="Which Forza?")
        enum_items = context.scene.bl_rna.properties["forza_selection"].enum_items
        for item in enum_items:
            col.prop_enum(context.scene, "forza_selection", item.identifier)

        box = layout.box()
        box.label(text="Inputs")
        row = box.row(align=True)
        row.operator("forza.pick_folder", icon="FILE_FOLDER")

        # file path string
        folder_path = context.scene.forza_last_folder
        if folder_path:
            sub = box.row()
            # emboss=False makes it label-like but still selectable; icon works here
            sub.prop(context.scene, "forza_last_folder", text="", emboss=False, icon='FILE_FOLDER')
        else:
            box.label(text="No folder selected", icon='INFO')

        layout.operator("forza.import", icon="CUBE")

        

classes = (FORZA_PT_main,)

def register():
    for c in classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes): bpy.utils.unregister_class(c)
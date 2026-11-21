import math
import bpy # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.shaders.shaders_util import *

# TrackSettings.xml
dark_color = (0, 0, 0)
light_color = (1.93, 1.93, 1.9)
light_curve_white_point = 300.000061
specular = 0 # GlobalSpecularLevel.value
sun_dir = (0.599128, -0.502329, 0.623467) # normalize(-ShadowLightDirection.xzy)
sky_scale = 1.2
sky_gain = 0.11

def generate_blender_compositing(scene: bpy.types.Scene):
    node_tree: bpy.types.CompositorNodeTree = bpy.data.node_groups.new("Compositor Nodes", type="CompositorNodeTree")
    node_tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    nodes = node_tree.nodes
    links = node_tree.links

    render_layers_node: bpy.types.CompositorNodeRLayers = nodes.new("CompositorNodeRLayers")

    # postprocess.fxo, technique FinalCombineBloomTonemap
    tonemap_node: bpy.types.ShaderNodeVectorMath = nodes.new("ShaderNodeVectorMath")
    tonemap_node.operation = "DIVIDE"
    tonemap_node.inputs["Vector_001"].default_value = (light_curve_white_point / 255, light_curve_white_point / 255, light_curve_white_point / 255)
    links.new(render_layers_node.outputs["Image"], tonemap_node.inputs["Vector"])

    # apply_gamma_table.cs.xesl, sRGB to Rec.709 (D3D::GetCurrentGammaTable())
    # sRGB to linear
    to_linear_node: bpy.types.CompositorNodeConvertColorSpace = nodes.new("CompositorNodeConvertColorSpace")
    to_linear_node.from_color_space = "sRGB"
    to_linear_node.to_color_space = "Linear Rec.709"
    links.new(tonemap_node.outputs["Vector"], to_linear_node.inputs["Image"])

    # color < 0.018
    cmp_sub_node: bpy.types.ShaderNodeVectorMath = nodes.new("ShaderNodeVectorMath")
    cmp_sub_node.operation = "SUBTRACT"
    cmp_sub_node.inputs["Vector"].default_value = (0.018, 0.018, 0.018)
    links.new(to_linear_node.outputs["Image"], cmp_sub_node.inputs["Vector_001"])

    cmp_mul_node: bpy.types.ShaderNodeVectorMath = nodes.new("ShaderNodeVectorMath")
    cmp_mul_node.operation = "MULTIPLY"
    cmp_mul_node.inputs["Vector_001"].default_value = (math.inf, math.inf, math.inf)
    links.new(cmp_sub_node.outputs["Vector"], cmp_mul_node.inputs["Vector"])

    # power
    power_node: bpy.types.ShaderNodeVectorMath = nodes.new("ShaderNodeVectorMath")
    power_node.operation = "POWER"
    power_node.inputs["Vector_001"].default_value = (0.45, 0.45, 0.45)
    links.new(to_linear_node.outputs["Image"], power_node.inputs["Vector"])

    power_mul_node: bpy.types.ShaderNodeVectorMath = nodes.new("ShaderNodeVectorMath")
    power_mul_node.operation = "MULTIPLY"
    power_mul_node.inputs["Vector_001"].default_value = (1.099, 1.099, 1.099)
    links.new(power_node.outputs["Vector"], power_mul_node.inputs["Vector"])

    power_sub_node: bpy.types.ShaderNodeVectorMath = nodes.new("ShaderNodeVectorMath")
    power_sub_node.operation = "SUBTRACT"
    power_sub_node.inputs["Vector_001"].default_value = (0.099, 0.099, 0.099)
    links.new(power_mul_node.outputs["Vector"], power_sub_node.inputs["Vector"])

    # linear
    linear_node: bpy.types.ShaderNodeVectorMath = nodes.new("ShaderNodeVectorMath")
    linear_node.operation = "MULTIPLY"
    linear_node.inputs["Vector_001"].default_value = (4.5, 4.5, 4.5)
    links.new(to_linear_node.outputs["Image"], linear_node.inputs["Vector"])

    # linear to Rec.709
    mix_node: bpy.types.ShaderNodeMix = nodes.new("ShaderNodeMix")
    mix_node.data_type = "VECTOR"
    mix_node.factor_mode = "NON_UNIFORM"
    links.new(cmp_mul_node.outputs["Vector"], mix_node.inputs["Factor"])
    links.new(power_sub_node.outputs["Vector"], mix_node.inputs["A"])
    links.new(linear_node.outputs["Vector"], mix_node.inputs["B"])

    # sRGB to Working Space, undo Blender post-processing
    to_scene_node: bpy.types.CompositorNodeConvertColorSpace = nodes.new("CompositorNodeConvertColorSpace")
    to_scene_node.from_color_space = "sRGB"
    links.new(mix_node.outputs["Result"], to_scene_node.inputs["Image"])

    # output
    group_output_node: bpy.types.NodeGroupOutput = nodes.new("NodeGroupOutput")
    links.new(to_scene_node.outputs["Image"], group_output_node.inputs["Socket_0"])

    viewer_node: bpy.types.CompositorNodeViewer = nodes.new("CompositorNodeViewer")
    links.new(to_scene_node.outputs["Image"], viewer_node.inputs["Image"])

    scene.compositing_node_group = node_tree

def generate_blender_materials_for_mesh(forza_mesh: ForzaMesh, track_folder_path):
    materials = []

    if forza_mesh.track_section.subsections[0].material_index == -1:
        return materials

    for sub in forza_mesh.track_section.subsections:
        fx_filename_index = forza_mesh.track_bin.material_sets[0].materials[sub.material_index].fx_filename_index
        shader_filename_simple = (forza_mesh.track_bin.shader_filenames[fx_filename_index].split('\\')[-1]).split('.')[0]
        material_name = F"{sub.name} {shader_filename_simple}"

        args = (forza_mesh, track_folder_path, material_name, sub.material_index)

        func = getattr(Shaders, shader_filename_simple, None)
        if callable(func):
            try:
                materials.append(func(*args))
            except:
                materials.append(bpy.data.materials.new(material_name))
        else:
            try:
                materials.append(Shaders.unknown(forza_mesh, track_folder_path, material_name, sub.material_index))
            except:
                materials.append(bpy.data.materials.new(material_name))
    return materials


class Shaders:
    @staticmethod
    def base(forza_mesh: ForzaMesh, track_folder_path, shader_name: str, material_index: int):
        # create material
        mat = bpy.data.materials.new(shader_name)
        mat.use_nodes = True
        nt = mat.node_tree
        nodes, links = nt.nodes, nt.links

        # nodes
        nodes.clear()
        textures = generate_image_texture_nodes_for_material(forza_mesh, track_folder_path, nodes, links, material_index)

        bsdf = nodes.new("ShaderNodeEmission")

        out = nodes.new("ShaderNodeOutputMaterial")
        links.new(bsdf.outputs["Emission"], out.inputs["Surface"])

        bsdf_wrapper = NodeWrapperShader(bsdf, bsdf.inputs["Color"], bsdf.outputs["Emission"])

        return mat, out, bsdf_wrapper, textures

    @staticmethod
    def unknown(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        t0 = textures[0] if textures else None # Diffuse_Texture
        t7 = textures[7] if len(textures) >= 7 else None # Light_Map

        if t7 is not None:
            uv2_map_node = nodes.new("ShaderNodeUVMap")
            uv2_map_node.uv_map = "TEXCOORD2"

            links.new(uv2_map_node.outputs["UV"], t7.in_uv)

            light_map_remap_node = nodes.new("ShaderNodeMix")
            light_map_remap_node.data_type = "VECTOR"
            light_map_remap_node.factor_mode = "NON_UNIFORM"
            light_map_remap_node.inputs["A"].default_value = dark_color
            light_map_remap_node.inputs["B"].default_value = light_color
            links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

            if t0 is not None:
                light_map_mix_node = nodes.new("ShaderNodeVectorMath")
                light_map_mix_node.operation = "MULTIPLY"
                links.new(t0.out_rgb, light_map_mix_node.inputs["Vector"])
                links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

                links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)
            else:
                links.new(light_map_remap_node.outputs["Result"], bsdf.in_rgb)
        elif t0 is not None:
            links.new(t0.out_rgb, bsdf.in_rgb)

        return mat



#region basic
    @staticmethod
    def clr_0(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, _ = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        diffuse_color_node = nodes.new("ShaderNodeCombineXYZ")
        diffuse_color_node.inputs["X"].default_value = c[0]
        diffuse_color_node.inputs["Y"].default_value = c[1]
        diffuse_color_node.inputs["Z"].default_value = c[2]

        links.new(diffuse_color_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def diff_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)

        # nodes
        diffuse_node = textures[0]
        ambient_occlusion_node = textures[7]
        mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, -150); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -200)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.in_uv)
        mat.node_tree.links.new(diffuse_node.out_rgb, mix_rgb_node.inputs[1])
        mat.node_tree.links.new(ambient_occlusion_node.out_rgb, mix_rgb_node.inputs[2])
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.in_rgb)

        return mat

    @staticmethod
    def diff_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_map_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_map_node.outputs["UV"], t7.in_uv)

        # blend
        t0_mul_node = nodes.new("ShaderNodeVectorMath")
        t0_mul_node.operation = "MULTIPLY"
        t0_mul_node.inputs["Vector_001"].default_value = (c[2], c[2], c[2])
        links.new(t0.out_rgb, t0_mul_node.inputs["Vector"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(t0_mul_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        # BSDF
        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        add_opacity(mat, bsdf, out, t0.out_a)

        return mat

    @staticmethod
    def diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_map_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_map_node.outputs["UV"], t7.in_uv)

        # blend
        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        # BSDF
        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        add_opacity(mat, bsdf, out, t0.out_a)

        return mat

    @staticmethod
    def diff_opac_2_nolm(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        mat.node_tree.links.new(textures[0].out_rgb, bsdf.in_rgb)

        add_opacity(mat, bsdf, out, textures[0].out_a)

        return mat

    @staticmethod
    def diff_opac_clampuv_nolm_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        mat.node_tree.links.new(textures[0].out_rgb, bsdf.in_rgb)

        add_opacity(mat, bsdf, out, textures[0].out_a)

        return mat

    @staticmethod
    def diff_opac_clamp_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        mat.node_tree.links.new(textures[0].out_rgb, bsdf.in_rgb)

        add_opacity(mat, bsdf, out, textures[0].out_a)

        return mat

    @staticmethod
    def diff_spec_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_map_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_map_node.outputs["UV"], t7.in_uv)

        # blend
        t0_mul_node = nodes.new("ShaderNodeVectorMath")
        t0_mul_node.operation = "MULTIPLY"
        t0_mul_node.inputs["Vector_001"].default_value = (c[2], c[2], c[2])
        links.new(t0.out_rgb, t0_mul_node.inputs["Vector"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(t0_mul_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def diff_spec_refl(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.diff_spec_opac_refl_3(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def diff_spec_refl_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t2
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[1], c[2], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[2], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # SPEC
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t2_uv_node = nodes.new("ShaderNodeVectorMath")
        t2_uv_node.operation = "MULTIPLY_ADD"
        t2_uv_node.inputs["Vector_001"].default_value = (c[4], c[5], 0)
        t2_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[5], 0)
        links.new(uv0_node.outputs["UV"], t2_uv_node.inputs["Vector"])

        t2 = textures[2] # Diffuse_Texture
        links.new(t2_uv_node.outputs["Vector"], t2.in_uv)

        # t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # cubemap
        geometry_node = nodes.new("ShaderNodeNewGeometry")

        view_dir_neg_node = nodes.new("ShaderNodeVectorMath")
        view_dir_neg_node.operation = "MULTIPLY"
        view_dir_neg_node.inputs["Vector_001"].default_value = (-1, -1, -1)
        links.new(geometry_node.outputs["Incoming"], view_dir_neg_node.inputs["Vector"])

        reflect_node = nodes.new("ShaderNodeVectorMath")
        reflect_node.operation = "REFLECT"
        links.new(view_dir_neg_node.outputs["Vector"], reflect_node.inputs["Vector"])
        links.new(geometry_node.outputs["Normal"], reflect_node.inputs["Vector_001"])

        # cubemap - in
        cube_vec_separate_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(reflect_node.outputs["Vector"], cube_vec_separate_node.inputs["Vector"])

        cube_vec_abs_node = nodes.new("ShaderNodeVectorMath")
        cube_vec_abs_node.operation = "ABSOLUTE"
        links.new(reflect_node.outputs["Vector"], cube_vec_abs_node.inputs["Vector"])

        cube_vec_abs_separate_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(cube_vec_abs_node.outputs["Vector"], cube_vec_abs_separate_node.inputs["Vector"])

        # cubemap - X
        cube_x_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(cube_vec_separate_node.outputs["Y"], cube_x_combine_node.inputs["X"])
        links.new(cube_vec_separate_node.outputs["Z"], cube_x_combine_node.inputs["Y"])

        cube_x_div_node = nodes.new("ShaderNodeVectorMath")
        cube_x_div_node.operation = "DIVIDE"
        links.new(cube_x_combine_node.outputs["Vector"], cube_x_div_node.inputs["Vector"])
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_x_div_node.inputs["Vector_001"])

        cube_x_p_node = nodes.new("ShaderNodeVectorMath")
        cube_x_p_node.operation = "MULTIPLY_ADD"
        cube_x_p_node.inputs["Vector_001"].default_value = (-0.5, 0.5, 0)
        cube_x_p_node.inputs["Vector_002"].default_value = (0.5, 5.5, 0)
        links.new(cube_x_div_node.outputs["Vector"], cube_x_p_node.inputs["Vector"])

        cube_x_n_node = nodes.new("ShaderNodeVectorMath")
        cube_x_n_node.operation = "MULTIPLY_ADD"
        cube_x_n_node.inputs["Vector_001"].default_value = (0.5, 0.5, 0)
        cube_x_n_node.inputs["Vector_002"].default_value = (0.5, 4.5, 0)
        links.new(cube_x_div_node.outputs["Vector"], cube_x_n_node.inputs["Vector"])

        cube_x_cmp_node = nodes.new("ShaderNodeMath")
        cube_x_cmp_node.operation = "GREATER_THAN"
        cube_x_cmp_node.inputs["Value_001"].default_value = 0
        links.new(cube_vec_separate_node.outputs["X"], cube_x_cmp_node.inputs["Value"])

        cube_x_mix_node = nodes.new("ShaderNodeMix")
        cube_x_mix_node.data_type = "VECTOR"
        links.new(cube_x_cmp_node.outputs["Value"], cube_x_mix_node.inputs["Factor"])
        links.new(cube_x_n_node.outputs["Vector"], cube_x_mix_node.inputs["A"])
        links.new(cube_x_p_node.outputs["Vector"], cube_x_mix_node.inputs["B"])

        # cubemap - Y
        cube_y_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(cube_vec_separate_node.outputs["X"], cube_y_combine_node.inputs["X"])
        links.new(cube_vec_separate_node.outputs["Z"], cube_y_combine_node.inputs["Y"])

        cube_y_div_node = nodes.new("ShaderNodeVectorMath")
        cube_y_div_node.operation = "DIVIDE"
        links.new(cube_y_combine_node.outputs["Vector"], cube_y_div_node.inputs["Vector"])
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_y_div_node.inputs["Vector_001"])

        cube_y_p_node = nodes.new("ShaderNodeVectorMath")
        cube_y_p_node.operation = "MULTIPLY_ADD"
        cube_y_p_node.inputs["Vector_001"].default_value = (0.5, 0.5, 0)
        cube_y_p_node.inputs["Vector_002"].default_value = (0.5, 1.5, 0)
        links.new(cube_y_div_node.outputs["Vector"], cube_y_p_node.inputs["Vector"])

        cube_y_n_node = nodes.new("ShaderNodeVectorMath")
        cube_y_n_node.operation = "MULTIPLY_ADD"
        cube_y_n_node.inputs["Vector_001"].default_value = (-0.5, 0.5, 0)
        cube_y_n_node.inputs["Vector_002"].default_value = (0.5, 0.5, 0)
        links.new(cube_y_div_node.outputs["Vector"], cube_y_n_node.inputs["Vector"])

        cube_y_cmp_node = nodes.new("ShaderNodeMath")
        cube_y_cmp_node.operation = "GREATER_THAN"
        cube_y_cmp_node.inputs["Value_001"].default_value = 0
        links.new(cube_vec_separate_node.outputs["Y"], cube_y_cmp_node.inputs["Value"])

        cube_y_mix_node = nodes.new("ShaderNodeMix")
        cube_y_mix_node.data_type = "VECTOR"
        links.new(cube_y_cmp_node.outputs["Value"], cube_y_mix_node.inputs["Factor"])
        links.new(cube_y_n_node.outputs["Vector"], cube_y_mix_node.inputs["A"])
        links.new(cube_y_p_node.outputs["Vector"], cube_y_mix_node.inputs["B"])

        # cubemap - Z
        cube_z_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(cube_vec_separate_node.outputs["X"], cube_z_combine_node.inputs["X"])
        links.new(cube_vec_separate_node.outputs["Y"], cube_z_combine_node.inputs["Y"])

        cube_z_div_node = nodes.new("ShaderNodeVectorMath")
        cube_z_div_node.operation = "DIVIDE"
        links.new(cube_z_combine_node.outputs["Vector"], cube_z_div_node.inputs["Vector"])
        links.new(cube_vec_abs_separate_node.outputs["Z"], cube_z_div_node.inputs["Vector_001"])

        cube_z_p_node = nodes.new("ShaderNodeVectorMath")
        cube_z_p_node.operation = "MULTIPLY_ADD"
        cube_z_p_node.inputs["Vector_001"].default_value = (0.5, -0.5, 0)
        cube_z_p_node.inputs["Vector_002"].default_value = (0.5, 3.5, 0)
        links.new(cube_z_div_node.outputs["Vector"], cube_z_p_node.inputs["Vector"])

        cube_z_n_node = nodes.new("ShaderNodeVectorMath")
        cube_z_n_node.operation = "MULTIPLY_ADD"
        cube_z_n_node.inputs["Vector_001"].default_value = (0.5, 0.5, 0)
        cube_z_n_node.inputs["Vector_002"].default_value = (0.5, 2.5, 0)
        links.new(cube_z_div_node.outputs["Vector"], cube_z_n_node.inputs["Vector"])

        cube_z_cmp_node = nodes.new("ShaderNodeMath")
        cube_z_cmp_node.operation = "GREATER_THAN"
        cube_z_cmp_node.inputs["Value_001"].default_value = 0
        links.new(cube_vec_separate_node.outputs["Z"], cube_z_cmp_node.inputs["Value"])

        cube_z_mix_node = nodes.new("ShaderNodeMix")
        cube_z_mix_node.data_type = "VECTOR"
        links.new(cube_z_cmp_node.outputs["Value"], cube_z_mix_node.inputs["Factor"])
        links.new(cube_z_n_node.outputs["Vector"], cube_z_mix_node.inputs["A"])
        links.new(cube_z_p_node.outputs["Vector"], cube_z_mix_node.inputs["B"])

        # cubemap - mix
        cube_yx_cmp_node = nodes.new("ShaderNodeMath")
        cube_yx_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_yx_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_yx_cmp_node.inputs["Value_001"])

        cube_yz_cmp_node = nodes.new("ShaderNodeMath")
        cube_yz_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_yz_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["Z"], cube_yz_cmp_node.inputs["Value_001"])

        cube_yx_yz_cmp_node = nodes.new("ShaderNodeMath")
        cube_yx_yz_cmp_node.operation = "MULTIPLY"
        links.new(cube_yx_cmp_node.outputs["Value"], cube_yx_yz_cmp_node.inputs["Value"])
        links.new(cube_yz_cmp_node.outputs["Value"], cube_yx_yz_cmp_node.inputs["Value_001"])

        cube_yz_mix_node = nodes.new("ShaderNodeMix")
        cube_yz_mix_node.data_type = "VECTOR"
        links.new(cube_yx_yz_cmp_node.outputs["Value"], cube_yz_mix_node.inputs["Factor"])
        links.new(cube_z_mix_node.outputs["Result"], cube_yz_mix_node.inputs["A"])
        links.new(cube_y_mix_node.outputs["Result"], cube_yz_mix_node.inputs["B"])

        cube_xy_cmp_node = nodes.new("ShaderNodeMath")
        cube_xy_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_xy_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_xy_cmp_node.inputs["Value_001"])

        cube_xz_cmp_node = nodes.new("ShaderNodeMath")
        cube_xz_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_xz_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["Z"], cube_xz_cmp_node.inputs["Value_001"])

        cube_xy_xz_cmp_node = nodes.new("ShaderNodeMath")
        cube_xy_xz_cmp_node.operation = "MULTIPLY"
        links.new(cube_xy_cmp_node.outputs["Value"], cube_xy_xz_cmp_node.inputs["Value"])
        links.new(cube_xz_cmp_node.outputs["Value"], cube_xy_xz_cmp_node.inputs["Value_001"])

        cube_mix_node = nodes.new("ShaderNodeMix")
        cube_mix_node.data_type = "VECTOR"
        links.new(cube_xy_xz_cmp_node.outputs["Value"], cube_mix_node.inputs["Factor"])
        links.new(cube_yz_mix_node.outputs["Result"], cube_mix_node.inputs["A"])
        links.new(cube_x_mix_node.outputs["Result"], cube_mix_node.inputs["B"])

        cube_node = nodes.new("ShaderNodeVectorMath")
        cube_node.operation = "DIVIDE"
        cube_node.inputs["Vector_001"].default_value = (1, 6, 1)
        links.new(cube_mix_node.outputs["Result"], cube_node.inputs["Vector"])

        t1 = textures[1] # Cube_Map
        t1.nodes[0].extension = "CLIP"
        links.new(cube_node.outputs["Vector"], t1.in_uv)

        refl_map_mul_node = nodes.new("ShaderNodeMath")
        refl_map_mul_node.operation = "MULTIPLY"
        refl_map_mul_node.inputs["Value_001"].default_value = c[0]
        links.new(t0.out_a, refl_map_mul_node.inputs["Value"])

        cube_mad_node = nodes.new("ShaderNodeVectorMath")
        cube_mad_node.operation = "MULTIPLY_ADD"
        links.new(t1.out_rgb, cube_mad_node.inputs["Vector"])
        links.new(refl_map_mul_node.outputs["Value"], cube_mad_node.inputs["Vector_001"])
        links.new(t2.out_rgb, cube_mad_node.inputs["Vector_002"])

        # blend
        t2_mul_node = nodes.new("ShaderNodeVectorMath")
        t2_mul_node.operation = "MULTIPLY"
        t2_mul_node.inputs["Vector_001"].default_value = (c[3], c[3], c[3])
        links.new(cube_mad_node.outputs["Vector"], t2_mul_node.inputs["Vector"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(t2_mul_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        # BSDF
        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def diff_spec_refl_norm_4(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        roughness_node = textures[0]
        diffuse_node = textures[2]
        ambient_occlusion_node = textures[7]

        # post-processing nodes
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.location = (-300, -700); uv_map_node.uv_map = "TEXCOORD2"

        # link
        links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.in_uv)
        links.new(diffuse_node.out_rgb, mix_rgb_node.inputs[1])
        links.new(ambient_occlusion_node.out_rgb, mix_rgb_node.inputs[2])
        links.new(mix_rgb_node.outputs[0], bsdf.in_rgb)
        # links.new(roughness_node.out_rgb, bsdf.inputs[2])

        return mat

    @staticmethod
    def diff_spec_opac_refl_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t2
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[1], c[2], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[2], 0)
        links.new(uv0_map_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # SPEC
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t2_uv_node = nodes.new("ShaderNodeVectorMath")
        t2_uv_node.operation = "MULTIPLY_ADD"
        t2_uv_node.inputs["Vector_001"].default_value = (c[4], c[5], 0)
        t2_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[5], 0)
        links.new(uv0_map_node.outputs["UV"], t2_uv_node.inputs["Vector"])

        t2 = textures[2] # Diffuse_Texture
        links.new(t2_uv_node.outputs["Vector"], t2.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_map_node.outputs["UV"], t7.in_uv)

        # cubemap
        geometry_node = nodes.new("ShaderNodeNewGeometry")

        view_dir_neg_node = nodes.new("ShaderNodeVectorMath")
        view_dir_neg_node.operation = "MULTIPLY"
        view_dir_neg_node.inputs["Vector_001"].default_value = (-1, -1, -1)
        links.new(geometry_node.outputs["Incoming"], view_dir_neg_node.inputs["Vector"])

        reflect_node = nodes.new("ShaderNodeVectorMath")
        reflect_node.operation = "REFLECT"
        links.new(view_dir_neg_node.outputs["Vector"], reflect_node.inputs["Vector"])
        links.new(geometry_node.outputs["Normal"], reflect_node.inputs["Vector_001"])

        # cubemap - in
        cube_vec_separate_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(reflect_node.outputs["Vector"], cube_vec_separate_node.inputs["Vector"])

        cube_vec_abs_node = nodes.new("ShaderNodeVectorMath")
        cube_vec_abs_node.operation = "ABSOLUTE"
        links.new(reflect_node.outputs["Vector"], cube_vec_abs_node.inputs["Vector"])

        cube_vec_abs_separate_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(cube_vec_abs_node.outputs["Vector"], cube_vec_abs_separate_node.inputs["Vector"])

        # cubemap - X
        cube_x_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(cube_vec_separate_node.outputs["Y"], cube_x_combine_node.inputs["X"])
        links.new(cube_vec_separate_node.outputs["Z"], cube_x_combine_node.inputs["Y"])

        cube_x_div_node = nodes.new("ShaderNodeVectorMath")
        cube_x_div_node.operation = "DIVIDE"
        links.new(cube_x_combine_node.outputs["Vector"], cube_x_div_node.inputs["Vector"])
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_x_div_node.inputs["Vector_001"])

        cube_x_p_node = nodes.new("ShaderNodeVectorMath")
        cube_x_p_node.operation = "MULTIPLY_ADD"
        cube_x_p_node.inputs["Vector_001"].default_value = (-0.5, 0.5, 0)
        cube_x_p_node.inputs["Vector_002"].default_value = (0.5, 5.5, 0)
        links.new(cube_x_div_node.outputs["Vector"], cube_x_p_node.inputs["Vector"])

        cube_x_n_node = nodes.new("ShaderNodeVectorMath")
        cube_x_n_node.operation = "MULTIPLY_ADD"
        cube_x_n_node.inputs["Vector_001"].default_value = (0.5, 0.5, 0)
        cube_x_n_node.inputs["Vector_002"].default_value = (0.5, 4.5, 0)
        links.new(cube_x_div_node.outputs["Vector"], cube_x_n_node.inputs["Vector"])

        cube_x_cmp_node = nodes.new("ShaderNodeMath")
        cube_x_cmp_node.operation = "GREATER_THAN"
        cube_x_cmp_node.inputs["Value_001"].default_value = 0
        links.new(cube_vec_separate_node.outputs["X"], cube_x_cmp_node.inputs["Value"])

        cube_x_mix_node = nodes.new("ShaderNodeMix")
        cube_x_mix_node.data_type = "VECTOR"
        links.new(cube_x_cmp_node.outputs["Value"], cube_x_mix_node.inputs["Factor"])
        links.new(cube_x_n_node.outputs["Vector"], cube_x_mix_node.inputs["A"])
        links.new(cube_x_p_node.outputs["Vector"], cube_x_mix_node.inputs["B"])

        # cubemap - Y
        cube_y_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(cube_vec_separate_node.outputs["X"], cube_y_combine_node.inputs["X"])
        links.new(cube_vec_separate_node.outputs["Z"], cube_y_combine_node.inputs["Y"])

        cube_y_div_node = nodes.new("ShaderNodeVectorMath")
        cube_y_div_node.operation = "DIVIDE"
        links.new(cube_y_combine_node.outputs["Vector"], cube_y_div_node.inputs["Vector"])
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_y_div_node.inputs["Vector_001"])

        cube_y_p_node = nodes.new("ShaderNodeVectorMath")
        cube_y_p_node.operation = "MULTIPLY_ADD"
        cube_y_p_node.inputs["Vector_001"].default_value = (0.5, 0.5, 0)
        cube_y_p_node.inputs["Vector_002"].default_value = (0.5, 1.5, 0)
        links.new(cube_y_div_node.outputs["Vector"], cube_y_p_node.inputs["Vector"])

        cube_y_n_node = nodes.new("ShaderNodeVectorMath")
        cube_y_n_node.operation = "MULTIPLY_ADD"
        cube_y_n_node.inputs["Vector_001"].default_value = (-0.5, 0.5, 0)
        cube_y_n_node.inputs["Vector_002"].default_value = (0.5, 0.5, 0)
        links.new(cube_y_div_node.outputs["Vector"], cube_y_n_node.inputs["Vector"])

        cube_y_cmp_node = nodes.new("ShaderNodeMath")
        cube_y_cmp_node.operation = "GREATER_THAN"
        cube_y_cmp_node.inputs["Value_001"].default_value = 0
        links.new(cube_vec_separate_node.outputs["Y"], cube_y_cmp_node.inputs["Value"])

        cube_y_mix_node = nodes.new("ShaderNodeMix")
        cube_y_mix_node.data_type = "VECTOR"
        links.new(cube_y_cmp_node.outputs["Value"], cube_y_mix_node.inputs["Factor"])
        links.new(cube_y_n_node.outputs["Vector"], cube_y_mix_node.inputs["A"])
        links.new(cube_y_p_node.outputs["Vector"], cube_y_mix_node.inputs["B"])

        # cubemap - Z
        cube_z_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(cube_vec_separate_node.outputs["X"], cube_z_combine_node.inputs["X"])
        links.new(cube_vec_separate_node.outputs["Y"], cube_z_combine_node.inputs["Y"])

        cube_z_div_node = nodes.new("ShaderNodeVectorMath")
        cube_z_div_node.operation = "DIVIDE"
        links.new(cube_z_combine_node.outputs["Vector"], cube_z_div_node.inputs["Vector"])
        links.new(cube_vec_abs_separate_node.outputs["Z"], cube_z_div_node.inputs["Vector_001"])

        cube_z_p_node = nodes.new("ShaderNodeVectorMath")
        cube_z_p_node.operation = "MULTIPLY_ADD"
        cube_z_p_node.inputs["Vector_001"].default_value = (0.5, -0.5, 0)
        cube_z_p_node.inputs["Vector_002"].default_value = (0.5, 3.5, 0)
        links.new(cube_z_div_node.outputs["Vector"], cube_z_p_node.inputs["Vector"])

        cube_z_n_node = nodes.new("ShaderNodeVectorMath")
        cube_z_n_node.operation = "MULTIPLY_ADD"
        cube_z_n_node.inputs["Vector_001"].default_value = (0.5, 0.5, 0)
        cube_z_n_node.inputs["Vector_002"].default_value = (0.5, 2.5, 0)
        links.new(cube_z_div_node.outputs["Vector"], cube_z_n_node.inputs["Vector"])

        cube_z_cmp_node = nodes.new("ShaderNodeMath")
        cube_z_cmp_node.operation = "GREATER_THAN"
        cube_z_cmp_node.inputs["Value_001"].default_value = 0
        links.new(cube_vec_separate_node.outputs["Z"], cube_z_cmp_node.inputs["Value"])

        cube_z_mix_node = nodes.new("ShaderNodeMix")
        cube_z_mix_node.data_type = "VECTOR"
        links.new(cube_z_cmp_node.outputs["Value"], cube_z_mix_node.inputs["Factor"])
        links.new(cube_z_n_node.outputs["Vector"], cube_z_mix_node.inputs["A"])
        links.new(cube_z_p_node.outputs["Vector"], cube_z_mix_node.inputs["B"])

        # cubemap - mix
        cube_yx_cmp_node = nodes.new("ShaderNodeMath")
        cube_yx_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_yx_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_yx_cmp_node.inputs["Value_001"])

        cube_yz_cmp_node = nodes.new("ShaderNodeMath")
        cube_yz_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_yz_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["Z"], cube_yz_cmp_node.inputs["Value_001"])

        cube_yx_yz_cmp_node = nodes.new("ShaderNodeMath")
        cube_yx_yz_cmp_node.operation = "MULTIPLY"
        links.new(cube_yx_cmp_node.outputs["Value"], cube_yx_yz_cmp_node.inputs["Value"])
        links.new(cube_yz_cmp_node.outputs["Value"], cube_yx_yz_cmp_node.inputs["Value_001"])

        cube_yz_mix_node = nodes.new("ShaderNodeMix")
        cube_yz_mix_node.data_type = "VECTOR"
        links.new(cube_yx_yz_cmp_node.outputs["Value"], cube_yz_mix_node.inputs["Factor"])
        links.new(cube_z_mix_node.outputs["Result"], cube_yz_mix_node.inputs["A"])
        links.new(cube_y_mix_node.outputs["Result"], cube_yz_mix_node.inputs["B"])

        cube_xy_cmp_node = nodes.new("ShaderNodeMath")
        cube_xy_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_xy_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_xy_cmp_node.inputs["Value_001"])

        cube_xz_cmp_node = nodes.new("ShaderNodeMath")
        cube_xz_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_xz_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["Z"], cube_xz_cmp_node.inputs["Value_001"])

        cube_xy_xz_cmp_node = nodes.new("ShaderNodeMath")
        cube_xy_xz_cmp_node.operation = "MULTIPLY"
        links.new(cube_xy_cmp_node.outputs["Value"], cube_xy_xz_cmp_node.inputs["Value"])
        links.new(cube_xz_cmp_node.outputs["Value"], cube_xy_xz_cmp_node.inputs["Value_001"])

        cube_mix_node = nodes.new("ShaderNodeMix")
        cube_mix_node.data_type = "VECTOR"
        links.new(cube_xy_xz_cmp_node.outputs["Value"], cube_mix_node.inputs["Factor"])
        links.new(cube_yz_mix_node.outputs["Result"], cube_mix_node.inputs["A"])
        links.new(cube_x_mix_node.outputs["Result"], cube_mix_node.inputs["B"])

        cube_node = nodes.new("ShaderNodeVectorMath")
        cube_node.operation = "DIVIDE"
        cube_node.inputs["Vector_001"].default_value = (1, 6, 1)
        links.new(cube_mix_node.outputs["Result"], cube_node.inputs["Vector"])

        t1 = textures[1] # Cube_Map
        t1.nodes[0].extension = "CLIP"
        links.new(cube_node.outputs["Vector"], t1.in_uv)

        refl_map_mul_node = nodes.new("ShaderNodeMath")
        refl_map_mul_node.operation = "MULTIPLY"
        refl_map_mul_node.inputs["Value_001"].default_value = c[0]
        links.new(t0.out_a, refl_map_mul_node.inputs["Value"])

        cube_mad_node = nodes.new("ShaderNodeVectorMath")
        cube_mad_node.operation = "MULTIPLY_ADD"
        links.new(t1.out_rgb, cube_mad_node.inputs["Vector"])
        links.new(refl_map_mul_node.outputs["Value"], cube_mad_node.inputs["Vector_001"])
        links.new(t2.out_rgb, cube_mad_node.inputs["Vector_002"])

        # blend
        t2_mul_node = nodes.new("ShaderNodeVectorMath")
        t2_mul_node.operation = "MULTIPLY"
        t2_mul_node.inputs["Vector_001"].default_value = (c[3], c[3], c[3])
        links.new(cube_mad_node.outputs["Vector"], t2_mul_node.inputs["Vector"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(t2_mul_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        transparency_remap_node = nodes.new("ShaderNodeMix")
        transparency_remap_node.inputs["A"].default_value = c[6]
        transparency_remap_node.inputs["B"].default_value = 1
        links.new(t2.out_a, transparency_remap_node.inputs["Factor"])

        # BSDF
        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        add_opacity(mat, bsdf, out, transparency_remap_node.outputs["Result"])

        return mat

    @staticmethod
    def diff_spec_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t1
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[4], c[5], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[5], 0)
        links.new(uv0_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # SPEC
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        # t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # blend
        t0_mul_node = nodes.new("ShaderNodeVectorMath")
        t0_mul_node.operation = "MULTIPLY"
        t0_mul_node.inputs["Vector_001"].default_value = (c[2], c[2], c[2])
        links.new(t0.out_rgb, t0_mul_node.inputs["Vector"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(t0_mul_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        # specular
        geometry_node = nodes.new("ShaderNodeNewGeometry")

        halfway_dir_node = nodes.new("ShaderNodeVectorMath")
        halfway_dir_node.operation = "ADD"
        halfway_dir_node.inputs["Vector_001"].default_value = sun_dir
        links.new(geometry_node.outputs["Incoming"], halfway_dir_node.inputs["Vector"])

        halfway_dir_norm_node = nodes.new("ShaderNodeVectorMath")
        halfway_dir_norm_node.operation = "NORMALIZE"
        links.new(halfway_dir_node.outputs["Vector"], halfway_dir_norm_node.inputs["Vector"])

        noh_node = nodes.new("ShaderNodeVectorMath")
        noh_node.operation = "DOT_PRODUCT"
        links.new(geometry_node.outputs["Normal"], noh_node.inputs["Vector"])
        links.new(halfway_dir_norm_node.outputs["Vector"], noh_node.inputs["Vector_001"])

        noh_clamp_node = nodes.new("ShaderNodeClamp")
        links.new(noh_node.outputs["Value"], noh_clamp_node.inputs["Value"])

        spec_node = nodes.new("ShaderNodeMath")
        spec_node.operation = "POWER"
        spec_node.inputs["Value_001"].default_value = c[6]
        links.new(noh_clamp_node.outputs["Result"], spec_node.inputs["Value"])

        t7_sep_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(t7.out_rgb, t7_sep_node.inputs["Vector"])

        t1_sep_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(t1.out_rgb, t1_sep_node.inputs["Vector"])

        spec_fac_mul_node = nodes.new("ShaderNodeMath")
        spec_fac_mul_node.operation = "MULTIPLY"
        links.new(t7_sep_node.outputs["X"], spec_fac_mul_node.inputs["Value"])
        links.new(t1_sep_node.outputs["X"], spec_fac_mul_node.inputs["Value_001"])

        spec_fac_mul2_node = nodes.new("ShaderNodeMath")
        spec_fac_mul2_node.operation = "MULTIPLY"
        spec_fac_mul2_node.inputs["Value_001"].default_value = c[3]
        links.new(spec_fac_mul_node.outputs["Value"], spec_fac_mul2_node.inputs["Value"])

        spec_fac_node = nodes.new("ShaderNodeMath")
        spec_fac_node.operation = "MAXIMUM"
        spec_fac_node.inputs["Value_001"].default_value = 0
        links.new(spec_fac_mul2_node.outputs["Value"], spec_fac_node.inputs["Value"])

        spec_mul_node = nodes.new("ShaderNodeMath")
        spec_mul_node.operation = "MULTIPLY"
        links.new(spec_node.outputs["Value"], spec_mul_node.inputs["Value"])
        links.new(spec_fac_node.outputs["Value"], spec_mul_node.inputs["Value_001"])

        spec_mul2_node = nodes.new("ShaderNodeMath")
        spec_mul2_node.operation = "MULTIPLY"
        spec_mul2_node.inputs["Value_001"].default_value = specular
        links.new(spec_mul_node.outputs["Value"], spec_mul2_node.inputs["Value"])

        color2_node = nodes.new("ShaderNodeVectorMath")
        color2_node.operation = "ADD"
        links.new(light_map_mix_node.outputs["Vector"], color2_node.inputs["Vector"])
        links.new(spec_mul2_node.outputs["Value"], color2_node.inputs["Vector_001"])

        # BSDF
        links.new(color2_node.outputs["Vector"], bsdf.in_rgb)

        add_opacity(mat, bsdf, out, t0.out_a)

        return mat

    @staticmethod
    def diff_spec_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def diff_spec_vert_nolm_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # blend
        color_attribute_node = nodes.new("ShaderNodeVertexColor")
        color_attribute_node.layer_name = "COLOR0"

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(color_attribute_node.outputs["Color"], light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        # BSDF
        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def diff_clr_opac_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t1
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_map_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t1 = textures[1] # Paint_Mask
        links.new(uv0_map_node.outputs["UV"], t1.in_uv)

        # t2
        model_data_attribute = nodes.new("ShaderNodeAttribute")
        model_data_attribute.attribute_type = "INSTANCER"
        model_data_attribute.attribute_name = "model_data"

        t2_u_node = nodes.new("ShaderNodeMath")
        t2_u_node.operation = "DIVIDE"
        t2_u_node.inputs["Value_001"].default_value = 32
        links.new(model_data_attribute.outputs["Fac"], t2_u_node.inputs["Value"])

        t2_uv_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(t2_u_node.outputs["Value"], t2_uv_node.inputs["X"])

        t2 = textures[2] # Palette
        t2.nodes[0].interpolation = "Closest"
        t2.nodes[0].extension = "CLIP"
        links.new(t2_uv_node.outputs["Vector"], t2.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_map_node.outputs["UV"], t7.in_uv)

        # blend
        palette_mix_node = nodes.new("ShaderNodeMix")
        palette_mix_node.data_type = "VECTOR"
        links.new(t1.out_rgb, palette_mix_node.inputs["Factor"])
        links.new(t0.out_rgb, palette_mix_node.inputs["A"])
        links.new(t2.out_rgb, palette_mix_node.inputs["B"])

        palette_mul_node = nodes.new("ShaderNodeVectorMath")
        palette_mul_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, palette_mul_node.inputs["Vector"])
        links.new(palette_mix_node.outputs["Result"], palette_mul_node.inputs["Vector_001"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(palette_mul_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        transparency_remap_node = nodes.new("ShaderNodeMath")
        transparency_remap_node.operation = "MULTIPLY"
        transparency_remap_node.inputs["Value_001"].default_value = c[2]
        links.new(t0.out_a, transparency_remap_node.inputs["Value"])

        # BSDF
        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        add_opacity(mat, bsdf, out, transparency_remap_node.outputs["Value"])

        return mat

    @staticmethod
    def diff_clr_spec_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t1
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_map_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t1 = textures[1] # Paint_Mask
        links.new(uv0_map_node.outputs["UV"], t1.in_uv)

        # t2
        model_data_attribute = nodes.new("ShaderNodeAttribute")
        model_data_attribute.attribute_type = "INSTANCER"
        model_data_attribute.attribute_name = "model_data"

        t2_u_node = nodes.new("ShaderNodeMath")
        t2_u_node.operation = "DIVIDE"
        t2_u_node.inputs["Value_001"].default_value = 32
        links.new(model_data_attribute.outputs["Fac"], t2_u_node.inputs["Value"])

        t2_uv_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(t2_u_node.outputs["Value"], t2_uv_node.inputs["X"])

        t2 = textures[2] # Palette
        t2.nodes[0].interpolation = "Closest"
        t2.nodes[0].extension = "CLIP"
        links.new(t2_uv_node.outputs["Vector"], t2.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_map_node.outputs["UV"], t7.in_uv)

        # blend
        t0_mul_node = nodes.new("ShaderNodeVectorMath")
        t0_mul_node.operation = "MULTIPLY"
        t0_mul_node.inputs["Vector_001"].default_value = (c[2], c[2], c[2])
        links.new(t0.out_rgb, t0_mul_node.inputs["Vector"])

        palette_mix_node = nodes.new("ShaderNodeMix")
        palette_mix_node.data_type = "VECTOR"
        links.new(t1.out_rgb, palette_mix_node.inputs["Factor"])
        links.new(t0.out_rgb, palette_mix_node.inputs["A"])
        links.new(t2.out_rgb, palette_mix_node.inputs["B"])

        palette_mul_node = nodes.new("ShaderNodeVectorMath")
        palette_mul_node.operation = "MULTIPLY"
        links.new(t0_mul_node.outputs["Vector"], palette_mul_node.inputs["Vector"])
        links.new(palette_mix_node.outputs["Result"], palette_mul_node.inputs["Vector_001"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(palette_mul_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def diff_clr_spec_opac_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.diff_clr_opac_3(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def chain_diff_spec_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)

        # nodes
        diffuse_node = textures[0]
        ambient_occlusion_node = textures[7]
        mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.in_uv)
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.in_rgb)
        mat.node_tree.links.new(diffuse_node.out_rgb, mix_rgb_node.inputs[1])
        mat.node_tree.links.new(ambient_occlusion_node.out_rgb, mix_rgb_node.inputs[2])

        add_opacity(mat, bsdf, out, diffuse_node.out_a)

        return mat

    @staticmethod
    def chain_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)

        # nodes
        diffuse_node = textures[0]
        ambient_occlusion_node = textures[7]
        mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.in_uv)
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.in_rgb)
        mat.node_tree.links.new(diffuse_node.out_rgb, mix_rgb_node.inputs[1])
        mat.node_tree.links.new(ambient_occlusion_node.out_rgb, mix_rgb_node.inputs[2])

        add_opacity(mat, bsdf, out, diffuse_node.out_a)

        return mat

    @staticmethod
    def anim_diff_filmstripuv_glow_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (1 / c[3], 1 / c[5], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - 1 / c[5], 0)
        links.new(uv0_map_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_map_node.outputs["UV"], t7.in_uv)

        # blend
        glow_remap_node = nodes.new("ShaderNodeMath")
        glow_remap_node.operation = "MULTIPLY_ADD"
        glow_remap_node.inputs["Value_001"].default_value = c[0]
        glow_remap_node.inputs["Value_002"].default_value = 1
        links.new(t0.out_a, glow_remap_node.inputs["Value"])

        glow_mix_node = nodes.new("ShaderNodeVectorMath")
        glow_mix_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, glow_mix_node.inputs["Vector"])
        links.new(glow_remap_node.outputs["Value"], glow_mix_node.inputs["Vector_001"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(glow_mix_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def sky_diff_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        t0.nodes[0].extension = "CLIP"
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # blend
        factor_madd_node = nodes.new("ShaderNodeMath")
        factor_madd_node.operation = "MULTIPLY_ADD"
        factor_madd_node.inputs["Value_001"].default_value = sky_gain
        factor_madd_node.inputs["Value_002"].default_value = sky_scale
        links.new(t0.out_a, factor_madd_node.inputs["Value"])

        diff_map_node = nodes.new("ShaderNodeVectorMath")
        diff_map_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, diff_map_node.inputs["Vector"])
        links.new(factor_madd_node.outputs["Value"], diff_map_node.inputs["Vector_001"])

        links.new(diff_map_node.outputs["Vector"], bsdf.in_rgb)

        return mat
#endregion

#region ocean
    @staticmethod
    def ocean_anim_norm_refl_5(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        vs_c = forza_mesh.track_bin.material_sets[0].materials[material_index].vertex_shader_constants
        ps_c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t1_a_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_a_uv_node.operation = "MULTIPLY_ADD"
        t1_a_uv_node.inputs["Vector_001"].default_value = (vs_c[19], vs_c[19], 0)
        t1_a_uv_node.inputs["Vector_002"].default_value = (0, 1 - vs_c[19], 0)
        links.new(uv0_node.outputs["UV"], t1_a_uv_node.inputs["Vector"])

        t1_a = textures[1] # NormalMapA
        t1_a_node = t1_a.nodes[0]
        links.new(t1_a_uv_node.outputs["Vector"], t1_a.in_uv)

        t1_b_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_b_uv_node.operation = "MULTIPLY_ADD"
        t1_b_uv_node.inputs["Vector_001"].default_value = (vs_c[23], vs_c[23], 0)
        t1_b_uv_node.inputs["Vector_002"].default_value = (0, 1 - vs_c[23], 0)
        links.new(uv0_node.outputs["UV"], t1_b_uv_node.inputs["Vector"])

        t1_a_mad_node = nodes.new("ShaderNodeVectorMath")
        t1_a_mad_node.operation = "MULTIPLY_ADD"
        t1_a_mad_node.inputs["Vector_001"].default_value = (2, 2, 0)
        t1_a_mad_node.inputs["Vector_002"].default_value = (-1, -1, 0)
        links.new(t1_a.out_rgb, t1_a_mad_node.inputs["Vector"])

        t1_b_node = nodes.new("ShaderNodeTexImage") # NormalMapA
        t1_b_node.label = F"{t1_a_node.label} copy"
        t1_b_node.image = t1_a_node.image
        links.new(t1_b_uv_node.outputs["Vector"], t1_b_node.inputs["Vector"])

        t1_b_mad_node = nodes.new("ShaderNodeVectorMath")
        t1_b_mad_node.operation = "MULTIPLY_ADD"
        t1_b_mad_node.inputs["Vector_001"].default_value = (2, 2, 0)
        t1_b_mad_node.inputs["Vector_002"].default_value = (-1, -1, 0)
        links.new(t1_b_node.outputs["Color"], t1_b_mad_node.inputs["Vector"])

        # blend
        add_a_b_node = nodes.new("ShaderNodeVectorMath")
        add_a_b_node.operation = "ADD"
        links.new(t1_a_mad_node.outputs["Vector"], add_a_b_node.inputs["Vector"])
        links.new(t1_b_mad_node.outputs["Vector"], add_a_b_node.inputs["Vector_001"])

        mul_a_b_node = nodes.new("ShaderNodeVectorMath")
        mul_a_b_node.operation = "MULTIPLY"
        mul_a_b_node.inputs["Vector_001"].default_value = (0.5, 0.5, 0)
        links.new(add_a_b_node.outputs["Vector"], mul_a_b_node.inputs["Vector"])

        # normal Z
        norm_z_dot_node = nodes.new("ShaderNodeVectorMath")
        norm_z_dot_node.operation = "DOT_PRODUCT"
        links.new(mul_a_b_node.outputs["Vector"], norm_z_dot_node.inputs["Vector"])
        links.new(mul_a_b_node.outputs["Vector"], norm_z_dot_node.inputs["Vector_001"])

        norm_z_sub_node = nodes.new("ShaderNodeMath")
        norm_z_sub_node.operation = "SUBTRACT"
        norm_z_sub_node.inputs["Value"].default_value = 1
        links.new(norm_z_dot_node.outputs["Value"], norm_z_sub_node.inputs["Value_001"])

        norm_z_abs_node = nodes.new("ShaderNodeMath")
        norm_z_abs_node.operation = "ABSOLUTE"
        links.new(norm_z_sub_node.outputs["Value"], norm_z_abs_node.inputs["Value"])

        norm_z_node = nodes.new("ShaderNodeMath")
        norm_z_node.operation = "SQRT"
        links.new(norm_z_abs_node.outputs["Value"], norm_z_node.inputs["Value"])

        # face space normal
        norm_xy_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(mul_a_b_node.outputs["Vector"], norm_xy_node.inputs["Vector"])

        norm_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(norm_xy_node.outputs["X"], norm_combine_node.inputs["X"])
        links.new(norm_xy_node.outputs["Y"], norm_combine_node.inputs["Y"])
        links.new(norm_z_node.outputs["Value"], norm_combine_node.inputs["Z"])

        norm_mul_node = nodes.new("ShaderNodeVectorMath")
        norm_mul_node.operation = "MULTIPLY"
        norm_mul_node.inputs["Vector_001"].default_value = (vs_c[16], vs_c[16], 1)
        links.new(norm_combine_node.outputs["Vector"], norm_mul_node.inputs["Vector"])

        norm_node = nodes.new("ShaderNodeVectorMath")
        norm_node.operation = "NORMALIZE"
        links.new(norm_mul_node.outputs["Vector"], norm_node.inputs["Vector"])

        norm_separate_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(norm_node.outputs["Vector"], norm_separate_node.inputs["Vector"])

        # tangent
        tangent_attr_node = nodes.new("ShaderNodeAttribute")
        tangent_attr_node.attribute_name = "BINORMAL0"

        tangent_tr_node = nodes.new("ShaderNodeVectorTransform")
        tangent_tr_node.convert_from = "OBJECT"
        tangent_tr_node.convert_to = "WORLD"
        links.new(tangent_attr_node.outputs["Vector"], tangent_tr_node.inputs["Vector"])

        # bitangent
        bitangent_attr_node = nodes.new("ShaderNodeAttribute")
        bitangent_attr_node.attribute_name = "TANGENT0"

        bitangent_node = nodes.new("ShaderNodeVectorMath")
        bitangent_node.operation = "MULTIPLY"
        bitangent_node.inputs["Vector_001"].default_value = (-1, -1, -1)
        links.new(bitangent_attr_node.outputs["Vector"], bitangent_node.inputs["Vector"])

        bitangent_tr_node = nodes.new("ShaderNodeVectorTransform")
        bitangent_tr_node.convert_from = "OBJECT"
        bitangent_tr_node.convert_to = "WORLD"
        links.new(bitangent_node.outputs["Vector"], bitangent_tr_node.inputs["Vector"])

        # normal
        normal_tr_node = nodes.new("ShaderNodeVectorTransform")
        normal_tr_node.convert_from = "OBJECT"
        normal_tr_node.convert_to = "WORLD"
        normal_tr_node.inputs["Vector"].default_value = (0, 1, 0)

        # world space normal
        normal_w_n_node = nodes.new("ShaderNodeVectorMath")
        normal_w_n_node.operation = "MULTIPLY"
        links.new(normal_tr_node.outputs["Vector"], normal_w_n_node.inputs["Vector"])
        links.new(norm_separate_node.outputs["Z"], normal_w_n_node.inputs["Vector_001"])

        normal_w_t_node = nodes.new("ShaderNodeVectorMath")
        normal_w_t_node.operation = "MULTIPLY_ADD"
        links.new(bitangent_tr_node.outputs["Vector"], normal_w_t_node.inputs["Vector"])
        links.new(norm_separate_node.outputs["Y"], normal_w_t_node.inputs["Vector_001"])
        links.new(normal_w_n_node.outputs["Vector"], normal_w_t_node.inputs["Vector_002"])

        normal_w_b_node = nodes.new("ShaderNodeVectorMath")
        normal_w_b_node.operation = "MULTIPLY_ADD"
        links.new(tangent_tr_node.outputs["Vector"], normal_w_b_node.inputs["Vector"])
        links.new(norm_separate_node.outputs["X"], normal_w_b_node.inputs["Vector_001"])
        links.new(normal_w_t_node.outputs["Vector"], normal_w_b_node.inputs["Vector_002"])

        #
        geometry_node = nodes.new("ShaderNodeNewGeometry")

        nov_node = nodes.new("ShaderNodeVectorMath")
        nov_node.operation = "DOT_PRODUCT"
        links.new(normal_w_b_node.outputs["Vector"], nov_node.inputs["Vector"])
        links.new(geometry_node.outputs["Incoming"], nov_node.inputs["Vector_001"])

        nov_clamp_node = nodes.new("ShaderNodeClamp")
        links.new(nov_node.outputs["Value"], nov_clamp_node.inputs["Value"])

        nov_mad_node = nodes.new("ShaderNodeMath")
        nov_mad_node.operation = "MULTIPLY_ADD"
        nov_mad_node.use_clamp = True
        nov_mad_node.inputs["Value_001"].default_value = -ps_c[11]
        nov_mad_node.inputs["Value_002"].default_value = 1
        links.new(nov_clamp_node.outputs["Result"], nov_mad_node.inputs["Value"])

        color_node = nodes.new("ShaderNodeMix")
        color_node.data_type = "VECTOR"
        color_node.factor_mode = "UNIFORM"
        color_node.inputs["A"].default_value = (ps_c[4], ps_c[5], ps_c[6])
        color_node.inputs["B"].default_value = (ps_c[0], ps_c[1], ps_c[2])
        links.new(nov_mad_node.outputs["Value"], color_node.inputs["Factor"])

        # foam
        foam_abs_node = nodes.new("ShaderNodeMath")
        foam_abs_node.operation = "ABSOLUTE"
        links.new(norm_separate_node.outputs["X"], foam_abs_node.inputs["Value"])

        vertex_color_node = nodes.new("ShaderNodeVertexColor")
        vertex_color_node.layer_name = "COLOR0"

        foam_mix_node = nodes.new("ShaderNodeMath")
        foam_mix_node.operation = "MULTIPLY"
        links.new(foam_abs_node.outputs["Value"], foam_mix_node.inputs["Value"])
        links.new(vertex_color_node.outputs["Alpha"], foam_mix_node.inputs["Value_001"])

        foam_mul_node = nodes.new("ShaderNodeMath")
        foam_mul_node.operation = "MULTIPLY"
        foam_mul_node.inputs["Value_001"].default_value = 2
        links.new(foam_mix_node.outputs["Value"], foam_mul_node.inputs["Value"])

        #
        blend_node = nodes.new("ShaderNodeVectorMath")
        blend_node.operation = "ADD"
        links.new(color_node.outputs["Result"], blend_node.inputs["Vector"])
        links.new(foam_mul_node.outputs["Value"], blend_node.inputs["Vector_001"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(vertex_color_node.outputs["Color"], light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(blend_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        # cubemap
        view_dir_neg_node = nodes.new("ShaderNodeVectorMath")
        view_dir_neg_node.operation = "MULTIPLY"
        view_dir_neg_node.inputs["Vector_001"].default_value = (-1, -1, -1)
        links.new(geometry_node.outputs["Incoming"], view_dir_neg_node.inputs["Vector"])

        reflect_node = nodes.new("ShaderNodeVectorMath")
        reflect_node.operation = "REFLECT"
        links.new(view_dir_neg_node.outputs["Vector"], reflect_node.inputs["Vector"])
        links.new(normal_w_b_node.outputs["Vector"], reflect_node.inputs["Vector_001"])

        # cubemap - in
        cube_vec_separate_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(reflect_node.outputs["Vector"], cube_vec_separate_node.inputs["Vector"])

        cube_vec_abs_node = nodes.new("ShaderNodeVectorMath")
        cube_vec_abs_node.operation = "ABSOLUTE"
        links.new(reflect_node.outputs["Vector"], cube_vec_abs_node.inputs["Vector"])

        cube_vec_abs_separate_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(cube_vec_abs_node.outputs["Vector"], cube_vec_abs_separate_node.inputs["Vector"])

        # cubemap - X
        cube_x_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(cube_vec_separate_node.outputs["Y"], cube_x_combine_node.inputs["X"])
        links.new(cube_vec_separate_node.outputs["Z"], cube_x_combine_node.inputs["Y"])

        cube_x_div_node = nodes.new("ShaderNodeVectorMath")
        cube_x_div_node.operation = "DIVIDE"
        links.new(cube_x_combine_node.outputs["Vector"], cube_x_div_node.inputs["Vector"])
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_x_div_node.inputs["Vector_001"])

        cube_x_p_node = nodes.new("ShaderNodeVectorMath")
        cube_x_p_node.operation = "MULTIPLY_ADD"
        cube_x_p_node.inputs["Vector_001"].default_value = (-0.5, 0.5, 0)
        cube_x_p_node.inputs["Vector_002"].default_value = (0.5, 5.5, 0)
        links.new(cube_x_div_node.outputs["Vector"], cube_x_p_node.inputs["Vector"])

        cube_x_n_node = nodes.new("ShaderNodeVectorMath")
        cube_x_n_node.operation = "MULTIPLY_ADD"
        cube_x_n_node.inputs["Vector_001"].default_value = (0.5, 0.5, 0)
        cube_x_n_node.inputs["Vector_002"].default_value = (0.5, 4.5, 0)
        links.new(cube_x_div_node.outputs["Vector"], cube_x_n_node.inputs["Vector"])

        cube_x_cmp_node = nodes.new("ShaderNodeMath")
        cube_x_cmp_node.operation = "GREATER_THAN"
        cube_x_cmp_node.inputs["Value_001"].default_value = 0
        links.new(cube_vec_separate_node.outputs["X"], cube_x_cmp_node.inputs["Value"])

        cube_x_mix_node = nodes.new("ShaderNodeMix")
        cube_x_mix_node.data_type = "VECTOR"
        links.new(cube_x_cmp_node.outputs["Value"], cube_x_mix_node.inputs["Factor"])
        links.new(cube_x_n_node.outputs["Vector"], cube_x_mix_node.inputs["A"])
        links.new(cube_x_p_node.outputs["Vector"], cube_x_mix_node.inputs["B"])

        # cubemap - Y
        cube_y_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(cube_vec_separate_node.outputs["X"], cube_y_combine_node.inputs["X"])
        links.new(cube_vec_separate_node.outputs["Z"], cube_y_combine_node.inputs["Y"])

        cube_y_div_node = nodes.new("ShaderNodeVectorMath")
        cube_y_div_node.operation = "DIVIDE"
        links.new(cube_y_combine_node.outputs["Vector"], cube_y_div_node.inputs["Vector"])
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_y_div_node.inputs["Vector_001"])

        cube_y_p_node = nodes.new("ShaderNodeVectorMath")
        cube_y_p_node.operation = "MULTIPLY_ADD"
        cube_y_p_node.inputs["Vector_001"].default_value = (0.5, 0.5, 0)
        cube_y_p_node.inputs["Vector_002"].default_value = (0.5, 1.5, 0)
        links.new(cube_y_div_node.outputs["Vector"], cube_y_p_node.inputs["Vector"])

        cube_y_n_node = nodes.new("ShaderNodeVectorMath")
        cube_y_n_node.operation = "MULTIPLY_ADD"
        cube_y_n_node.inputs["Vector_001"].default_value = (-0.5, 0.5, 0)
        cube_y_n_node.inputs["Vector_002"].default_value = (0.5, 0.5, 0)
        links.new(cube_y_div_node.outputs["Vector"], cube_y_n_node.inputs["Vector"])

        cube_y_cmp_node = nodes.new("ShaderNodeMath")
        cube_y_cmp_node.operation = "GREATER_THAN"
        cube_y_cmp_node.inputs["Value_001"].default_value = 0
        links.new(cube_vec_separate_node.outputs["Y"], cube_y_cmp_node.inputs["Value"])

        cube_y_mix_node = nodes.new("ShaderNodeMix")
        cube_y_mix_node.data_type = "VECTOR"
        links.new(cube_y_cmp_node.outputs["Value"], cube_y_mix_node.inputs["Factor"])
        links.new(cube_y_n_node.outputs["Vector"], cube_y_mix_node.inputs["A"])
        links.new(cube_y_p_node.outputs["Vector"], cube_y_mix_node.inputs["B"])

        # cubemap - Z
        cube_z_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(cube_vec_separate_node.outputs["X"], cube_z_combine_node.inputs["X"])
        links.new(cube_vec_separate_node.outputs["Y"], cube_z_combine_node.inputs["Y"])

        cube_z_div_node = nodes.new("ShaderNodeVectorMath")
        cube_z_div_node.operation = "DIVIDE"
        links.new(cube_z_combine_node.outputs["Vector"], cube_z_div_node.inputs["Vector"])
        links.new(cube_vec_abs_separate_node.outputs["Z"], cube_z_div_node.inputs["Vector_001"])

        cube_z_p_node = nodes.new("ShaderNodeVectorMath")
        cube_z_p_node.operation = "MULTIPLY_ADD"
        cube_z_p_node.inputs["Vector_001"].default_value = (0.5, -0.5, 0)
        cube_z_p_node.inputs["Vector_002"].default_value = (0.5, 3.5, 0)
        links.new(cube_z_div_node.outputs["Vector"], cube_z_p_node.inputs["Vector"])

        cube_z_n_node = nodes.new("ShaderNodeVectorMath")
        cube_z_n_node.operation = "MULTIPLY_ADD"
        cube_z_n_node.inputs["Vector_001"].default_value = (0.5, 0.5, 0)
        cube_z_n_node.inputs["Vector_002"].default_value = (0.5, 2.5, 0)
        links.new(cube_z_div_node.outputs["Vector"], cube_z_n_node.inputs["Vector"])

        cube_z_cmp_node = nodes.new("ShaderNodeMath")
        cube_z_cmp_node.operation = "GREATER_THAN"
        cube_z_cmp_node.inputs["Value_001"].default_value = 0
        links.new(cube_vec_separate_node.outputs["Z"], cube_z_cmp_node.inputs["Value"])

        cube_z_mix_node = nodes.new("ShaderNodeMix")
        cube_z_mix_node.data_type = "VECTOR"
        links.new(cube_z_cmp_node.outputs["Value"], cube_z_mix_node.inputs["Factor"])
        links.new(cube_z_n_node.outputs["Vector"], cube_z_mix_node.inputs["A"])
        links.new(cube_z_p_node.outputs["Vector"], cube_z_mix_node.inputs["B"])

        # cubemap - mix
        cube_yx_cmp_node = nodes.new("ShaderNodeMath")
        cube_yx_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_yx_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_yx_cmp_node.inputs["Value_001"])

        cube_yz_cmp_node = nodes.new("ShaderNodeMath")
        cube_yz_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_yz_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["Z"], cube_yz_cmp_node.inputs["Value_001"])

        cube_yx_yz_cmp_node = nodes.new("ShaderNodeMath")
        cube_yx_yz_cmp_node.operation = "MULTIPLY"
        links.new(cube_yx_cmp_node.outputs["Value"], cube_yx_yz_cmp_node.inputs["Value"])
        links.new(cube_yz_cmp_node.outputs["Value"], cube_yx_yz_cmp_node.inputs["Value_001"])

        cube_yz_mix_node = nodes.new("ShaderNodeMix")
        cube_yz_mix_node.data_type = "VECTOR"
        links.new(cube_yx_yz_cmp_node.outputs["Value"], cube_yz_mix_node.inputs["Factor"])
        links.new(cube_z_mix_node.outputs["Result"], cube_yz_mix_node.inputs["A"])
        links.new(cube_y_mix_node.outputs["Result"], cube_yz_mix_node.inputs["B"])

        cube_xy_cmp_node = nodes.new("ShaderNodeMath")
        cube_xy_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_xy_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["Y"], cube_xy_cmp_node.inputs["Value_001"])

        cube_xz_cmp_node = nodes.new("ShaderNodeMath")
        cube_xz_cmp_node.operation = "GREATER_THAN"
        links.new(cube_vec_abs_separate_node.outputs["X"], cube_xz_cmp_node.inputs["Value"])
        links.new(cube_vec_abs_separate_node.outputs["Z"], cube_xz_cmp_node.inputs["Value_001"])

        cube_xy_xz_cmp_node = nodes.new("ShaderNodeMath")
        cube_xy_xz_cmp_node.operation = "MULTIPLY"
        links.new(cube_xy_cmp_node.outputs["Value"], cube_xy_xz_cmp_node.inputs["Value"])
        links.new(cube_xz_cmp_node.outputs["Value"], cube_xy_xz_cmp_node.inputs["Value_001"])

        cube_mix_node = nodes.new("ShaderNodeMix")
        cube_mix_node.data_type = "VECTOR"
        links.new(cube_xy_xz_cmp_node.outputs["Value"], cube_mix_node.inputs["Factor"])
        links.new(cube_yz_mix_node.outputs["Result"], cube_mix_node.inputs["A"])
        links.new(cube_x_mix_node.outputs["Result"], cube_mix_node.inputs["B"])

        cube_node = nodes.new("ShaderNodeVectorMath")
        cube_node.operation = "DIVIDE"
        cube_node.inputs["Vector_001"].default_value = (1, 6, 1)
        links.new(cube_mix_node.outputs["Result"], cube_node.inputs["Vector"])

        t0 = textures[0] # CubeMap
        t0.nodes[0].extension = "CLIP"
        links.new(cube_node.outputs["Vector"], t0.in_uv)

        cube_mul_node = nodes.new("ShaderNodeVectorMath")
        cube_mul_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, cube_mul_node.inputs["Vector"])
        links.new(nov_mad_node.outputs["Value"], cube_mul_node.inputs["Vector_001"])

        cube_mad_node = nodes.new("ShaderNodeVectorMath")
        cube_mad_node.operation = "MULTIPLY_ADD"
        cube_mad_node.inputs["Vector_001"].default_value = (ps_c[8], ps_c[8], ps_c[8])
        links.new(cube_mul_node.outputs["Vector"], cube_mad_node.inputs["Vector"])
        links.new(light_map_mix_node.outputs["Vector"], cube_mad_node.inputs["Vector_002"])

        #
        links.new(cube_mad_node.outputs["Vector"], bsdf.in_rgb)

        return mat
#endregion

#region road
    @staticmethod
    def road_blnd_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        geometry_node = nodes.new("ShaderNodeNewGeometry")

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY"
        t0_uv_node.inputs["Vector_001"].default_value = (c[4], -c[4], 0)
        links.new(geometry_node.outputs["Position"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Blend_B
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t1, t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[5], c[6], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[6], 0)
        links.new(uv2_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Blend_Value
        t1.nodes[0].extension = "CLIP"
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # blend
        diff_a_node = nodes.new("ShaderNodeVectorMath")
        diff_a_node.operation = "MULTIPLY"
        diff_a_node.inputs["Vector_001"].default_value = (c[0], c[1], c[2])
        links.new(t0.out_rgb, diff_a_node.inputs["Vector"])

        diff_b_node = nodes.new("ShaderNodeVectorMath")
        diff_b_node.operation = "ADD"
        diff_b_node.inputs["Vector_001"].default_value = (c[8], c[9], c[10])
        links.new(t0.out_rgb, diff_b_node.inputs["Vector"])

        diff_mix_node = nodes.new("ShaderNodeMix")
        diff_mix_node.data_type = "VECTOR"
        diff_mix_node.factor_mode = "NON_UNIFORM"
        links.new(t1.out_rgb, diff_mix_node.inputs["Factor"])
        links.new(diff_a_node.outputs["Vector"], diff_mix_node.inputs["A"])
        links.new(diff_b_node.outputs["Vector"], diff_mix_node.inputs["B"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(diff_mix_node.outputs["Result"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def road_3clr_blnd_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        asphalt_node = textures[0]
        tiremarks_node = textures[1]
        shadow_node = textures[7]
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.inputs['Fac'].default_value = 0.8; mix_rgb_node.blend_type = 'OVERLAY'
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (600, 150); mix_darken_node.blend_type = 'DARKEN'

        # links
        links.new(asphalt_node.out_rgb, mix_rgb_node.inputs[1])
        links.new(tiremarks_node.out_rgb, mix_rgb_node.inputs[2])
        links.new(shadow_node.out_rgb, mix_darken_node.inputs[2])
        links.new(mix_rgb_node.outputs[0], mix_darken_node.inputs[1])
        links.new(mix_darken_node.outputs[0], bsdf.in_rgb)

        return mat

    @staticmethod
    def shldr_blnd_uv2_spec_clipped_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links


        t0 = textures[0] if textures else None # Diffuse_Texture
        t7 = textures[7] if len(textures) >= 7 else None # Light_Map

        if t7 is not None:
            uv2_map_node = nodes.new("ShaderNodeUVMap")
            uv2_map_node.uv_map = "TEXCOORD2"

            links.new(uv2_map_node.outputs["UV"], t7.in_uv)

            light_map_remap_node = nodes.new("ShaderNodeMix")
            light_map_remap_node.data_type = "VECTOR"
            light_map_remap_node.factor_mode = "NON_UNIFORM"
            light_map_remap_node.inputs["A"].default_value = dark_color
            light_map_remap_node.inputs["B"].default_value = light_color
            links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

            if t0 is not None:
                light_map_mix_node = nodes.new("ShaderNodeVectorMath")
                light_map_mix_node.operation = "MULTIPLY"
                links.new(t0.out_rgb, light_map_mix_node.inputs["Vector"])
                links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

                links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)
            else:
                links.new(light_map_remap_node.outputs["Result"], bsdf.in_rgb)
        elif t0 is not None:
            links.new(t0.out_rgb, bsdf.in_rgb)



        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # TextureMap_4903
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        return mat

    @staticmethod
    def road_diff_spec_ovly_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # r11.yzw = Diff_Spec02Sampler.xyz
        # r9.yzw = TextureMap_4903Sampler.xyz
        # r14.yzw = 2 * r11.yzw * r9.yzw
        # r6.yzw = 1 - 2 * (1 - r11.yzw) * (1 - r9.yzw)
        # r6.yzw = lerp(r14.yzw, r6.yzw, saturate(10000 * (r11.yzw - 0.5)))

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # TextureMap_4903
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t1, t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[4], c[5], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[5], 0)
        links.new(uv2_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Diff_Spec02
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # blend
        overlay_t1_t0_node = nodes.new("ShaderNodeMix")
        overlay_t1_t0_node.data_type = "RGBA"
        overlay_t1_t0_node.blend_type = "OVERLAY"
        overlay_t1_t0_node.inputs["Factor"].default_value = 1
        links.new(t1.out_rgb, overlay_t1_t0_node.inputs["A"])
        links.new(t0.out_rgb, overlay_t1_t0_node.inputs["B"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(overlay_t1_t0_node.outputs["Result"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def rdline_blnd_spec_opac_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.rdline_diff_opac_2(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def rdline_diff_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.diff_opac_2(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def rdline_diff_opac_clipped_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.diff_opac_2(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def rdedg_ovly_blnd_diff_spec_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t1
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Blend_A
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[4], c[5], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[5], 0)
        links.new(uv0_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Blend_B
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        # t2
        uv1_node = nodes.new("ShaderNodeUVMap")
        uv1_node.uv_map = "TEXCOORD1"

        t2_uv_node = nodes.new("ShaderNodeVectorMath")
        t2_uv_node.operation = "MULTIPLY_ADD"
        t2_uv_node.inputs["Vector_001"].default_value = (c[8], c[9], 0)
        t2_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[9], 0)
        links.new(uv1_node.outputs["UV"], t2_uv_node.inputs["Vector"])

        t2 = textures[2] # Blend_Value
        links.new(t2_uv_node.outputs["Vector"], t2.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_map_node.outputs["UV"], t7.in_uv)

        # blend
        mix_a_b_node = nodes.new("ShaderNodeMix")
        mix_a_b_node.data_type = "VECTOR"
        links.new(t2.out_a, mix_a_b_node.inputs["Factor"])
        links.new(t0.out_rgb, mix_a_b_node.inputs["A"])
        links.new(t1.out_rgb, mix_a_b_node.inputs["B"])

        overlay_t2_node = nodes.new("ShaderNodeMix")
        overlay_t2_node.data_type = "RGBA"
        overlay_t2_node.blend_type = "OVERLAY"
        overlay_t2_node.inputs["Factor"].default_value = 1
        links.new(t2.out_rgb, overlay_t2_node.inputs["A"])
        links.new(mix_a_b_node.outputs["Result"], overlay_t2_node.inputs["B"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(overlay_t2_node.outputs["Result"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def shldr_diff_spec_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.diff_spec_1(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    # amalfi road - looks great
    def road_diff_spec_ovly_blur_detailscale_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        geometry_node = nodes.new("ShaderNodeNewGeometry")

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], -c[0], 0)
        links.new(geometry_node.outputs["Position"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # TextureMap_4903
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t1, t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[1], c[2], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[2], 0)
        links.new(uv2_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Diff_Spec02
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # blend
        overlay_t1_t0_node = nodes.new("ShaderNodeMix")
        overlay_t1_t0_node.data_type = "RGBA"
        overlay_t1_t0_node.blend_type = "OVERLAY"
        overlay_t1_t0_node.inputs["Factor"].default_value = 1
        links.new(t1.out_rgb, overlay_t1_t0_node.inputs["A"])
        links.new(t0.out_rgb, overlay_t1_t0_node.inputs["B"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(overlay_t1_t0_node.outputs["Result"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    # camino road
    def road_blnd_diff_spec_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t2_a
        geometry_node = nodes.new("ShaderNodeNewGeometry")

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], -c[0], 0)
        links.new(geometry_node.outputs["Position"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Road
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t2_a_uv_node = nodes.new("ShaderNodeVectorMath")
        t2_a_uv_node.operation = "MULTIPLY"
        t2_a_uv_node.inputs["Vector_001"].default_value = (c[2], -c[2], 0)
        links.new(geometry_node.outputs["Position"], t2_a_uv_node.inputs["Vector"])

        t2_a = textures[2] # BumpBlend
        t2_a_node = t2_a.nodes[0]
        links.new(t2_a_uv_node.outputs["Vector"], t2_a.in_uv)

        # t1, t7
        uv1_node = nodes.new("ShaderNodeUVMap")
        uv1_node.uv_map = "TEXCOORD1"

        t1 = textures[1] # Skids
        t1.nodes[0].extension = "CLIP"
        links.new(uv1_node.outputs["UV"], t1.in_uv)

        t7 = textures[7] # v3lighting
        links.new(uv1_node.outputs["UV"], t7.in_uv)

        # t2_b
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t2_b_uv_node = nodes.new("ShaderNodeVectorMath")
        t2_b_uv_node.operation = "MULTIPLY_ADD"
        t2_b_uv_node.inputs["Vector_001"].default_value = (1, c[1], 0)
        t2_b_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t2_b_uv_node.inputs["Vector"])

        t2_b_node = nodes.new("ShaderNodeTexImage")
        t2_b_node.label = F"{t2_a_node.label} copy"
        t2_b_node.image = t2_a_node.image
        links.new(t2_b_uv_node.outputs["Vector"], t2_b_node.inputs["Vector"])

        # blend
        diff_add_node = nodes.new("ShaderNodeVectorMath")
        diff_add_node.operation = "ADD"
        diff_add_node.inputs["Vector_001"].default_value = (c[4], c[5], c[6])
        links.new(t0.out_rgb, diff_add_node.inputs["Vector"])

        t2_a_sep_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(t2_a.out_rgb, t2_a_sep_node.inputs["Vector"])

        t2_a_mix_node = nodes.new("ShaderNodeMix")
        t2_a_mix_node.data_type = "FLOAT"
        t2_a_mix_node.inputs["A"].default_value = 1
        links.new(t1.out_a, t2_a_mix_node.inputs["Factor"])
        links.new(t2_a_sep_node.outputs["Y"], t2_a_mix_node.inputs["B"])

        diff_mul_node = nodes.new("ShaderNodeVectorMath")
        diff_mul_node.operation = "MULTIPLY"
        links.new(diff_add_node.outputs["Vector"], diff_mul_node.inputs["Vector"])
        links.new(t2_a_mix_node.outputs["Result"], diff_mul_node.inputs["Vector_001"])

        t2_b_mix_node = nodes.new("ShaderNodeMix")
        t2_b_mix_node.data_type = "FLOAT"
        t2_b_mix_node.inputs["A"].default_value = 1
        links.new(t1.out_a, t2_b_mix_node.inputs["Factor"])
        links.new(t2_b_node.outputs["Alpha"], t2_b_mix_node.inputs["B"])

        diff_mul2_node = nodes.new("ShaderNodeVectorMath")
        diff_mul2_node.operation = "MULTIPLY"
        links.new(diff_mul_node.outputs["Vector"], diff_mul2_node.inputs["Vector"])
        links.new(t2_b_mix_node.outputs["Result"], diff_mul2_node.inputs["Vector_001"])

        t1_sep_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(t1.out_rgb, t1_sep_node.inputs["Vector"])

        color_mix_node = nodes.new("ShaderNodeMix")
        color_mix_node.data_type = "VECTOR"
        color_mix_node.factor_mode = "UNIFORM"
        color_mix_node.inputs["A"].default_value = (c[8], c[9], c[10])
        color_mix_node.inputs["B"].default_value = (1, 1, 1)
        links.new(t1_sep_node.outputs["X"], color_mix_node.inputs["Factor"])

        diff_mul3_node = nodes.new("ShaderNodeVectorMath")
        diff_mul3_node.operation = "MULTIPLY"
        links.new(diff_mul2_node.outputs["Vector"], diff_mul3_node.inputs["Vector"])
        links.new(color_mix_node.outputs["Result"], diff_mul3_node.inputs["Vector_001"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(diff_mul3_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        nol_node = nodes.new("ShaderNodeVectorMath")
        nol_node.operation = "DOT_PRODUCT"
        nol_node.inputs["Vector_001"].default_value = sun_dir
        links.new(geometry_node.outputs["Normal"], nol_node.inputs["Vector"])

        nol_apply_node = nodes.new("ShaderNodeVectorMath")
        nol_apply_node.operation = "MULTIPLY"
        links.new(light_map_mix_node.outputs["Vector"], nol_apply_node.inputs["Vector"])
        links.new(nol_node.outputs["Value"], nol_apply_node.inputs["Vector_001"])

        links.new(nol_apply_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def road_blnd_diff_spec_unlit_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t2_a
        geometry_node = nodes.new("ShaderNodeNewGeometry")

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], -c[0], 0)
        links.new(geometry_node.outputs["Position"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Road
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t2_a_uv_node = nodes.new("ShaderNodeVectorMath")
        t2_a_uv_node.operation = "MULTIPLY"
        t2_a_uv_node.inputs["Vector_001"].default_value = (c[2], -c[2], 0)
        links.new(geometry_node.outputs["Position"], t2_a_uv_node.inputs["Vector"])

        t2_a = textures[2] # BumpBlend
        t2_a_node = t2_a.nodes[0]
        links.new(t2_a_uv_node.outputs["Vector"], t2_a.in_uv)

        # t1, t7
        uv1_node = nodes.new("ShaderNodeUVMap")
        uv1_node.uv_map = "TEXCOORD1"

        t1 = textures[1] # Skids
        t1.nodes[0].extension = "CLIP"
        links.new(uv1_node.outputs["UV"], t1.in_uv)

        t7 = textures[7] # v3lighting
        links.new(uv1_node.outputs["UV"], t7.in_uv)

        # t2_b
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t2_b_uv_node = nodes.new("ShaderNodeVectorMath")
        t2_b_uv_node.operation = "MULTIPLY_ADD"
        t2_b_uv_node.inputs["Vector_001"].default_value = (1, c[1], 0)
        t2_b_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t2_b_uv_node.inputs["Vector"])

        t2_b_node = nodes.new("ShaderNodeTexImage")
        t2_b_node.label = F"{t2_a_node.label} copy"
        t2_b_node.image = t2_a_node.image
        links.new(t2_b_uv_node.outputs["Vector"], t2_b_node.inputs["Vector"])

        # blend
        diff_add_node = nodes.new("ShaderNodeVectorMath")
        diff_add_node.operation = "ADD"
        diff_add_node.inputs["Vector_001"].default_value = (c[4], c[5], c[6])
        links.new(t0.out_rgb, diff_add_node.inputs["Vector"])

        t2_a_sep_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(t2_a.out_rgb, t2_a_sep_node.inputs["Vector"])

        t2_a_mix_node = nodes.new("ShaderNodeMix")
        t2_a_mix_node.data_type = "FLOAT"
        t2_a_mix_node.inputs["A"].default_value = 1
        links.new(t1.out_a, t2_a_mix_node.inputs["Factor"])
        links.new(t2_a_sep_node.outputs["Y"], t2_a_mix_node.inputs["B"])

        diff_mul_node = nodes.new("ShaderNodeVectorMath")
        diff_mul_node.operation = "MULTIPLY"
        links.new(diff_add_node.outputs["Vector"], diff_mul_node.inputs["Vector"])
        links.new(t2_a_mix_node.outputs["Result"], diff_mul_node.inputs["Vector_001"])

        t2_b_mix_node = nodes.new("ShaderNodeMix")
        t2_b_mix_node.data_type = "FLOAT"
        t2_b_mix_node.inputs["A"].default_value = 1
        links.new(t1.out_a, t2_b_mix_node.inputs["Factor"])
        links.new(t2_b_node.outputs["Alpha"], t2_b_mix_node.inputs["B"])

        diff_mul2_node = nodes.new("ShaderNodeVectorMath")
        diff_mul2_node.operation = "MULTIPLY"
        links.new(diff_mul_node.outputs["Vector"], diff_mul2_node.inputs["Vector"])
        links.new(t2_b_mix_node.outputs["Result"], diff_mul2_node.inputs["Vector_001"])

        t1_sep_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(t1.out_rgb, t1_sep_node.inputs["Vector"])

        color_mix_node = nodes.new("ShaderNodeMix")
        color_mix_node.data_type = "VECTOR"
        color_mix_node.factor_mode = "UNIFORM"
        color_mix_node.inputs["A"].default_value = (c[8], c[9], c[10])
        color_mix_node.inputs["B"].default_value = (1, 1, 1)
        links.new(t1_sep_node.outputs["X"], color_mix_node.inputs["Factor"])

        diff_mul3_node = nodes.new("ShaderNodeVectorMath")
        diff_mul3_node.operation = "MULTIPLY"
        links.new(diff_mul2_node.outputs["Vector"], diff_mul3_node.inputs["Vector"])
        links.new(color_mix_node.outputs["Result"], diff_mul3_node.inputs["Vector_001"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(diff_mul3_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def rdedg_blnd_diff_spec_bump_4(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.road_blnd_diff_spec_3(forza_mesh,path_last_texture_folder,shader_name,material_index)

    @staticmethod
    def shldr_diff_spec_ovly_vendor_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv1_node = nodes.new("ShaderNodeUVMap")
        uv1_node.uv_map = "TEXCOORD1"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv1_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diff_Spec02
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t1
        geometry_node = nodes.new("ShaderNodeNewGeometry")

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY"
        t1_uv_node.inputs["Vector_001"].default_value = (c[2], -c[2], 0)
        links.new(geometry_node.outputs["Position"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Diff_spec
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # v3lighting
        links.new(uv2_map_node.outputs["UV"], t7.in_uv)

        # blend
        overlay_t2_t0_node = nodes.new("ShaderNodeMix")
        overlay_t2_t0_node.data_type = "RGBA"
        overlay_t2_t0_node.blend_type = "OVERLAY"
        overlay_t2_t0_node.inputs["Factor"].default_value = 1
        links.new(t1.out_rgb, overlay_t2_t0_node.inputs["A"])
        links.new(t0.out_rgb, overlay_t2_t0_node.inputs["B"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(overlay_t2_t0_node.outputs["Result"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def barr_shad_diff_spec_nolm_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.diff_spec_vert_nolm_1(forza_mesh, path_last_texture_folder, shader_name, material_index)
#endregion

#region vegetation
    @staticmethod
    def bush_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def bush_diff_opac_2_2sd_vclr(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def tree_diff_opac_vclr_2_2sd_notanfade(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.tree_diff_opac_vclr_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def tree_diff_opac_vclr_2_2sd_nofade(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_map_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # blend
        model_data_attribute = nodes.new("ShaderNodeAttribute")
        model_data_attribute.attribute_type = "INSTANCER"
        model_data_attribute.attribute_name = "model_data"

        fac_add_node = nodes.new("ShaderNodeMath")
        fac_add_node.operation = "ADD"
        fac_add_node.inputs["Value_001"].default_value = 1
        links.new(model_data_attribute.outputs["Fac"], fac_add_node.inputs["Value"])

        fac_mix_node = nodes.new("ShaderNodeVectorMath")
        fac_mix_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, fac_mix_node.inputs["Vector"])
        links.new(fac_add_node.outputs["Value"], fac_mix_node.inputs["Vector_001"])

        color_attribute_node = nodes.new("ShaderNodeVertexColor")
        color_attribute_node.layer_name = "COLOR0"

        color_mix_node = nodes.new("ShaderNodeVectorMath")
        color_mix_node.operation = "MULTIPLY"
        links.new(fac_mix_node.outputs["Vector"], color_mix_node.inputs["Vector"])
        links.new(color_attribute_node.outputs["Color"], color_mix_node.inputs["Vector_001"])

        # BSDF
        links.new(color_mix_node.outputs["Vector"], bsdf.in_rgb)

        add_opacity(mat, bsdf, out, t0.out_a)

        return mat

    @staticmethod
    def tree_diff_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def tree_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        #
        model_data_attribute = nodes.new("ShaderNodeAttribute")
        model_data_attribute.attribute_type = "INSTANCER"
        model_data_attribute.attribute_name = "model_data"

        fac_add_node = nodes.new("ShaderNodeMath")
        fac_add_node.operation = "ADD"
        fac_add_node.inputs["Value_001"].default_value = 1
        links.new(model_data_attribute.outputs["Fac"], fac_add_node.inputs["Value"])

        # blend
        diff_mul_node = nodes.new("ShaderNodeVectorMath")
        diff_mul_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, diff_mul_node.inputs["Vector"])
        links.new(fac_add_node.outputs["Value"], diff_mul_node.inputs["Vector_001"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(diff_mul_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        # BSDF
        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        add_opacity(mat, bsdf, out, t0.out_a)

        return mat

    @staticmethod
    def tree_diff_opac_2_2sd_fade(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def tree_diff_opac_vclr_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        #
        model_data_attribute = nodes.new("ShaderNodeAttribute")
        model_data_attribute.attribute_type = "INSTANCER"
        model_data_attribute.attribute_name = "model_data"

        fac_add_node = nodes.new("ShaderNodeMath")
        fac_add_node.operation = "ADD"
        fac_add_node.inputs["Value_001"].default_value = 1
        links.new(model_data_attribute.outputs["Fac"], fac_add_node.inputs["Value"])

        fac_mix_node = nodes.new("ShaderNodeVectorMath")
        fac_mix_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, fac_mix_node.inputs["Vector"])
        links.new(fac_add_node.outputs["Value"], fac_mix_node.inputs["Vector_001"])

        #
        color_attribute_node = nodes.new("ShaderNodeVertexColor")
        color_attribute_node.layer_name = "COLOR0"

        color_mul_node = nodes.new("ShaderNodeVectorMath")
        color_mul_node.operation = "MULTIPLY"
        links.new(fac_mix_node.outputs["Vector"], color_mul_node.inputs["Vector"])
        links.new(color_attribute_node.outputs["Color"], color_mul_node.inputs["Vector_001"])

        # blend
        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(color_mul_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        # BSDF
        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        add_opacity(mat, bsdf, out, t0.out_a)

        return mat

    @staticmethod
    def treecard_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def treecard_diff_opac_2_2sd_fade(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def grass_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def diff_spec_vert_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # blend
        color_attribute_node = nodes.new("ShaderNodeVertexColor")
        color_attribute_node.layer_name = "COLOR0"

        color_mix_node = nodes.new("ShaderNodeVectorMath")
        color_mix_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, color_mix_node.inputs["Vector"])
        links.new(color_attribute_node.outputs["Color"], color_mix_node.inputs["Vector_001"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(color_mix_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        # BSDF
        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat
#endregion

#region terrain
    @staticmethod
    def shldr_blnd_spec_vclr_mix_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        dirt_node = textures[0]
        grass_node = textures[1]
        mask_node = textures[2]; mask_node.nodes[0].image.colorspace_settings.name = 'Non-Color'
        rock_node = textures[3] # TODO how does this blend in camino viejo?
        amb_occlusion_node = textures[7]

        # post-diffuse nodes
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord'); tex_coord_node.location = (-600, -200)
        map_node = nodes.new('ShaderNodeMapping'); map_node.inputs['Scale'].default_value = (2.5, 2.5, 1.0); map_node.location = (-300, -400)
        map_grass_node = nodes.new('ShaderNodeMapping'); map_grass_node.inputs['Scale'].default_value = (5.0, 5.0, 1.0); map_grass_node.location = (-300, 000)
        separate_colors_node = nodes.new('ShaderNodeSeparateColor'); separate_colors_node.location = (300, -600)
        mix_mask_node = nodes.new(type='ShaderNodeMixRGB'); mix_mask_node.location = (600, 0); mix_mask_node.blend_type = 'MIX'
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (900, 0); mix_darken_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -600)

        # links
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(tex_coord_node.outputs[2], map_grass_node.inputs["Vector"])
        links.new(map_grass_node.outputs[0], grass_node.in_uv)
        links.new(map_node.outputs[0], dirt_node.in_uv)
        links.new(uv_map_node.outputs[0], amb_occlusion_node.in_uv)
        links.new(uv_map_node.outputs[0], mask_node.in_uv)
        links.new(grass_node.out_rgb, mix_mask_node.inputs[1])
        links.new(dirt_node.out_rgb, mix_mask_node.inputs[2])
        links.new(mask_node.out_rgb, separate_colors_node.inputs[0])
        links.new(separate_colors_node.outputs[2], mix_mask_node.inputs[0]) # separate blue for camino viejo
        links.new(mix_mask_node.outputs[0], mix_darken_node.inputs[1])
        links.new(amb_occlusion_node.out_rgb, mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.in_rgb)

        return mat

    @staticmethod
    def diff_opac_clampv_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0_uv_separate_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(t0_uv_node.outputs["Vector"], t0_uv_separate_node.inputs["Vector"])

        t0_v_clamp_node = nodes.new("ShaderNodeMath")
        t0_v_clamp_node.operation = "FRACT"
        links.new(t0_uv_separate_node.outputs["X"], t0_v_clamp_node.inputs["Value"])

        t0_uv_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(t0_v_clamp_node.outputs["Value"], t0_uv_combine_node.inputs["X"])
        links.new(t0_uv_separate_node.outputs["Y"], t0_uv_combine_node.inputs["Y"])

        t0 = textures[0] # Diffuse_Texture
        t0.nodes[0].extension = "CLIP"
        links.new(t0_uv_combine_node.outputs["Vector"], t0.in_uv)

        # t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # blend
        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(t0.out_rgb, light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        # BSDF
        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        add_opacity(mat, bsdf, out, t0.out_a)

        return mat

    @staticmethod
    def terr_blnd_spec_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t1
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[4], c[5], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[5], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Blend_A
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[8], c[9], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[9], 0)
        links.new(uv0_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Blend_B
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        # t2, t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t2 = textures[2] # Blend_Value
        t2.nodes[0].extension = "CLIP"
        t2.nodes[0].image.colorspace_settings.name = "Non-Color"
        links.new(uv2_node.outputs["UV"], t2.in_uv)

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # blend
        mul_a_node = nodes.new("ShaderNodeVectorMath")
        mul_a_node.operation = "MULTIPLY"
        mul_a_node.inputs["Vector_001"].default_value = (c[0], c[1], c[2])
        links.new(t0.out_rgb, mul_a_node.inputs["Vector"])

        mix_a_b_node = nodes.new("ShaderNodeMix")
        mix_a_b_node.data_type = "VECTOR"
        mix_a_b_node.factor_mode = "NON_UNIFORM"
        links.new(t2.out_rgb, mix_a_b_node.inputs["Factor"])
        links.new(mul_a_node.outputs["Vector"], mix_a_b_node.inputs["A"])
        links.new(t1.out_rgb, mix_a_b_node.inputs["B"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(mix_a_b_node.outputs["Result"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def terr_blnd_spec_vclr_mix_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        dirt_node = textures[0]
        grass_node = textures[1]
        mask_node = textures[2]; mask_node.nodes[0].image.colorspace_settings.name = 'Non-Color'
        rock_node = textures[3] # TODO how does this blend in camino viejo?
        amb_occlusion_node = textures[7]

        # post-diffuse nodes
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord'); tex_coord_node.location = (-600, -200)
        map_node = nodes.new('ShaderNodeMapping'); map_node.inputs['Scale'].default_value = (2.5, 2.5, 1.0); map_node.location = (-300, -400)
        map_grass_node = nodes.new('ShaderNodeMapping'); map_grass_node.inputs['Scale'].default_value = (5.0, 5.0, 1.0); map_grass_node.location = (-300, 000)
        separate_colors_node = nodes.new('ShaderNodeSeparateColor'); separate_colors_node.location = (300, -600)
        mix_mask_node = nodes.new(type='ShaderNodeMixRGB'); mix_mask_node.location = (600, 0); mix_mask_node.blend_type = 'MIX'
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (900, 0); mix_darken_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -600)

        # links
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(tex_coord_node.outputs[2], map_grass_node.inputs["Vector"])
        links.new(map_grass_node.outputs[0], grass_node.in_uv)
        links.new(map_node.outputs[0], dirt_node.in_uv)
        links.new(uv_map_node.outputs[0], amb_occlusion_node.in_uv)
        links.new(uv_map_node.outputs[0], mask_node.in_uv)
        links.new(grass_node.out_rgb, mix_mask_node.inputs[1])
        links.new(dirt_node.out_rgb, mix_mask_node.inputs[2])
        links.new(mask_node.out_rgb, separate_colors_node.inputs[0])
        links.new(separate_colors_node.outputs[2], mix_mask_node.inputs[0]) # separate blue for camino viejo
        links.new(mix_mask_node.outputs[0], mix_darken_node.inputs[1])
        links.new(amb_occlusion_node.out_rgb, mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.in_rgb)

        return mat

    @staticmethod
    def terr_2_blnd_spec_vclr_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        grass_node = textures[0]
        rock1_node = textures[1]
        mask_node = textures[2]; mask_node.nodes[0].image.colorspace_settings.name = 'Non-Color'
        ambient_occlusion_node = textures[7]

        uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -900)
        links.new(uv_map_node.outputs[0], ambient_occlusion_node.in_uv)

        uv_map_node_2 = nodes.new('ShaderNodeUVMap'); uv_map_node_2.uv_map = "TEXCOORD2"; uv_map_node_2.location = (-300, -700)
        links.new(uv_map_node_2.outputs[0], mask_node.in_uv)

        # post-diffuse nodes
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord'); tex_coord_node.location = (-600, -200)
        map_node = nodes.new('ShaderNodeMapping'); map_node.inputs['Scale'].default_value = (2.5, 2.5, 1.0); map_node.location = (-300, -400)
        map_grass_node = nodes.new('ShaderNodeMapping'); map_grass_node.inputs['Scale'].default_value = (5.0, 5.0, 1.0); map_grass_node.location = (-300, 000)
        normal_map_node = nodes.new(type='ShaderNodeNormalMap'); normal_map_node.location = (300, -1500)
        mix_mask_node = nodes.new(type='ShaderNodeMixRGB'); mix_mask_node.location = (600, 0); mix_mask_node.blend_type = 'MIX'
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (900, 0); mix_darken_node.blend_type = 'DARKEN'

        # links
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(tex_coord_node.outputs[2], map_grass_node.inputs["Vector"])
        links.new(map_grass_node.outputs[0], grass_node.in_uv)
        links.new(map_node.outputs[0], rock1_node.in_uv)
        links.new(grass_node.out_rgb, mix_mask_node.inputs[1])
        links.new(rock1_node.out_rgb, mix_mask_node.inputs[2])
        links.new(mask_node.out_rgb, mix_mask_node.inputs[0])
        links.new(mix_mask_node.outputs[0], mix_darken_node.inputs[1])
        links.new(ambient_occlusion_node.out_rgb, mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.in_rgb)


        return mat

    @staticmethod
    def terr_2_blnd_spec_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        grass_node = textures[0]
        rock1_node = textures[1]
        mask_node = textures[2]; mask_node.nodes[0].image.colorspace_settings.name = 'Non-Color'
        ambient_occlusion_node = textures[7]

        uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -900)
        links.new(uv_map_node.outputs[0], ambient_occlusion_node.in_uv)

        uv_map_node_2 = nodes.new('ShaderNodeUVMap'); uv_map_node_2.uv_map = "TEXCOORD2"; uv_map_node_2.location = (-300, -700)
        links.new(uv_map_node_2.outputs[0], mask_node.in_uv)

        # post-diffuse nodes
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord'); tex_coord_node.location = (-600, -200)
        map_node = nodes.new('ShaderNodeMapping'); map_node.inputs['Scale'].default_value = (2.5, 2.5, 1.0); map_node.location = (-300, -400)
        map_grass_node = nodes.new('ShaderNodeMapping'); map_grass_node.inputs['Scale'].default_value = (5.0, 5.0, 1.0); map_grass_node.location = (-300, 000)
        normal_map_node = nodes.new(type='ShaderNodeNormalMap'); normal_map_node.location = (300, -1500)
        mix_mask_node = nodes.new(type='ShaderNodeMixRGB'); mix_mask_node.location = (600, 0); mix_mask_node.blend_type = 'MIX'
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (900, 0); mix_darken_node.blend_type = 'DARKEN'

        # links
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(tex_coord_node.outputs[2], map_grass_node.inputs["Vector"])
        links.new(map_grass_node.outputs[0], grass_node.in_uv)
        links.new(map_node.outputs[0], rock1_node.in_uv)
        links.new(grass_node.out_rgb, mix_mask_node.inputs[1])
        links.new(rock1_node.out_rgb, mix_mask_node.inputs[2])
        links.new(mask_node.out_rgb, mix_mask_node.inputs[0])
        links.new(mix_mask_node.outputs[0], mix_darken_node.inputs[1])
        links.new(ambient_occlusion_node.out_rgb, mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.in_rgb)

        return mat

    @staticmethod
    def terr_blnd_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[4], c[5], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[5], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Blend_A
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t1
        uv1_node = nodes.new("ShaderNodeUVMap")
        uv1_node.uv_map = "TEXCOORD1"

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[8], c[9], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[9], 0)
        links.new(uv1_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Blend_B
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        # t2, t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t2 = textures[2] # Blend_Value
        t2.nodes[0].extension = "CLIP"
        links.new(uv2_node.outputs["UV"], t2.in_uv)

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # blend
        mul_a_node = nodes.new("ShaderNodeVectorMath")
        mul_a_node.operation = "MULTIPLY"
        mul_a_node.inputs["Vector_001"].default_value = (c[0], c[1], c[2])
        links.new(t0.out_rgb, mul_a_node.inputs["Vector"])

        mix_a_b_node = nodes.new("ShaderNodeMix")
        mix_a_b_node.data_type = "VECTOR"
        mix_a_b_node.factor_mode = "NON_UNIFORM"
        links.new(t2.out_rgb, mix_a_b_node.inputs["Factor"])
        links.new(mul_a_node.outputs["Vector"], mix_a_b_node.inputs["A"])
        links.new(t1.out_rgb, mix_a_b_node.inputs["B"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(mix_a_b_node.outputs["Result"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def terr_blnd_spec_norm_5(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t3, t4
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[4], c[4], 0) # NodeSocketVector
        t0_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[4], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Blend_A
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t3_uv_node = nodes.new("ShaderNodeVectorMath")
        t3_uv_node.operation = "MULTIPLY_ADD"
        t3_uv_node.inputs["Vector_001"].default_value = (c[6], c[6], 0)
        t3_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[6], 0)
        links.new(uv0_node.outputs["UV"], t3_uv_node.inputs["Vector"])

        t3 = textures[3] # Blend_C
        links.new(t3_uv_node.outputs["Vector"], t3.in_uv)

        t4_uv_node = nodes.new("ShaderNodeVectorMath")
        t4_uv_node.operation = "MULTIPLY_ADD"
        t4_uv_node.inputs["Vector_001"].default_value = (c[9], c[9], 0)
        t4_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[9], 0)
        links.new(uv0_node.outputs["UV"], t4_uv_node.inputs["Vector"])

        t4 = textures[4] # NormalMap
        links.new(t4_uv_node.outputs["Vector"], t4.in_uv)

        # t1, t2
        uv1_node = nodes.new("ShaderNodeUVMap")
        uv1_node.uv_map = "TEXCOORD1"

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[5], c[5], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, 1 - c[5], 0)
        links.new(uv1_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Blend_B
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        t2 = textures[2] # Blend_Value
        t2.nodes[0].extension = "CLIP"
        t2.nodes[0].image.colorspace_settings.name = "Non-Color"
        links.new(uv1_node.outputs["UV"], t2.in_uv)

        # t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # normal map
        t4_mad_node = nodes.new("ShaderNodeVectorMath")
        t4_mad_node.operation = "MULTIPLY_ADD"
        t4_mad_node.inputs["Vector_001"].default_value = (2, 2, 0)
        t4_mad_node.inputs["Vector_002"].default_value = (-1, -1, 0)
        links.new(t4.out_rgb, t4_mad_node.inputs["Vector"])

        # normal map Z
        norm_z_dot_node = nodes.new("ShaderNodeVectorMath")
        norm_z_dot_node.operation = "DOT_PRODUCT"
        links.new(t4_mad_node.outputs["Vector"], norm_z_dot_node.inputs["Vector"])
        links.new(t4_mad_node.outputs["Vector"], norm_z_dot_node.inputs["Vector_001"])

        norm_z_sub_node = nodes.new("ShaderNodeMath")
        norm_z_sub_node.operation = "SUBTRACT"
        norm_z_sub_node.inputs["Value"].default_value = 1
        links.new(norm_z_dot_node.outputs["Value"], norm_z_sub_node.inputs["Value_001"])

        norm_z_abs_node = nodes.new("ShaderNodeMath")
        norm_z_abs_node.operation = "ABSOLUTE"
        links.new(norm_z_sub_node.outputs["Value"], norm_z_abs_node.inputs["Value"])

        norm_z_node = nodes.new("ShaderNodeMath")
        norm_z_node.operation = "SQRT"
        links.new(norm_z_abs_node.outputs["Value"], norm_z_node.inputs["Value"])

        # face space normal
        norm_xy_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(t4_mad_node.outputs["Vector"], norm_xy_node.inputs["Vector"])

        norm_combine_node = nodes.new("ShaderNodeCombineXYZ")
        links.new(norm_xy_node.outputs["X"], norm_combine_node.inputs["X"])
        links.new(norm_xy_node.outputs["Y"], norm_combine_node.inputs["Y"])
        links.new(norm_z_node.outputs["Value"], norm_combine_node.inputs["Z"])

        norm_node = nodes.new("ShaderNodeVectorMath")
        norm_node.operation = "NORMALIZE"
        links.new(norm_combine_node.outputs["Vector"], norm_node.inputs["Vector"])

        norm_separate_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(norm_node.outputs["Vector"], norm_separate_node.inputs["Vector"])

        # tangent
        tangent_attr_node = nodes.new("ShaderNodeAttribute")
        tangent_attr_node.attribute_name = "BINORMAL0"

        tangent_tr_node = nodes.new("ShaderNodeVectorTransform")
        tangent_tr_node.vector_type = "NORMAL"
        tangent_tr_node.convert_from = "OBJECT"
        tangent_tr_node.convert_to = "WORLD"
        links.new(tangent_attr_node.outputs["Vector"], tangent_tr_node.inputs["Vector"])

        # bitangent
        bitangent_attr_node = nodes.new("ShaderNodeAttribute")
        bitangent_attr_node.attribute_name = "TANGENT0"

        bitangent_tr_node = nodes.new("ShaderNodeVectorTransform")
        bitangent_tr_node.vector_type = "NORMAL"
        bitangent_tr_node.convert_from = "OBJECT"
        bitangent_tr_node.convert_to = "WORLD"
        links.new(bitangent_attr_node.outputs["Vector"], bitangent_tr_node.inputs["Vector"])

        # normal
        geometry_node = nodes.new("ShaderNodeNewGeometry")

        # world space normal
        normal_w_n_node = nodes.new("ShaderNodeVectorMath")
        normal_w_n_node.operation = "MULTIPLY"
        links.new(geometry_node.outputs["Normal"], normal_w_n_node.inputs["Vector"])
        links.new(norm_separate_node.outputs["Z"], normal_w_n_node.inputs["Vector_001"])

        normal_w_t_node = nodes.new("ShaderNodeVectorMath")
        normal_w_t_node.operation = "MULTIPLY_ADD"
        links.new(bitangent_tr_node.outputs["Vector"], normal_w_t_node.inputs["Vector"])
        links.new(norm_separate_node.outputs["Y"], normal_w_t_node.inputs["Vector_001"])
        links.new(normal_w_n_node.outputs["Vector"], normal_w_t_node.inputs["Vector_002"])

        normal_w_b_node = nodes.new("ShaderNodeVectorMath")
        normal_w_b_node.operation = "MULTIPLY_ADD"
        links.new(tangent_tr_node.outputs["Vector"], normal_w_b_node.inputs["Vector"])
        links.new(norm_separate_node.outputs["X"], normal_w_b_node.inputs["Vector_001"])
        links.new(normal_w_t_node.outputs["Vector"], normal_w_b_node.inputs["Vector_002"])

        normal_w_node = nodes.new("ShaderNodeVectorMath")
        normal_w_node.operation = "NORMALIZE"
        links.new(normal_w_b_node.outputs["Vector"], normal_w_node.inputs["Vector"])

        normal_sub_node = nodes.new("ShaderNodeVectorMath")
        normal_sub_node.operation = "SUBTRACT"
        links.new(normal_w_node.outputs["Vector"], normal_sub_node.inputs["Vector"])
        links.new(geometry_node.outputs["Normal"], normal_sub_node.inputs["Vector_001"])

        normal_sub_dot_node = nodes.new("ShaderNodeVectorMath")
        normal_sub_dot_node.operation = "DOT_PRODUCT"
        normal_sub_dot_node.inputs["Vector_001"].default_value = sun_dir
        links.new(normal_sub_node.outputs["Vector"], normal_sub_dot_node.inputs["Vector"])

        light_map_gray_node = nodes.new("ShaderNodeVectorMath")
        light_map_gray_node.operation = "DOT_PRODUCT"
        light_map_gray_node.inputs["Vector_001"].default_value = (0.2126, 0.7152, 0.0722)
        links.new(t7.out_rgb, light_map_gray_node.inputs["Vector"])

        # blend
        blend_value_separate_node = nodes.new("ShaderNodeSeparateXYZ")
        links.new(t2.out_rgb, blend_value_separate_node.inputs["Vector"])

        mix_a_b_node = nodes.new("ShaderNodeMix")
        mix_a_b_node.data_type = "VECTOR"
        links.new(blend_value_separate_node.outputs["Y"], mix_a_b_node.inputs["Factor"])
        links.new(t0.out_rgb, mix_a_b_node.inputs["A"])
        links.new(t1.out_rgb, mix_a_b_node.inputs["B"])

        mix_c_node = nodes.new("ShaderNodeMix")
        mix_c_node.data_type = "VECTOR"
        links.new(blend_value_separate_node.outputs["Z"], mix_c_node.inputs["Factor"])
        links.new(mix_a_b_node.outputs["Result"], mix_c_node.inputs["A"])
        links.new(t3.out_rgb, mix_c_node.inputs["B"])

        mix_blend_value_r_node = nodes.new("ShaderNodeVectorMath")
        mix_blend_value_r_node.operation = "MULTIPLY"
        links.new(mix_c_node.outputs["Result"], mix_blend_value_r_node.inputs["Vector"])
        links.new(blend_value_separate_node.outputs["X"], mix_blend_value_r_node.inputs["Vector_001"])

        diffuse_remap_node = nodes.new("ShaderNodeVectorMath")
        diffuse_remap_node.name = "DiffuseRemap"
        diffuse_remap_node.operation = "MULTIPLY"
        diffuse_remap_node.inputs["Vector_001"].default_value = (c[0] * c[10], c[1] * c[10], c[2] * c[10])
        links.new(mix_blend_value_r_node.outputs["Vector"], diffuse_remap_node.inputs["Vector"])

        light_map_mad_node = nodes.new("ShaderNodeVectorMath")
        light_map_mad_node.operation = "MULTIPLY_ADD"
        links.new(normal_sub_dot_node.outputs["Value"], light_map_mad_node.inputs["Vector"])
        links.new(light_map_gray_node.outputs["Value"], light_map_mad_node.inputs["Vector_001"])
        links.new(t7.out_rgb, light_map_mad_node.inputs["Vector_002"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(light_map_mad_node.outputs["Vector"], light_map_remap_node.inputs["Factor"])

        light_map_mix_node = nodes.new("ShaderNodeVectorMath")
        light_map_mix_node.operation = "MULTIPLY"
        links.new(diffuse_remap_node.outputs["Vector"], light_map_mix_node.inputs["Vector"])
        links.new(light_map_remap_node.outputs["Result"], light_map_mix_node.inputs["Vector_001"])

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def shldr_blnd_spec_norm_5(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.terr_blnd_spec_norm_5(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes = mat.node_tree.nodes

        diffuse_remap_node = nodes["DiffuseRemap"]
        diffuse_remap_node.inputs["Vector_001"].default_value = (1, 1, 1)

        return mat
#endregion
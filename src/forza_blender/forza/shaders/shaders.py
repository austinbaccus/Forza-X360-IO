import math
import bpy # type: ignore
from mathutils import Color # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.shaders.shaders_util import *

# TrackSettings.xml
dark_color = (0, 0, 0)
light_color = (1.93, 1.93, 1.9)

def generate_blender_materials_for_mesh(forza_mesh: ForzaMesh, track_folder_path):
    materials = []
    for sub in forza_mesh.track_section.subsections:
        fx_filename_index = forza_mesh.track_bin.material_sets[0].materials[sub.material_index].fx_filename_index
        shader_filename_simple = (forza_mesh.track_bin.shader_filenames[fx_filename_index].split('\\')[-1]).split('.')[0]
        material_name = F"{sub.name} {shader_filename_simple}"

        args = (forza_mesh, track_folder_path, material_name, sub.material_index)

        func = getattr(Shaders, shader_filename_simple, None)
        if callable(func):
            materials.append(func(*args))
        else:
            materials.append(Shaders.unknown(forza_mesh, track_folder_path, material_name, sub.material_index))
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

        color_node = nodes.new("NodeReroute")

        # color < 0.04045
        cmp_sub_node = nodes.new("ShaderNodeVectorMath")
        cmp_sub_node.operation = "SUBTRACT"
        cmp_sub_node.inputs["Vector"].default_value = (0.04045, 0.04045, 0.04045)
        links.new(color_node.outputs["Output"], cmp_sub_node.inputs["Vector_001"])

        cmp_mul_node = nodes.new("ShaderNodeVectorMath")
        cmp_mul_node.operation = "MULTIPLY"
        cmp_mul_node.inputs["Vector_001"].default_value = (math.inf, math.inf, math.inf)
        links.new(cmp_sub_node.outputs["Vector"], cmp_mul_node.inputs["Vector"])

        # power
        power_add_node = nodes.new("ShaderNodeVectorMath")
        power_add_node.inputs["Vector_001"].default_value = (0.055, 0.055, 0.055)
        links.new(color_node.outputs["Output"], power_add_node.inputs["Vector"])

        power_div_node = nodes.new("ShaderNodeVectorMath")
        power_div_node.operation = "DIVIDE"
        power_div_node.inputs["Vector_001"].default_value = (1.055, 1.055, 1.055)
        links.new(power_add_node.outputs["Vector"], power_div_node.inputs["Vector"])

        power_node = nodes.new("ShaderNodeVectorMath")
        power_node.operation = "POWER"
        power_node.inputs["Vector_001"].default_value = (2.4, 2.4, 2.4)
        links.new(power_div_node.outputs["Vector"], power_node.inputs["Vector"])

        # linear
        linear_node = nodes.new("ShaderNodeVectorMath")
        linear_node.operation = "DIVIDE"
        linear_node.inputs["Vector_001"].default_value = (12.92, 12.92, 12.92)
        links.new(color_node.outputs["Output"], linear_node.inputs["Vector"])

        # sRGB to linear
        mix_node = nodes.new("ShaderNodeMix")
        mix_node.data_type = "VECTOR"
        mix_node.factor_mode = "NON_UNIFORM"
        links.new(cmp_mul_node.outputs["Vector"], mix_node.inputs["Factor"])
        links.new(power_node.outputs["Vector"], mix_node.inputs["A"])
        links.new(linear_node.outputs["Vector"], mix_node.inputs["B"])

        bsdf = nodes.new("ShaderNodeEmission")
        links.new(mix_node.outputs["Result"], bsdf.inputs["Color"])

        out = nodes.new("ShaderNodeOutputMaterial")
        links.new(bsdf.outputs["Emission"], out.inputs["Surface"])

        bsdf_wrapper = NodeWrapperShader(bsdf, color_node.inputs["Input"], bsdf.outputs["Emission"])

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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
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

        transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")

        transparency_mix_node = nodes.new("ShaderNodeMixShader")
        links.new(t0.out_a, transparency_mix_node.inputs["Fac"])
        links.new(transparent_bsdf.outputs["BSDF"], transparency_mix_node.inputs["Shader"])
        links.new(bsdf.out_shader, transparency_mix_node.inputs["Shader_001"])

        links.new(transparency_mix_node.outputs["Shader"], out.inputs["Surface"])

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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
        links.new(uv0_map_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD0"

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

        transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")

        transparency_mix_node = nodes.new("ShaderNodeMixShader")
        links.new(t0.out_a, transparency_mix_node.inputs["Fac"])
        links.new(transparent_bsdf.outputs["BSDF"], transparency_mix_node.inputs["Shader"])
        links.new(bsdf.out_shader, transparency_mix_node.inputs["Shader_001"])

        links.new(transparency_mix_node.outputs["Shader"], out.inputs["Surface"])

        return mat
    
    @staticmethod
    def diff_opac_2_nolm(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        mat.node_tree.links.new(textures[0].out_rgb, bsdf.in_rgb)
        # mat.node_tree.links.new(textures[0].out_a, bsdf.inputs["Alpha"])
        return mat
    
    @staticmethod
    def diff_opac_clampuv_nolm_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        mat.node_tree.links.new(textures[0].out_rgb, bsdf.in_rgb)
        # mat.node_tree.links.new(textures[0].out_a, bsdf.inputs["Alpha"])
        return mat
    
    @staticmethod
    def diff_opac_clamp_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        mat.node_tree.links.new(textures[0].out_rgb, bsdf.in_rgb)
        # mat.node_tree.links.new(textures[0].out_a, bsdf.inputs["Alpha"])
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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
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
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)

        # nodes
        diffuse_node = textures[2]
        ambient_occlusion_node = textures[7]
        mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.in_uv)
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.in_rgb)
        mat.node_tree.links.new(diffuse_node.out_rgb, mix_rgb_node.inputs[1])
        mat.node_tree.links.new(ambient_occlusion_node.out_rgb, mix_rgb_node.inputs[2])

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

        # t2
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t2_uv_node = nodes.new("ShaderNodeVectorMath")
        t2_uv_node.operation = "MULTIPLY_ADD"
        t2_uv_node.inputs["Vector_001"].default_value = (c[4], c[5], 0)
        t2_uv_node.inputs["Vector_002"].default_value = (0, -c[5], 0)
        links.new(uv0_map_node.outputs["UV"], t2_uv_node.inputs["Vector"])

        t2 = textures[2] # Diffuse_Texture
        links.new(t2_uv_node.outputs["Vector"], t2.in_uv)

        # t7
        uv2_map_node = nodes.new("ShaderNodeUVMap")
        uv2_map_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_map_node.outputs["UV"], t7.in_uv)

        # blend
        t2_mul_node = nodes.new("ShaderNodeVectorMath")
        t2_mul_node.operation = "MULTIPLY"
        t2_mul_node.inputs["Vector_001"].default_value = (c[3], c[3], c[3])
        links.new(t2.out_rgb, t2_mul_node.inputs["Vector"])

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

        transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")

        transparency_mix_node = nodes.new("ShaderNodeMixShader")
        links.new(transparency_remap_node.outputs["Result"], transparency_mix_node.inputs["Fac"])
        links.new(transparent_bsdf.outputs["BSDF"], transparency_mix_node.inputs["Shader"])
        links.new(bsdf.out_shader, transparency_mix_node.inputs["Shader_001"])

        links.new(transparency_mix_node.outputs["Shader"], out.inputs["Surface"])

        return mat

    @staticmethod
    def diff_spec_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)

        # nodes
        diffuse_node = textures[0]
        roughness_node = textures[1]
        shadow_node = textures[7]
        darken_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); darken_node.location = (300, 0); darken_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], shadow_node.in_uv)
        mat.node_tree.links.new(darken_node.outputs[0], bsdf.in_rgb)
        mat.node_tree.links.new(diffuse_node.out_rgb, darken_node.inputs[1])
        mat.node_tree.links.new(shadow_node.out_rgb, darken_node.inputs[2])
        # mat.node_tree.links.new(diffuse_node.out_a, bsdf.inputs['Alpha'])
        # mat.node_tree.links.new(roughness_node.out_rgb, bsdf.inputs[2])

        return mat  

    @staticmethod
    def diff_spec_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
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

        transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")

        transparency_mix_node = nodes.new("ShaderNodeMixShader")
        links.new(t0.out_a, transparency_mix_node.inputs["Fac"])
        links.new(transparent_bsdf.outputs["BSDF"], transparency_mix_node.inputs["Shader"])
        links.new(bsdf.out_shader, transparency_mix_node.inputs["Shader_001"])

        links.new(transparency_mix_node.outputs["Shader"], out.inputs["Surface"])

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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
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

        transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")

        transparency_mix_node = nodes.new("ShaderNodeMixShader")
        links.new(transparency_remap_node.outputs["Value"], transparency_mix_node.inputs["Fac"])
        links.new(transparent_bsdf.outputs["BSDF"], transparency_mix_node.inputs["Shader"])
        links.new(bsdf.out_shader, transparency_mix_node.inputs["Shader_001"])

        links.new(transparency_mix_node.outputs["Shader"], out.inputs["Surface"])

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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
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
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        diffuse_node = textures[0]
        #roughness_node = textures[1]
        #shadow_node = textures[7]
        #mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        #uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        #links.new(uv_map_node.outputs["UV"], shadow_node.in_uv)
        #links.new(mix_rgb_node.outputs[0], bsdf.in_rgb)
        #links.new(diffuse_node.out_rgb, mix_rgb_node.inputs[1])
        #links.new(shadow_node.out_rgb, mix_rgb_node.inputs[2])
        # links.new(diffuse_node.out_a, bsdf.inputs['Alpha'])
        links.new(diffuse_node.out_rgb, bsdf.in_rgb)

        return mat

    @staticmethod
    def chain_diff_spec_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)

        # nodes
        diffuse_node = textures[0]
        ambient_occlusion_node = textures[7]
        mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.in_uv)
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.in_rgb)
        mat.node_tree.links.new(diffuse_node.out_rgb, mix_rgb_node.inputs[1])
        # mat.node_tree.links.new(diffuse_node.out_a, bsdf.inputs['Alpha'])
        mat.node_tree.links.new(ambient_occlusion_node.out_rgb, mix_rgb_node.inputs[2])

        return mat
    
    @staticmethod
    def chain_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)

        # nodes
        diffuse_node = textures[0]
        ambient_occlusion_node = textures[7]
        mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.in_uv)
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.in_rgb)
        mat.node_tree.links.new(diffuse_node.out_rgb, mix_rgb_node.inputs[1])
        # mat.node_tree.links.new(diffuse_node.out_a, bsdf.inputs['Alpha'])
        mat.node_tree.links.new(ambient_occlusion_node.out_rgb, mix_rgb_node.inputs[2])

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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -1 / c[5], 0)
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
#endregion

#region ocean
    @staticmethod
    def ocean_anim_norm_refl_5(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, _, _ = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        return mat
#endregion

#region road
    @staticmethod
    def road_blnd_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.road_diff_spec_ovly_blur_detailscale_2(forza_mesh, path_last_texture_folder, shader_name, material_index)

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
        t1_uv_node.inputs["Vector_002"].default_value = (0, -c[2], 0)
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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # TextureMap_4903
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # t1, t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[4], c[5], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, -c[5], 0)
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
    def rdline_diff_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        diffuse_node = textures[0]
        shadow_node = textures[7]
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (600, 150); mix_darken_node.blend_type = 'DARKEN'

        transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")
        transparency_mix_node = nodes.new("ShaderNodeMixShader")

        # links
        links.new(diffuse_node.out_rgb, mix_darken_node.inputs[1])
        links.new(shadow_node.out_rgb, mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.in_rgb)

        links.new(diffuse_node.out_a, transparency_mix_node.inputs["Fac"])
        links.new(transparent_bsdf.outputs["BSDF"], transparency_mix_node.inputs["Shader"])
        links.new(bsdf.out_shader, transparency_mix_node.inputs["Shader_001"])
        links.new(transparency_mix_node.outputs["Shader"], _.inputs["Surface"])
        
        return mat

    @staticmethod
    def rdline_diff_opac_clipped_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

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

        transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")

        transparency_mix_node = nodes.new("ShaderNodeMixShader")
        links.new(t0.out_a, transparency_mix_node.inputs["Fac"])
        links.new(transparent_bsdf.outputs["BSDF"], transparency_mix_node.inputs["Shader"])
        links.new(bsdf.out_shader, transparency_mix_node.inputs["Shader_001"])

        links.new(transparency_mix_node.outputs["Shader"], out.inputs["Surface"])
        
        return mat

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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Blend_A
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[4], c[5], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, -c[5], 0)
        links.new(uv0_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Blend_B
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        # t2
        uv1_node = nodes.new("ShaderNodeUVMap")
        uv1_node.uv_map = "TEXCOORD1"

        t2_uv_node = nodes.new("ShaderNodeVectorMath")
        t2_uv_node.operation = "MULTIPLY_ADD"
        t2_uv_node.inputs["Vector_001"].default_value = (c[8], c[9], 0)
        t2_uv_node.inputs["Vector_002"].default_value = (0, -c[9], 0)
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
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

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

        links.new(light_map_mix_node.outputs["Vector"], bsdf.in_rgb)

        return mat

    @staticmethod
    def road_blnd_diff_spec_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        diffuse_node = textures[0]
        tiremarks_node = textures[1]
        shadow_node = textures[7]
        map_node = nodes.new('ShaderNodeMapping'); map_node.inputs['Scale'].default_value = (10.0, 10.0, 1.0); map_node.location = (-300, -300)
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord'); tex_coord_node.location = (-600, -300)
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (300, 150); mix_darken_node.blend_type = 'DARKEN'; mix_darken_node.inputs['Fac'].default_value = 1.0
        mix_darken2_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken2_node.location = (300, 150); mix_darken2_node.blend_type = 'DARKEN'
        uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD1"; uv_map_node.location = (-300, -600)

        

        # links
        links.new(diffuse_node.out_rgb, mix_darken_node.inputs[1])
        links.new(tiremarks_node.out_rgb, mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], mix_darken2_node.inputs[1])
        links.new(shadow_node.out_rgb, mix_darken2_node.inputs[2])
        links.new(mix_darken2_node.outputs[0], bsdf.in_rgb)
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(map_node.outputs[0], diffuse_node.in_uv)
        links.new(uv_map_node.outputs[0], shadow_node.in_uv)
        links.new(uv_map_node.outputs[0], tiremarks_node.in_uv)

        return mat

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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
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

        t7 = textures[7] # Light_Map
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
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        # BSDF
        links.new(t0.out_rgb, bsdf.in_rgb)

        return mat
#endregion

#region vegetation
    @staticmethod
    def bush_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[0], c[1], 0)
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
        links.new(uv0_map_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

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

        transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")

        transparency_mix_node = nodes.new("ShaderNodeMixShader")
        links.new(t0.out_a, transparency_mix_node.inputs["Fac"])
        links.new(transparent_bsdf.outputs["BSDF"], transparency_mix_node.inputs["Shader"])
        links.new(bsdf.out_shader, transparency_mix_node.inputs["Shader_001"])

        links.new(transparency_mix_node.outputs["Shader"], out.inputs["Surface"])

        return mat
    
    @staticmethod
    def bush_diff_opac_2_2sd_vclr(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def tree_diff_opac_vclr_2_2sd_notanfade(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def tree_diff_opac_vclr_2_2sd_nofade(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat, out, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0
        uv0_map_node = nodes.new("ShaderNodeUVMap")
        uv0_map_node.uv_map = "TEXCOORD0"

        t0 = textures[0] # Diffuse_Texture
        links.new(uv0_map_node.outputs["UV"], t0.in_uv)

        # BSDF
        links.new(t0.out_rgb, bsdf.in_rgb)

        transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")

        transparency_mix_node = nodes.new("ShaderNodeMixShader")
        links.new(t0.out_a, transparency_mix_node.inputs["Fac"])
        links.new(transparent_bsdf.outputs["BSDF"], transparency_mix_node.inputs["Shader"])
        links.new(bsdf.out_shader, transparency_mix_node.inputs["Shader_001"])

        links.new(transparency_mix_node.outputs["Shader"], out.inputs["Surface"])

        return mat

    @staticmethod
    def tree_diff_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def tree_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)
    
    @staticmethod
    def tree_diff_opac_2_2sd_fade(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def tree_diff_opac_vclr_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

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
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        
        # links
        mat.node_tree.links.new(textures[0].out_rgb, bsdf.in_rgb)

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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[1], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Diffuse_Texture
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

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

        transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")

        transparency_mix_node = nodes.new("ShaderNodeMixShader")
        links.new(t0.out_a, transparency_mix_node.inputs["Fac"])
        links.new(transparent_bsdf.outputs["BSDF"], transparency_mix_node.inputs["Shader"])
        links.new(bsdf.out_shader, transparency_mix_node.inputs["Shader_001"])

        links.new(transparency_mix_node.outputs["Shader"], out.inputs["Surface"])

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
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[5], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Blend_A
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[8], c[9], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, -c[9], 0)
        links.new(uv0_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Blend_B
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        # t2, t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t2 = textures[2] # Blend_Value
        t2.nodes[0].image.colorspace_settings.name = "Non-Color"
        links.new(uv2_node.outputs["UV"], t2.in_uv)

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

        # blend
        mix_a_b_node = nodes.new("ShaderNodeMix")
        mix_a_b_node.data_type = "VECTOR"
        mix_a_b_node.factor_mode = "NON_UNIFORM"
        links.new(t2.out_rgb, mix_a_b_node.inputs["Factor"])
        links.new(t0.out_rgb, mix_a_b_node.inputs["A"])
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
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        grass_node = textures[0]
        rock1_node = textures[1]
        mask_node = textures[2]; mask_node.nodes[0].image.colorspace_settings.name = 'Non-Color'
        shadow_node = textures[7]

        # post-diffuse nodes
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord'); tex_coord_node.location = (-600, -200)
        map_node = nodes.new('ShaderNodeMapping'); map_node.inputs['Scale'].default_value = (2.5, 2.5, 1.0); map_node.location = (-300, -400)
        map_grass_node = nodes.new('ShaderNodeMapping'); map_grass_node.inputs['Scale'].default_value = (5.0, 5.0, 1.0); map_grass_node.location = (-300, 000)
        normal_map_node = nodes.new(type='ShaderNodeNormalMap'); normal_map_node.location = (300, -1200)
        mix_mask_node = nodes.new(type='ShaderNodeMixRGB'); mix_mask_node.location = (600, 0); mix_mask_node.blend_type = 'MIX'
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (900, 0); mix_darken_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -600)

        # links
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(tex_coord_node.outputs[2], map_grass_node.inputs["Vector"])
        links.new(map_grass_node.outputs[0], grass_node.in_uv)
        links.new(map_node.outputs[0], rock1_node.in_uv)
        links.new(uv_map_node.outputs[0], mask_node.in_uv)
        links.new(uv_map_node.outputs[0], shadow_node.in_uv)
        links.new(mask_node.out_rgb, mix_mask_node.inputs[0])
        links.new(grass_node.out_rgb, mix_mask_node.inputs[1])
        links.new(rock1_node.out_rgb, mix_mask_node.inputs[2])
        links.new(mix_mask_node.outputs[0], mix_darken_node.inputs[1])
        links.new(mix_darken_node.outputs[0], bsdf.in_rgb)

        return mat

    @staticmethod
    def terr_blnd_spec_norm_5(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        c = forza_mesh.track_bin.material_sets[0].materials[material_index].pixel_shader_constants
        mat, _, bsdf, textures = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # t0, t3
        uv0_node = nodes.new("ShaderNodeUVMap")
        uv0_node.uv_map = "TEXCOORD0"

        t0_uv_node = nodes.new("ShaderNodeVectorMath")
        t0_uv_node.operation = "MULTIPLY_ADD"
        t0_uv_node.inputs["Vector_001"].default_value = (c[4], c[4], 0) # NodeSocketVector
        t0_uv_node.inputs["Vector_002"].default_value = (0, -c[4], 0)
        links.new(uv0_node.outputs["UV"], t0_uv_node.inputs["Vector"])

        t0 = textures[0] # Blend_A
        links.new(t0_uv_node.outputs["Vector"], t0.in_uv)

        t3_uv_node = nodes.new("ShaderNodeVectorMath")
        t3_uv_node.operation = "MULTIPLY_ADD"
        t3_uv_node.inputs["Vector_001"].default_value = (c[6], c[6], 0)
        t3_uv_node.inputs["Vector_002"].default_value = (0, -c[6], 0)
        links.new(uv0_node.outputs["UV"], t3_uv_node.inputs["Vector"])

        t3 = textures[3] # Blend_C
        links.new(t3_uv_node.outputs["Vector"], t3.in_uv)

        # t1, t2
        uv1_node = nodes.new("ShaderNodeUVMap")
        uv1_node.uv_map = "TEXCOORD1"

        t1_uv_node = nodes.new("ShaderNodeVectorMath")
        t1_uv_node.operation = "MULTIPLY_ADD"
        t1_uv_node.inputs["Vector_001"].default_value = (c[5], c[5], 0)
        t1_uv_node.inputs["Vector_002"].default_value = (0, -c[5], 0)
        links.new(uv1_node.outputs["UV"], t1_uv_node.inputs["Vector"])

        t1 = textures[1] # Blend_B
        links.new(t1_uv_node.outputs["Vector"], t1.in_uv)

        t2 = textures[2] # Blend_Value
        t2.nodes[0].image.colorspace_settings.name = "Non-Color"
        links.new(uv1_node.outputs["UV"], t2.in_uv)

        # t7
        uv2_node = nodes.new("ShaderNodeUVMap")
        uv2_node.uv_map = "TEXCOORD2"

        t7 = textures[7] # Light_Map
        links.new(uv2_node.outputs["UV"], t7.in_uv)

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
        diffuse_remap_node.operation = "MULTIPLY"
        diffuse_remap_node.inputs["Vector_001"].default_value = (c[0] * c[10], c[1] * c[10], c[2] * c[10])
        links.new(mix_blend_value_r_node.outputs["Vector"], diffuse_remap_node.inputs["Vector"])

        light_map_remap_node = nodes.new("ShaderNodeMix")
        light_map_remap_node.data_type = "VECTOR"
        light_map_remap_node.factor_mode = "NON_UNIFORM"
        light_map_remap_node.inputs["A"].default_value = dark_color
        light_map_remap_node.inputs["B"].default_value = light_color
        links.new(t7.out_rgb, light_map_remap_node.inputs["Factor"])

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

        diffuse_remap_node = nodes["ShaderNodeVectorMath"]
        diffuse_remap_node.inputs["Vector_001"].default_value = (1, 1, 1)

        return mat
#endregion
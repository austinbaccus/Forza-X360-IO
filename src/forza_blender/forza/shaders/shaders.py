import bpy # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.shaders.shaders_util import *

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
        generate_image_texture_nodes_for_material(forza_mesh, track_folder_path, nodes, links, material_index)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (300, 0); bsdf.inputs.get("IOR").default_value = 1.02
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)

        # link
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

        return mat
    
    @staticmethod
    def unknown(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        if "Color" in mat.node_tree.nodes[0].outputs:
            mat.node_tree.links.new(mat.node_tree.nodes[0].outputs["Color"], mat.node_tree.nodes[-2].inputs["Base Color"])
        return mat



    # basic
    @staticmethod
    def diff_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        mat.node_tree.links.new(mat.node_tree.nodes[0].outputs["Color"], mat.node_tree.nodes[-2].inputs["Base Color"])
        mat.node_tree.links.new(mat.node_tree.nodes[0].outputs["Alpha"], mat.node_tree.nodes[-2].inputs["Alpha"])
        return mat
    
    @staticmethod
    def diff_spec_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)

        # nodes
        diffuse_node = mat.node_tree.nodes[0]
        ambient_occlusion_node = mat.node_tree.nodes[1]
        out = mat.node_tree.nodes[-1]; out.location = (900, 0)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (600, 0)
        mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, -150); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -200)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.inputs["Vector"])
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.inputs["Base Color"])
        mat.node_tree.links.new(diffuse_node.outputs["Color"], mix_rgb_node.inputs[1])
        mat.node_tree.links.new(ambient_occlusion_node.outputs["Color"], mix_rgb_node.inputs[2])
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.inputs[0])

        return mat

    @staticmethod
    def diff_spec_refl(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.diff_spec_opac_refl_3(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def diff_spec_refl_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (600, 0)
        out = mat.node_tree.nodes[-1]; out.location = (900, 0)

        # nodes
        diffuse_node = mat.node_tree.nodes[2]
        ambient_occlusion_node = mat.node_tree.nodes[3]
        bsdf = mat.node_tree.nodes[-2]
        mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.inputs["Vector"])
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.inputs["Base Color"])
        mat.node_tree.links.new(diffuse_node.outputs["Color"], mix_rgb_node.inputs[1])
        mat.node_tree.links.new(ambient_occlusion_node.outputs["Color"], mix_rgb_node.inputs[2])

        return mat

    @staticmethod
    def diff_spec_refl_norm_4(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        roughness_node = nodes[0]
        diffuse_node = nodes[2]
        ambient_occlusion_node = nodes[4]
        bsdf = nodes[-2]; bsdf.location = (600, 0)
        out = nodes[-1]; out.location = (900, 0)

        # post-processing nodes
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.location = (-300, -700); uv_map_node.uv_map = "TEXCOORD2"

        # link
        links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.inputs["Vector"])
        links.new(diffuse_node.outputs["Color"], mix_rgb_node.inputs[1])
        links.new(ambient_occlusion_node.outputs["Color"], mix_rgb_node.inputs[2])
        links.new(mix_rgb_node.outputs[0], bsdf.inputs["Base Color"])
        links.new(roughness_node.outputs[0], bsdf.inputs[2])

        return mat

    @staticmethod
    def diff_spec_opac_refl_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        out = mat.node_tree.nodes[-1]; out.location = (900, 0)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (1200, 0)
        roughness_node = mat.node_tree.nodes[0]; roughness_node.image.colorspace_settings.name = 'Non-Color'
        diffuse_node = mat.node_tree.nodes[2]
        shadow_node = mat.node_tree.nodes[3]
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (600, 150); mix_darken_node.blend_type = 'DARKEN'

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], shadow_node.inputs["Vector"])
        links.new(roughness_node.outputs["Color"], bsdf.inputs["Roughness"])
        links.new(diffuse_node.outputs["Color"], mix_darken_node.inputs[1])
        links.new(shadow_node.outputs["Color"], mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.inputs[0])
        links.new(diffuse_node.outputs["Alpha"], bsdf.inputs['Alpha'])

        return mat

    @staticmethod
    def diff_spec_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (600, 0)
        out = mat.node_tree.nodes[-1]; out.location = (900, 0)

        # nodes
        diffuse_node = mat.node_tree.nodes[0]
        roughness_node = mat.node_tree.nodes[1]
        shadow_node = mat.node_tree.nodes[2]
        darken_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); darken_node.location = (300, 0); darken_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], shadow_node.inputs["Vector"])
        mat.node_tree.links.new(darken_node.outputs[0], bsdf.inputs["Base Color"])
        mat.node_tree.links.new(diffuse_node.outputs["Color"], darken_node.inputs[1])
        mat.node_tree.links.new(shadow_node.outputs["Color"], darken_node.inputs[2])
        mat.node_tree.links.new(diffuse_node.outputs["Alpha"], bsdf.inputs['Alpha'])
        mat.node_tree.links.new(roughness_node.outputs[0], bsdf.inputs[2])

        return mat  

    @staticmethod
    def diff_spec_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (600, 0)
        out = mat.node_tree.nodes[-1]; out.location = (900, 0)

        # nodes
        diffuse_node = mat.node_tree.nodes[0]
        shadow_node = mat.node_tree.nodes[2]
        mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], shadow_node.inputs["Vector"])
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.inputs["Base Color"])
        mat.node_tree.links.new(diffuse_node.outputs["Color"], mix_rgb_node.inputs[1])
        mat.node_tree.links.new(shadow_node.outputs["Color"], mix_rgb_node.inputs[2])
        mat.node_tree.links.new(diffuse_node.outputs["Alpha"], bsdf.inputs['Alpha'])

        return mat

    @staticmethod
    def chain_diff_spec_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (600, 0)
        out = mat.node_tree.nodes[-1]; out.location = (900, 0)

        # nodes
        diffuse_node = mat.node_tree.nodes[0]
        ambient_occlusion_node = mat.node_tree.nodes[2]
        mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -700)

        # link
        mat.node_tree.links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.inputs["Vector"])
        mat.node_tree.links.new(mix_rgb_node.outputs[0], bsdf.inputs["Base Color"])
        mat.node_tree.links.new(diffuse_node.outputs["Color"], mix_rgb_node.inputs[1])
        mat.node_tree.links.new(diffuse_node.outputs["Alpha"], bsdf.inputs['Alpha'])
        mat.node_tree.links.new(ambient_occlusion_node.outputs["Color"], mix_rgb_node.inputs[2])

        return mat
    


    # ocean
    @staticmethod
    def ocean_anim_norm_refl_5(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        return mat



    # road
    @staticmethod
    def road_blnd_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.road_diff_spec_ovly_blur_detailscale_2(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def road_3clr_blnd_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        
        # nodes
        asphalt_node = mat.node_tree.nodes[0]
        tiremarks_node = mat.node_tree.nodes[1]
        shadow_node = mat.node_tree.nodes[2]
        out = mat.node_tree.nodes[-1]; out.location = (900, 0)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (1200, 0)
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, 0); mix_rgb_node.inputs['Fac'].default_value = 0.8; mix_rgb_node.blend_type = 'OVERLAY'
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (600, 150); mix_darken_node.blend_type = 'DARKEN'

        # links
        links.new(asphalt_node.outputs[0], mix_rgb_node.inputs[1])
        links.new(tiremarks_node.outputs[0], mix_rgb_node.inputs[2])
        links.new(shadow_node.outputs[0], mix_darken_node.inputs[2])
        links.new(mix_rgb_node.outputs[0], mix_darken_node.inputs[1])
        links.new(mix_darken_node.outputs[0], bsdf.inputs[0])

        return mat

    @staticmethod
    def road_diff_spec_ovly_blur_detailscale_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        diffuse1_node = mat.node_tree.nodes[0]
        diffuse2_node = mat.node_tree.nodes[1]
        shadow_node = mat.node_tree.nodes[2]
        out = mat.node_tree.nodes[-1]; out.location = (1200, 0)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (900, 0)
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, -150); mix_rgb_node.inputs['Fac'].default_value = .8; mix_rgb_node.blend_type = 'OVERLAY'
        map_node = nodes.new('ShaderNodeMapping')#; map_node.inputs['Scale'].default_value = (4.0, 4.0, 1.0); map_node.location = (-900, -300)
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord'); tex_coord_node.location = (-1200, -300)
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (600, 150); mix_darken_node.blend_type = 'DARKEN'

        # links
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(map_node.outputs[0], diffuse1_node.inputs["Vector"])
        links.new(diffuse1_node.outputs["Color"], mix_rgb_node.inputs[1])
        links.new(diffuse2_node.outputs["Color"], mix_rgb_node.inputs[2])
        links.new(mix_rgb_node.outputs[0], mix_darken_node.inputs[1])
        links.new(shadow_node.outputs[0], mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.inputs[0])

        return mat

    @staticmethod
    def road_diff_spec_ovly_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        diffuse1_node = mat.node_tree.nodes[0]
        diffuse2_node = mat.node_tree.nodes[1]
        shadow_node = mat.node_tree.nodes[2]
        out = mat.node_tree.nodes[-1]; out.location = (1200, 0)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (900, 0)
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (300, -150); mix_rgb_node.inputs['Fac'].default_value = .8; mix_rgb_node.blend_type = 'OVERLAY'
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (600, 150); mix_darken_node.blend_type = 'DARKEN'
        map_node = nodes.new('ShaderNodeMapping')#; map_node.inputs['Scale'].default_value = (4.0, 4.0, 1.0); map_node.location = (-900, -300)
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord'); tex_coord_node.location = (-1200, -300)
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -600)

        # links
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(map_node.outputs[0], diffuse1_node.inputs["Vector"])
        links.new(uv_map_node.outputs[0], shadow_node.inputs[0])

        links.new(diffuse1_node.outputs["Color"], mix_rgb_node.inputs[1])
        links.new(diffuse2_node.outputs["Color"], mix_rgb_node.inputs[2])
        links.new(mix_rgb_node.outputs[0], mix_darken_node.inputs[1])
        links.new(shadow_node.outputs[0], mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.inputs[0])

        return mat
    
    @staticmethod
    def rdline_diff_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        out = mat.node_tree.nodes[-1]; out.location = (1200, 0)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (900, 0)
        diffuse_node = mat.node_tree.nodes[0]
        shadow_node = mat.node_tree.nodes[0]
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (600, 150); mix_darken_node.blend_type = 'DARKEN'

        # links
        links.new(diffuse_node.outputs["Alpha"], bsdf.inputs['Alpha'])
        links.new(diffuse_node.outputs["Color"], mix_darken_node.inputs[1])
        links.new(shadow_node.outputs["Color"], mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.inputs[0])
        
        return mat

    @staticmethod
    def rdline_diff_opac_clipped_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        out = mat.node_tree.nodes[-1]; out.location = (1200, 0)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (900, 0)
        diffuse_node = mat.node_tree.nodes[0]
        shadow_node = mat.node_tree.nodes[0]
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (600, 150); mix_darken_node.blend_type = 'DARKEN'

        # links
        links.new(diffuse_node.outputs["Alpha"], bsdf.inputs['Alpha'])
        links.new(diffuse_node.outputs["Color"], mix_darken_node.inputs[1])
        links.new(shadow_node.outputs["Color"], mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.inputs[0])
        
        return mat

    @staticmethod
    def shldr_diff_spec_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links

        # nodes
        out = mat.node_tree.nodes[-1]; out.location = (1200, 0)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (900, 0)
        diffuse_node = mat.node_tree.nodes[0]
        shadow_node = mat.node_tree.nodes[0]
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (600, 150); mix_darken_node.blend_type = 'DARKEN'

        # links
        links.new(diffuse_node.outputs["Alpha"], bsdf.inputs['Alpha'])
        links.new(diffuse_node.outputs["Color"], mix_darken_node.inputs[1])
        links.new(shadow_node.outputs["Color"], mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.inputs[0])

        return mat



    # vegetation
    @staticmethod
    def bush_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        mat.node_tree.nodes[0].image.alpha_mode = 'STRAIGHT'
        
        # links
        mat.node_tree.links.new(mat.node_tree.nodes[0].outputs["Color"], mat.node_tree.nodes[-2].inputs["Base Color"])
        mat.node_tree.links.new(mat.node_tree.nodes[0].outputs["Alpha"], mat.node_tree.nodes[-2].inputs["Alpha"])

        return mat

    @staticmethod
    def tree_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def tree_diff_opac_vclr_2_2sd_notanfade(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)

    @staticmethod
    def grass_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        return Shaders.bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name, material_index)



    # terrain
    @staticmethod
    def diff_opac_clampv_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        mat.node_tree.nodes[0].image.alpha_mode = 'STRAIGHT'
        
        # links
        mat.node_tree.links.new(mat.node_tree.nodes[0].outputs["Color"], mat.node_tree.nodes[-2].inputs["Base Color"])
        mat.node_tree.links.new(mat.node_tree.nodes[0].outputs["Alpha"], mat.node_tree.nodes[-2].inputs["Alpha"])

        return mat

    @staticmethod
    def terr_2_blnd_spec_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (1200, 0)
        out = mat.node_tree.nodes[-1]; out.location = (1500, 0)

        # nodes
        grass_node = nodes[0]
        rock1_node = nodes[1]
        mask_node = nodes[2]; mask_node.image.colorspace_settings.name = 'Non-Color'
        ambient_occlusion_node = nodes[3]
        
        uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -900)
        links.new(uv_map_node.outputs[0], ambient_occlusion_node.inputs[0])

        uv_map_node_2 = nodes.new('ShaderNodeUVMap'); uv_map_node_2.uv_map = "TEXCOORD2"; uv_map_node_2.location = (-300, -700)
        links.new(uv_map_node_2.outputs[0], mask_node.inputs[0])

        # post-diffuse nodes
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord'); tex_coord_node.location = (-600, -200)
        map_node = nodes.new('ShaderNodeMapping'); map_node.inputs['Scale'].default_value = (2.5, 2.5, 1.0); map_node.location = (-300, -400)
        map_grass_node = nodes.new('ShaderNodeMapping'); map_grass_node.inputs['Scale'].default_value = (5.0, 5.0, 1.0); map_grass_node.location = (-300, 000)
        separate_colors_node = nodes.new('ShaderNodeSeparateColor'); separate_colors_node.location = (300, -600)
        normal_map_node = nodes.new(type='ShaderNodeNormalMap'); normal_map_node.location = (300, -1500)
        mix_mask_node = nodes.new(type='ShaderNodeMixRGB'); mix_mask_node.location = (600, 0); mix_mask_node.blend_type = 'MIX'
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (900, 0); mix_darken_node.blend_type = 'DARKEN'

        # links
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(tex_coord_node.outputs[2], map_grass_node.inputs["Vector"])
        links.new(map_grass_node.outputs[0], grass_node.inputs["Vector"])
        links.new(map_node.outputs[0], rock1_node.inputs["Vector"])
        links.new(grass_node.outputs[0], mix_mask_node.inputs[1])
        links.new(rock1_node.outputs[0], mix_mask_node.inputs[2])
        links.new(mask_node.outputs[0], separate_colors_node.inputs[0])
        links.new(separate_colors_node.outputs[1], mix_mask_node.inputs[0])
        links.new(mix_mask_node.outputs[0], mix_darken_node.inputs[1])
        links.new(ambient_occlusion_node.outputs[0], mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.inputs[0])

        return mat

    @staticmethod
    def terr_blnd_spec_norm_5(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str, material_index: int):
        mat = Shaders.base(forza_mesh, path_last_texture_folder, shader_name, material_index)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        image_node_count = len(forza_mesh.textures)
        bsdf = mat.node_tree.nodes[-2]; bsdf.location = (1200, 0)
        out = mat.node_tree.nodes[-1]; out.location = (1500, 0)

        # nodes
        grass_node = nodes[0]
        rock1_node = nodes[1]
        mask_node = nodes[2]; mask_node.image.colorspace_settings.name = 'Non-Color'
        if image_node_count > 4: normal_node = nodes[4]
        if image_node_count > 5: amb_occlusion_node = nodes[5]

        # post-diffuse nodes
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord'); tex_coord_node.location = (-600, -200)
        map_node = nodes.new('ShaderNodeMapping'); map_node.inputs['Scale'].default_value = (2.5, 2.5, 1.0); map_node.location = (-300, -400)
        map_grass_node = nodes.new('ShaderNodeMapping'); map_grass_node.inputs['Scale'].default_value = (5.0, 5.0, 1.0); map_grass_node.location = (-300, 000)
        separate_colors_node = nodes.new('ShaderNodeSeparateColor'); separate_colors_node.location = (300, -600)
        normal_map_node = nodes.new(type='ShaderNodeNormalMap'); normal_map_node.location = (300, -1200)
        mix_mask_node = nodes.new(type='ShaderNodeMixRGB'); mix_mask_node.location = (600, 0); mix_mask_node.blend_type = 'MIX'
        mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (900, 0); mix_darken_node.blend_type = 'DARKEN'
        uv_map_node = mat.node_tree.nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "TEXCOORD2"; uv_map_node.location = (-300, -600)

        # links
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(tex_coord_node.outputs[2], map_grass_node.inputs["Vector"])
        links.new(map_grass_node.outputs[0], grass_node.inputs["Vector"])
        links.new(map_node.outputs[0], rock1_node.inputs["Vector"])
        links.new(uv_map_node.outputs[0], mask_node.inputs["Vector"])
        if image_node_count > 4:
            links.new(map_node.outputs[0], normal_node.inputs["Vector"])
            links.new(normal_node.outputs[0], normal_map_node.inputs["Color"])
            links.new(normal_map_node.outputs[0], bsdf.inputs["Normal"])
        links.new(grass_node.outputs[0], mix_mask_node.inputs[1])
        links.new(rock1_node.outputs[0], mix_mask_node.inputs[2])
        links.new(mask_node.outputs[0], separate_colors_node.inputs[0])
        links.new(separate_colors_node.outputs[1], mix_mask_node.inputs[0])
        links.new(mix_mask_node.outputs[0], mix_darken_node.inputs[1])
        if image_node_count > 5: links.new(amb_occlusion_node.outputs[0], mix_darken_node.inputs[2])
        links.new(mix_darken_node.outputs[0], bsdf.inputs[0])

        return mat

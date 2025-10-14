import bpy # type: ignore
from pathlib import Path
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.models.read_rmbbin import RmbBin
from forza_blender.forza.pvs.pvs_util import BinaryStream
from forza_blender.forza.pvs.read_pvs import PVS
from forza_blender.forza.shaders.read_shader import FXLShader

def generate_meshes_from_pvs_model_instance(pvs_model_instance, pvs, rmbbin_files, shaders, context):
    try:
        if not context.scene.generate_lods and (pvs_model_instance.flags & (1 << 11)) == 0 and (pvs_model_instance.flags & (6 << 11)) != 0:
            return None

        pvs_model = pvs.models[pvs_model_instance.model_index]
        pvs_texture_filenames = []
        for texture_idx in pvs_model.textures:
            pvs_texture_filenames.append(pvs.textures[texture_idx])

        # TODO: check if all textures for a track section are being passed to the track subsection

        path_to_rmbbin = rmbbin_files[pvs_model_instance.model_index]
        pvs_model_meshes = generate_meshes_from_rmbbin(path_to_rmbbin, context, pvs_model_instance.transform, pvs_texture_filenames, shaders)
        return pvs_model_meshes
    except:
        print("Problem getting mesh from model index", pvs_model_instance.model_index)

def generate_meshes_from_pvs(path_bin, path_ribbon_pvs, context):
    rmbbin_files = get_rmbbin_files(path_bin)
    pvs: PVS = PVS.from_stream(BinaryStream.from_path(path_ribbon_pvs.resolve(), ">"))
    shaders: dict[str, FXLShader] = get_shaders(path_bin, pvs)

    instance_meshes = []

    i = 0
    for pvs_model_instance in pvs.models_instances:
        try:
            if not context.scene.generate_lods and (pvs_model_instance.flags & (1 << 11)) == 0 and (pvs_model_instance.flags & (6 << 11)) != 0:
                continue

            pvs_model = pvs.models[pvs_model_instance.model_index]
            pvs_texture_filenames = []
            for texture_idx in pvs_model.textures:
                pvs_texture_filenames.append(pvs.textures[texture_idx])

            # TODO: check if all textures for a track section are being passed to the track subsection

            path_to_rmbbin = rmbbin_files[pvs_model_instance.model_index]
            pvs_model_meshes = generate_meshes_from_rmbbin(path_to_rmbbin, context, pvs_model_instance.transform, pvs_texture_filenames, shaders)
            instance_meshes.extend(pvs_model_meshes)
        except:
            print("Problem getting mesh from model index", pvs_model_instance.model_index)
        
        i = i + 1
        print(f"[{i}/{len(pvs.models_instances)}] meshes imported")
        bpy.context.workspace.status_text_set(f"[{i}/{len(pvs.models_instances)}] meshes imported")
        
    return instance_meshes

def generate_meshes_from_rmbbin(path_trackbin: Path, context, transform, textures, shaders: dict[str, FXLShader]):
    track_bin: RmbBin = RmbBin.from_path(path_trackbin)
    rmbbin_meshes = []

    # assume that all submeshes have the same vertex buffer layout, even if they have different shaders
    for track_section in track_bin.track_sections:
        # track_section_num track_section_name track_subsection_name
        meshName: str = path_trackbin.name.split('.')[1] + " " + track_section.name + " " + track_section.subsections[0].name
        # TODO: replace with proper shader selection based on .pvs file
        fx_index = track_bin.material_sets[0].materials[track_section.subsections[0].material_index].fx_filename_index
        vertices, faces, material_indexes = track_section.generate_vertices(shaders[track_bin.shader_filenames[fx_index]].vdecl.elements)
        forza_mesh = ForzaMesh(meshName, track_section.subsections[0].name, faces, vertices, material_indexes, track_bin, track_section, transform=transform, model_index=int(path_trackbin.name.split('.')[1]), textures=textures, shader_filenames=track_bin.shader_filenames)
        rmbbin_meshes.append(forza_mesh)

    return rmbbin_meshes

def get_rmbbin_files(path_bin):
    rmbbin_files = {}
    for path_rmbbin in path_bin.glob("*.rmb.bin"):
        if path_rmbbin.name.endswith(".sky.rmb.bin"):
            continue # ignore for now - this has special logic
        else:
            rmbbin_index = int(str(path_rmbbin.name).split('.')[1])
            rmbbin_files[rmbbin_index] = path_rmbbin
    return rmbbin_files

def get_shaders(path_bin,pvs):
    shaders: dict[str, FXLShader] = {}
    for shader_relative_path in pvs.shaders:
        path = path_bin / (shader_relative_path + ".fxobj")
        # TODO: replace dict of paths with proper command buffer indexing
        shaders[shader_relative_path + ".fx"] = FXLShader.from_stream(BinaryStream.from_path(path, ">"))
    return shaders
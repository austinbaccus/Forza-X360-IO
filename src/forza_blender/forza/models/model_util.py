import bpy # type: ignore
from pathlib import Path
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.models.read_rmbbin import RmbBin
from forza_blender.forza.pvs.pvs_util import BinaryStream
from forza_blender.forza.pvs.read_pvs import PVS, PVSTexture
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
    pvs: PVS = PVS.from_stream(BinaryStream.from_path(path_ribbon_pvs.resolve(), ">"))
    shaders: dict[str, FXLShader] = get_shaders(path_bin, pvs)

    pvs_model_instances = [model_instance for model_instance in pvs.models_instances if context.scene.generate_lods or (model_instance.flags & (6 << 11)) == 0 or (model_instance.flags & (1 << 11)) != 0]
    pvs_model_instances.extend([model_instance for model_instance in pvs.lone_models_instances])

    unique_model_indexes = set([model_instance.model_index for model_instance in pvs_model_instances])
    models_to_load = [(model_index, pvs.models[model_index], F"{model_index:05d}") for model_index in unique_model_indexes]
    model_meshes: list[list[ForzaMesh] | None] = [None] * len(pvs.models)

    if pvs.sky_model is not None:
        pvs.sky_model_instance.model_index = len(model_meshes)
        pvs_model_instances.append(pvs.sky_model_instance)
        models_to_load.append((pvs.sky_model_instance.model_index, pvs.sky_model, "sky"))
        model_meshes.append(None)

    for i, (model_index, pvs_model, model_filename) in enumerate(models_to_load):
        pvs_texture_filenames = [pvs.textures[texture_idx] for texture_idx in pvs_model.textures]

        # TODO: check if all textures for a track section are being passed to the track subsection

        path_to_rmbbin = path_bin / F"{pvs.prefix}.{model_filename}.rmb.bin"
        try:
            model_meshes[model_index] = generate_meshes_from_rmbbin(path_to_rmbbin, context, pvs_texture_filenames, shaders)
        except:
            print("Problem getting mesh from model index", model_index)

        if (i + 1) % 100 == 0:
            print(f"[{i + 1}/{len(models_to_load)}] meshes imported")
            bpy.context.workspace.status_text_set(f"[{i + 1}/{len(models_to_load)}] meshes imported")

    return pvs, pvs_model_instances, models_to_load, model_meshes

def generate_meshes_from_rmbbin(path_trackbin: Path, context, textures: list[tuple[PVSTexture, int, bool]], shaders: dict[str, FXLShader], inherited_textures: list[int]):
    track_bin: RmbBin = RmbBin.from_path(path_trackbin)
    rmbbin_meshes: list[ForzaMesh] = []

    # assume that all submeshes have the same vertex buffer layout, even if they have different shaders
    for track_section in track_bin.track_sections:
        # track_section_num track_section_name track_subsection_name
        meshName: str = path_trackbin.name.split('.')[1] + " " + track_section.name + " " + track_section.subsections[0].name
        # TODO: replace with proper shader selection based on .pvs file
        fx_index = track_bin.material_sets[0].materials[track_section.subsections[0].material_index].fx_filename_index
        vertices, faces, material_indexes = track_section.generate_vertices(shaders[track_bin.shader_filenames[fx_index]].vdecl.elements)
        forza_mesh = ForzaMesh(meshName, track_section.subsections[0].name, faces, vertices, material_indexes, track_bin, track_section, textures, track_bin.shader_filenames, inherited_textures)
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
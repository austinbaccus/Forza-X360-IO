from pathlib import Path
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.models.read_rmbbin import RmbBin
from forza_blender.forza.pvs.pvs_util import BinaryStream
from forza_blender.forza.pvs.read_pvs import PVS

def generate_meshes_from_pvs(path_bin, path_ribbon_pvs, context) -> list[ForzaMesh]:
    rmbbin_files = {}
    for path_rmbbin in path_bin.glob("*.rmb.bin"):
        if path_rmbbin.name.endswith(".sky.rmb.bin"):
            continue # ignore for now - this has special logic
        else:
            rmbbin_index = int(str(path_rmbbin.name).split('.')[1])
            rmbbin_files[rmbbin_index] = path_rmbbin

    instance_meshes = []
    pvs: PVS = PVS.from_stream(BinaryStream.from_path(path_ribbon_pvs.resolve(), ">"))

    i = 0
    for pvs_model_instance in pvs.models_instances:
        try:
            if pvs_model_instance.model_index == 826:
                # new york statue
                print()

            pvs_model = pvs.models[pvs_model_instance.model_index]
            pvs_texture_filenames = []
            for texture_idx in pvs_model.textures:
                pvs_texture_filenames.append(pvs.textures[texture_idx]) # this may be in decimal or hex, not sure yet

            # TODO: check if all textures for a track section are being passed to the track subsection

            path_to_rmbbin = rmbbin_files[pvs_model_instance.model_index]
            pvs_model_meshes = generate_meshes_from_rmbbin(path_to_rmbbin, context, pvs_model_instance.transform, pvs_texture_filenames)
            instance_meshes.extend(pvs_model_meshes)
        except:
            print("Problem getting mesh from model index", pvs_model_instance.model_index)
        
        i = i + 1
        print(f"[{i}/{len(pvs.models_instances)}] meshes imported")
        
    return instance_meshes

def generate_meshes_from_rmbbin(path_trackbin: Path, context, transform, textures):
    track_bin = RmbBin(path_trackbin)
    rmbbin_meshes = []
    track_bin.populate_objects_from_rmbbin()

    if track_bin.forza_version.name != context.scene.forza_selection:
        raise RuntimeError("Forza version mismatch!")
    for track_section in track_bin.track_sections:
        # track_section_num track_section_name track_subsection_name
        meshName: str = path_trackbin.name.split('.')[1] + " " + track_section.name + " " + track_section.subsections[0].name
        vertices, faces = track_section.generate_vertices()
        forza_mesh = ForzaMesh(meshName, track_section.subsections[0].name, faces, vertices, transform=transform, model_index=int(path_trackbin.name.split('.')[1]), textures=textures, shader_filenames=track_bin.shader_filenames)
        rmbbin_meshes.append(forza_mesh)

    return rmbbin_meshes
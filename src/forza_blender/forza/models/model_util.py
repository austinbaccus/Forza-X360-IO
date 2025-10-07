from pathlib import Path
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.models.read_rmbbin import RmbBin
from forza_blender.forza.pvs.pvs_util import BinaryStream
from forza_blender.forza.pvs.read_pvs import PVS

def generate_meshes_from_rmbbin(path_trackbin: Path, context, transform, textures):
    track_bin = RmbBin(path_trackbin)
    rmbbin_meshes = []
    track_bin.populate_objects_from_rmbbin()

    if track_bin.forza_version.name != context.scene.forza_selection:
        raise RuntimeError("Forza version mismatch!")
    for track_section in track_bin.track_sections:
        for track_subsection in track_section.subsections:
            meshName: str = path_trackbin.name.split('.')[1] + " " + track_section.name + " " + track_subsection.name
            forza_mesh = ForzaMesh(meshName, track_subsection.name, track_subsection.indices, track_subsection.vertices, transform=transform, model_index=int(path_trackbin.name.split('.')[1]), textures=textures)
            rmbbin_meshes.append(forza_mesh)

    return rmbbin_meshes

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
            pvs_model = pvs.models[pvs_model_instance.model_index]
            pvs_texture_filenames = []
            for texture_idx in pvs_model.textures:
                pvs_texture_filenames.append(pvs.textures[texture_idx]) # this may be in decimal or hex, not sure yet


            path_to_rmbbin = rmbbin_files[pvs_model_instance.model_index]
            pvs_model_meshes = generate_meshes_from_rmbbin(path_to_rmbbin, context, pvs_model_instance.transform, pvs_texture_filenames)
            instance_meshes.extend(pvs_model_meshes)
        except:
            print("Problem getting mesh from model index", pvs_model_instance.model_index)
        
        i = i + 1
        print(f"[{i}/{len(pvs.models_instances)}]")
        
    return instance_meshes
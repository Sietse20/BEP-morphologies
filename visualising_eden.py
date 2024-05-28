import eden_simulator
import trimesh


def visualise(file):
    cell_info = eden_simulator.experimental.explain_cell(file)[file.split('/')[-1].split('_')[0]]

    viz = trimesh.Trimesh(vertices=cell_info['mesh_vertices'],
                          faces=cell_info['mesh_faces'])

    viz.visual.face_colors = (0.1, 0.9, 0.1)
    viz.show()


file = "NML_files_working/GGN_20170309_sc_converted.cell.nml"
visualise(file)
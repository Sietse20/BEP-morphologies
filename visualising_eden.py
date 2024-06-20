import eden_simulator
import trimesh


def visualise(file):
    cell_dict = eden_simulator.experimental.explain_cell(file)
    cell_info = cell_dict[list(cell_dict.keys())[0]]
    print(cell_info.keys())
    viz = trimesh.Trimesh(vertices=cell_info['mesh_vertices']/10,
                          faces=cell_info['mesh_faces'])

    viz.visual.face_colors = (0.1, 0.9, 0.1)
    viz.show()


file = "oi28rpy1_1_converted.cell.nml"
visualise(file)

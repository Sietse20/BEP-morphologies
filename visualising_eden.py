import eden_simulator
import trimesh


def visualise(file):
    cell_info = eden_simulator.experimental.explain_cell(file)[file.split('/')[-1].split('_')[0]]
    print(cell_info.keys())
    viz = trimesh.Trimesh(vertices=cell_info['mesh_vertices'],
                          faces=cell_info['mesh_faces'])

    viz.visual.face_colors = (0.1, 0.9, 0.1)
    viz.show()


file = "NML_files_working/STRESS_1_N5_1_CNG_converted.cell.nml"
visualise(file)

# The total area of this neuron is: 442970.51466962165
# The total volume of this neuron is: 425285.584402701

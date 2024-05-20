import eden_simulator
import trimesh

cell_info = eden_simulator.experimental.explain_cell('map_nml_files/neuron_1_converted.cell.nml')['neuron']
print(cell_info)

viz = trimesh.Trimesh(
    vertices=cell_info['mesh_vertices'],
    faces=cell_info['mesh_faces'],
)
viz.visual.face_colors = (0.1,0.9,0.1)
viz.show()
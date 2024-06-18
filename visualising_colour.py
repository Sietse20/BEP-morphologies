import neuroml.loaders as loaders
import numpy as np
import trimesh
import eden_simulator


def get_segments_from_group(nml_doc, group_id, visited_groups=None):
    if visited_groups is None:
        visited_groups = set()
    
    segment_ids = set()
    
    group = next((g for g in nml_doc.cells[0].morphology.segment_groups if g.id == group_id), None)
    if group is None or group_id in visited_groups:
        return segment_ids
    
    visited_groups.add(group_id)
    
    for member in group.members:
        segment_ids.add(member.segments)
    
    for include in group.includes:
        included_group_id = include.segment_groups
        segment_ids.update(get_segments_from_group(nml_doc, included_group_id, visited_groups))
    
    return segment_ids

def get_all_segments_by_primary_group(neuroml_file):
    nml_doc = loaders.NeuroMLLoader.load(neuroml_file)
    primary_segments_by_group = {}
    predefined_primary_group_ids = {
        'soma_group',
        'axon_group',
        'dendrite_group',
        'basal_group',
        'apical_group'
    }
    
    for cell in nml_doc.cells:
        for segment_group in cell.morphology.segment_groups:
            group_id = segment_group.id
            if group_id in predefined_primary_group_ids or any(include.segment_groups in predefined_primary_group_ids for include in segment_group.includes):
                if group_id not in primary_segments_by_group:
                    primary_segments_by_group[group_id] = set()
                primary_segments_by_group[group_id].update(get_segments_from_group(nml_doc, group_id))
            elif group_id.endswith('_group') and all(include.segment_groups not in predefined_primary_group_ids for include in segment_group.includes):
                if group_id not in primary_segments_by_group:
                    primary_segments_by_group[group_id] = set()
                primary_segments_by_group[group_id].update(get_segments_from_group(nml_doc, group_id))
    
    return {key: list(value) for key, value in primary_segments_by_group.items()}

def generate_unique_color(seed):
    """
    Generate a unique color based on a seed value.
    """
    np.random.seed((seed) % (2**32))
    return np.random.randint(0, 256, size=3)

def visualise(file):
    cell_dict = eden_simulator.experimental.explain_cell(file)
    cell_info = cell_dict[list(cell_dict.keys())[0]]
    
    # Define colors for each primary segment group
    segment_group_colors = {
        'soma_group': (255, 0, 0),
        'axon_group': (0, 255, 0),
        'dendrite_group': (0, 0, 255),
        'basal_group': (255, 255, 0),
        'apical_group': (255, 0, 255)
    }
    
    # Load the NeuroML file and get primary segments by group
    primary_segments_by_group = get_all_segments_by_primary_group(file)
    
    # Assign unique colors to custom groups
    for group_id in primary_segments_by_group:
        if group_id not in segment_group_colors:
            segment_group_colors[group_id] = generate_unique_color(hash(group_id))
    
    # Create a face color array with default color (e.g., white)
    face_colors = np.ones((len(cell_info['mesh_faces']), 4), dtype=np.uint8) * 255
    
    # Color the faces based on their corresponding segment group
    for group_id, segment_ids in primary_segments_by_group.items():
        color = segment_group_colors.get(group_id, (0, 0, 0))  # Default to black if not found
        for segment_id in segment_ids:
            faces = [i for i, comp in enumerate(cell_info['mesh_comp_per_face']) if comp == segment_id]
            for face in faces:
                face_colors[face][:3] = color  # Set RGB color
                face_colors[face][3] = 255  # Set alpha to fully opaque
    
    # Create the trimesh object and assign face colors
    viz = trimesh.Trimesh(vertices=cell_info['mesh_vertices'],
                          faces=cell_info['mesh_faces'])
    viz.visual.face_colors = face_colors
    viz.show()

# Example usage
file = 'Case1_new_converted.cell.nml'
visualise(file)

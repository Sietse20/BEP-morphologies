import eden_simulator
import numpy as np
from eden_simulator.display.spatial import k3d as ek3d      # added in version 4


def generate_unique_color(seed):
    """
    Generate a unique color based on a seed value.
    """
    np.random.seed((seed) % (2**32))
    return np.random.randint(0, 256, size=3)


def visualize_compartments(file):
    cell_dict = eden_simulator.experimental.explain_cell(file)
    cell_info = cell_dict[list(cell_dict.keys())[0]]
    nCellComps = len(cell_info['comp_midpoint'])

    rng = np.random.default_rng(seed=20240901)
    comp_colors = rng.random([nCellComps, 3])

    plot = ek3d.Plot(grid_visible=False, menu_visibility=False, camera_auto_fit=True)
    plot += ek3d.plot_neuron(cell_info, comp_colors)
    html = plot.get_snapshot()

    with open("neuron.html", "w", encoding="utf-8") as f:
        f.write(html)


def visualize_groups(file):
    cell_dict = eden_simulator.experimental.explain_cell(file)
    cell_info = cell_dict[list(cell_dict.keys())[0]]
    comp_colors = []
    segment_group_colors = {
        'soma_group': (255, 0, 0),
        'axon_group': (0, 255, 0),
        'dendrite_group': (0, 0, 255),
        'basal_group': (255, 255, 0),
        'apical_group': (255, 0, 255)
    }

    for group_id in cell_info['segment_groups']:         # added in version 4
        if group_id not in segment_group_colors:
            segment_group_colors[group_id] = generate_unique_color(hash(group_id))

    for group_name, color in segment_group_colors.items():
        comps_in_group = cell_info['segment_groups'][group_name]['comps']
        comp_colors[comps_in_group] = color

    # Show the neuron:
    plot = ek3d.Plot(grid_visible=False, menu_visibility=False)
    plot += ek3d.plot_neuron(cell_info, comp_colors)

    # And add some annotations.
    for i, (_, color, description) in enumerate(segment_group_colors):
        plot += k3d.text2d(description, (0,0.9-0.15*i), color=ek3d.RgbToInt(color),
                        is_html=True, label_box=False, size=2.5)

    plot.show_html("neuron.html")


if __name__ == "__main__":
    file = "nml_random/Cell_500_MPD_8_FT_10_XYZ_Sorted-swc_N3DFix-swc_pruned_converted.cell.nml"
    visualize_compartments(file)

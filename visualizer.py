import eden_simulator
import numpy as np
from eden_simulator.display.spatial import k3d as ek3d      # added in version 4
import k3d


def generate_unique_color(seed):
    np.random.seed(seed % (2**32))
    return np.random.random(size=3)  


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
    nCellComps = len(cell_info['comp_midpoint'])
    comp_colors = np.zeros((nCellComps, 3), dtype=np.float64)  # float, not uint8

    segment_group_colors = {
    'axon_group':       (0.0, 1.0, 0.0),   # green
    'dendrite_group':   (0.0, 0.0, 1.0),   # blue
    'basal_group':      (0.0, 0.5, 1.0),   # cyan-blue
    'apical_group':     (1.0, 0.0, 1.0),   # magenta
    'soma_group':       (1.0, 0.0, 0.0)    # red
    }

    SKIP_GROUPS = {'all'}

    for group_id in cell_info['segment_groups']:
        if group_id not in segment_group_colors and group_id not in SKIP_GROUPS:
            segment_group_colors[group_id] = generate_unique_color(hash(group_id))

    for group_name, color in segment_group_colors.items():
        if group_name not in cell_info['segment_groups']:  # skip absent groups
            continue
        comps_in_group = cell_info['segment_groups'][group_name]['comps']
        comp_colors[comps_in_group] = color

    soma_comps = cell_info['segment_groups']['soma_group']['comps']
    comp_colors[soma_comps] = (1.0, 0.0, 0.0)

    # Show the neuron:
    plot = ek3d.Plot(grid_visible=False, menu_visibility=False)
    plot += ek3d.plot_neuron(cell_info, comp_colors)

    # And add some annotations.
    for i, (group_name, color) in enumerate(segment_group_colors.items()):
        plot += k3d.text2d(group_name, (0,0.9-0.15*i), color=ek3d.RgbToInt(color),
                        is_html=True, label_box=False, size=2.5)

    html = plot.get_snapshot()
    with open("neuron.html", "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    file = "1028ir2x-40x-NL_converted.cell.nml"
    visualize_compartments(file)

import neuroml
import neuroml.writers as writers
import re
import os
import io


'''

BEFORE USING THIS PROGRAM

This program offers the following functionalities:
1. Converts a single SWC file.
2. Converts multiple SWC files from a specified directory.
3. Converts SWC files from neuromorpho.org using their API.
At the bottom of the file, you can choose which functionality to use by uncommenting the relevant section and leaving the others commented out.

You can find a detailed explanatory Jupyter Notebook in my GitHub repository: https://github.com/Sietse20/BEP-morphologies.
Search for the file 'converter_notebook.ipynb'.

If you have any questions about the code, feel free to contact me at s.reissenweber12@gmail.com.

'''


def construct_nml(input_data, output_dir=''):
    '''
    This function is the big function that calls all helper functions to construct the neuroml file.

    Input: - input_data: filepath to SWC file (str) or SWC data from API (tuple[filename (str), SWC data (bytes)])
           - output_dir (optional): directory in which the neuroml file will be saved (str)

    Returns: - name of the newly created neuroml file (str)
             - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}
    '''

    errors = {}

    # Extract input_data (tuple means API)
    if isinstance(input_data, tuple):
        filename = input_data[0]
        input = input_data[1]
    else:
        filename = os.path.basename(input_data).split('.')[0]
        input = input_data

    filename = change_filename(filename, errors)
    cell_ID = f"{filename}_cell"
    nml_doc = neuroml.NeuroMLDocument(id=filename)
    nml_cell = neuroml.Cell(id=cell_ID)

    d, comments = open_and_split(input, errors)
    make_notes(comments, nml_cell)
    n, children, type_seg, root = classify_types_branches_and_leafs(d, errors)
    segmentGroups = find_segments(d, n)
    nml_mor = process_segments(d, children, root, cell_ID, errors)
    process_cables(segmentGroups, type_seg, nml_mor, nml_cell)
    define_biophysical_properties(nml_cell, cell_ID)

    nml_doc.cells.append(nml_cell)

    nml_file = f'{output_dir}/{filename}_converted.cell.nml' if output_dir else f'{filename}_converted.cell.nml'
    writers.NeuroMLWriter.write(nml_doc, nml_file)

    return os.path.basename(nml_file), errors


class ConversionException(Exception):
    '''
    This is an exception class used to store the errors dictionary when the SWC file is invalid and an exception is raised as a consequence.
    '''

    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors


def log_error(errors, error_type, occurrence=1, extra_info=None, fix=None, stop=False):
    '''
    This function logs errors detected in the SWC file to a dictionary and adds any additional information about the errors.

    Input: - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}
           - error_type: error message (str)
           - occurence (optional): amount of occurences (int)
           - extra_info (optional): extra information about the error (str)
           - fix (optional): measure implemented to fix the error (str)
           - stop (optional): should the conversion continue or not (bool)

    Returns: None
    '''

    # Check if error_type is related to unknown SWC types
    if error_type.startswith("Unknown type detected"):
        type_id = error_type[23:]
        if "Unknown type detected" not in errors:
            errors["Unknown type detected"] = {}

        if type_id not in errors["Unknown type detected"]:
            errors["Unknown type detected"][type_id] = {
                "occurrences": 0,
                "fix": None
            }

        errors["Unknown type detected"][type_id]["occurrences"] += occurrence
        if fix is not None:
            errors["Unknown type detected"][type_id]["fix"] = fix
    else:
        if error_type not in errors:
            errors[error_type] = {
                "occurrences": 0,
                "fix": None
            }

        errors[error_type]["occurrences"] += occurrence
        if extra_info is not None:
            if "extra_info" not in errors[error_type]:
                errors[error_type]["extra_info"] = [extra_info]
            else:
                errors[error_type]["extra_info"].append(extra_info)
        if fix is not None:
            errors[error_type]["fix"] = fix

    if stop:
        raise ConversionException(error_type, errors)


def open_and_split(input_data, errors):
    '''
    This function takes SWC data and creates a dictionary with necessary information to generate the neuroml file.

    Input: - input_data: filepath to SWC file (str) or SWC data (bytes)
           - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}

    Returns: - d: dict {point (int): (type, x_coord, y_coord, z_coord, radius, parent)}
             - comments: list of comments [comment (str)]
    '''

    d = {}
    line_nr = 0
    comments = []
    no_par = []
    invalid_lines = []
    soma_detected = False

    # Extract input_data (bytes means API)
    if isinstance(input_data, bytes):
        f = io.BytesIO(input_data)
        f = io.TextIOWrapper(f, encoding='utf-8')
    else:
        f = open(input_data, 'r+')

    with f:
        for line in f:
            line_nr += 1
            if not line:
                pass
            elif line.startswith('#') or line.startswith("*"):
                comments.append(line[1:].strip())
            else:
                information = [elem for elem in line.strip().split(' ') if elem]
                if not information:
                    pass
                else:
                    if len(information) != 7:
                        invalid_lines.append(line_nr)
                    else:
                        seg_ID = int(information[0]) - 1
                        type_ID = int(information[1])
                        x_coor = float(information[2])
                        y_coor = float(information[3])
                        z_coor = float(information[4])
                        rad = float(information[5])
                        par_ID = int(information[6]) - 1

                        if par_ID > seg_ID:
                            log_error(errors, "Parent ID referred to before being defined. Loops might be present", extra_info=f"Point {seg_ID + 1}, parent {par_ID + 1}", fix="No fixes. SWC file is invalid", stop=True)

                        if type_ID == 1:
                            soma_detected = True

                        if par_ID == -1:
                            no_par.append(str(seg_ID + 1))

                        d[seg_ID] = (type_ID, x_coor, y_coor, z_coor, rad, par_ID)

    # Check if there are invalid lines in the SWC file
    if invalid_lines:
        log_error(errors, "Line in SWC file contains an invalid amount of columns (more or less than 7)", occurrence=len(invalid_lines), extra_info=f"Lines {', '.join(map(str, invalid_lines))}", fix="Skipped these lines")

    # Check if cell has segments
    if not d:
        log_error(errors, "SWC file does not contain any segments", fix="No fixes. SWC file is invalid.", stop=True)

    # Check if cell has more than one or zero segment(s) without a parent
    if len(no_par) == 0:
        log_error(errors, "Zero segments without parent (root segments) detected", fix="No fixes. SWC file is invalid.", stop=True)
    if len(no_par) > 1:
        log_error(errors, "More than one segment without parent (root segment) detected", extra_info=f"Points {', '.join(no_par)}", fix="No fixes. SWC file is invalid.", stop=True)

    # Check if cell contains soma samples
    if not soma_detected:
        log_error(errors, "No soma segments detected", fix="No fixes.")

    return d, comments


def change_filename(filename, errors):
    '''
    This function is used to change the filename to conform to neuroml filename pattern restrictions.

    Inputs: - filename: str
            - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}

    Returns: new_name: new file name (str)
    '''

    new_name = re.sub(r'[^a-zA-Z0-9_]', '_', filename)
    if new_name[0].isdigit():
        new_name = '_' + new_name

    if new_name != filename:
        log_error(errors, "Filename does not comply with neuroml filename pattern restrictions", fix=f"Changed filename to {new_name}")

    return new_name


def make_notes(comments, nml_cell):
    '''
    This function creates the notes listed at the top of the neuroml file. It also includes the original comments listed in the SWC file.

    Input: - comments: list of comments [comment (str)]
           - nml_cell: neuroml cell object

    Returns: None
    '''

    nml_cell.notes = "\n\n" + '*' * 40 + \
                     "\nThis NeuroML file was converted from SWC to NeuroML format by Sietse Reissenweber's converter. \
                     \nFor any questions regarding the conversion, you can email me at s.reissenweber12@gmail.com. \
                     \nThe notes listed below are the notes that were originally contained in the SWC file.\n" \
                     + '*' * 40 + "\n\n"

    nml_cell.notes += "#" * 40 + "\n\n"

    for comment in comments:
        nml_cell.notes += f'{comment}\n'

    nml_cell.notes += "\n" + "#" * 40 + "\n\n"


def classify_types_branches_and_leafs(d, errors):
    '''
    This function classifies the segments into different types, and determines the children of points.

    Input: - d: dict {point (int): (type, x_coord, y_coord, z_coord, radius, parent)}
           - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}

    Returns: - n: dict {amount of children (int): [points]}
             - children: dict {point (int): [children]}
             - type_seg: dict {point (int): type morph. part (e.g. soma) (str)}
             - root: point without parent (int)
    '''

    n = {0: [],
         1: [],
         2: []}
    root = -float("Inf")
    children = {}
    type_seg = {}
    endpoints = []
    internal_points = []

    children_count = {point: 0 for point in d}

    for point, info in d.items():
        parent = info[5]
        if parent in children_count:
            children_count[parent] += 1
        else:
            children_count[parent] = 1

    for point, info in d.items():
        # Create dict n
        number_of_children = children_count[point]
        if number_of_children == 0:
            n[0].append(point)
        elif number_of_children == 1:
            n[1].append(point)
        else:
            n[2].append(point)

        # Check for 0.0 diameter:
        if info[4] <= 0.0:
            d[point] = info[:4] + (0.000001,) + (info[5],)
            if point in n[0]:
                endpoints.append(point)
            else:
                internal_points.append(point)

        # Create dicts type_seg and types:
        if info[0] == 1:
            type_seg[point] = 'soma'
        elif info[0] == 2:
            type_seg[point] = 'axon'
        elif info[0] == 3:
            type_seg[point] = 'bas_dend'
        elif info[0] == 4:
            type_seg[point] = 'ap_dend'
        else:  # Account for custom types
            type_id = f'custom_{info[0]}'
            type_seg[point] = type_id
            log_error(errors, f"Unknown type detected: {type_id}", fix=f"Added new type {type_id} and new group {type_id}_group")

        # Find root:
        if info[5] == -1:
            root = point
            if type_seg[root] != 'soma':
                log_error(errors, "Spherical root segment does not belong to soma_group", fix="No fixes.")

        children[point] = []

    # Create dict children:
    for point, info in d.items():
        if point != root:
            children[info[5]].append(point)

    # Check for endpoints with zero radius
    if endpoints:
        log_error(errors, "Endpoint of zero radius detected", occurrence=len(endpoints), extra_info=f"Points {', '.join(map(str, endpoints))}", fix=f"Changed radius to small number {0.000001}")

    # Check for internal points with zero radius
    if internal_points:
        log_error(errors, "Internal point of zero radius detected", occurrence=len(internal_points), extra_info=f"Points {', '.join(map(str, internal_points))}", fix=f"Changed radius to small number {0.000001}")

    return n, children, type_seg, root


def find_segments(d, n):
    '''
    This function organizes the segments into unbranched segment groups of the same type.

    Input: - d: dict {point (int): (type, x_coord, y_coord, z_coord, radius, parent)}
           - n: dict {amount of children (int): [points]}

    Returns: - segmentGroups: list with lists of segmentgroups [[points], [points], ...]
    '''

    segmentGroups = []

    # Processing from leaf points to branch points:
    for leaf in n[0]:
        toAdd = leaf
        group_type = d[toAdd][0]
        segGr = []
        segmentFound = False

        while segmentFound is False:
            if toAdd == -1:
                segmentFound = True
            elif toAdd in n[2]:  # Found a branch point
                segmentFound = True
            elif d[toAdd][0] != group_type:
                segmentGroups.append(segGr)
                segGr = []
                segGr.append(toAdd)
                group_type = d[toAdd][0]
                toAdd = d[toAdd][5]
            else:
                segGr.append(toAdd)
                toAdd = d[toAdd][5]

        if segGr:
            segmentGroups.append(segGr)

    # Processing from branch points to other branch points:
    for branch in n[2]:
        toAdd = branch
        group_type = d[toAdd][0]
        segGr = []
        segmentFound = False

        while segmentFound is False:
            if toAdd == -1:
                segmentFound = True
            elif toAdd in n[2] and toAdd != branch:
                segmentFound = True
            elif d[toAdd][0] != group_type:
                segmentGroups.append(segGr)
                segGr = []
                segGr.append(toAdd)
                group_type = d[toAdd][0]
                toAdd = d[toAdd][5]
            else:
                segGr.append(toAdd)
                toAdd = d[toAdd][5]

        if segGr:
            segmentGroups.append(segGr)

    return segmentGroups


def process_segments(d, children, root, Cell_ID, errors):
    '''
    This function incorporates the segments into the neuroml morphology object.

    Input: - d: dict {point (int): (type, x_coord, y_coord, z_coord, radius, parent)}
           - children: dict {point (int): [children]}
           - root: point without parent (int)
           - cell_ID: unique ID of neuroml cell (str)
           - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}

    Returns: nml_mor: neuroml morphology object
    '''

    nml_mor = neuroml.Morphology(id=f'{Cell_ID}_morphology')

    available_points = [root]
    processed = []
    all_processed = False

    while all_processed is False:
        next_to_process = min(available_points)

        if next_to_process == root:  # Set distal and proximal points to root point if root
            Soma_Root = neuroml.Point3DWithDiam(x=str(d[next_to_process][1]),
                                                y=str(d[next_to_process][2]),
                                                z=str(d[next_to_process][3]),
                                                diameter=str(d[next_to_process][4] * 2))
            distalp = Soma_Root
            proximalp = Soma_Root
        else:
            distalp = neuroml.Point3DWithDiam(x=str(d[next_to_process][1]),
                                              y=str(d[next_to_process][2]),
                                              z=str(d[next_to_process][3]),
                                              diameter=str(d[next_to_process][4] * 2))
            parent = d[next_to_process][5]
            proximalp = neuroml.Point3DWithDiam(x=str(d[parent][1]),
                                                y=str(d[parent][2]),
                                                z=str(d[parent][3]),
                                                diameter=str(d[parent][4] * 2))

        parentID = d[next_to_process][5]
        if parentID != -1:
            coord_distal = (d[next_to_process][1], d[next_to_process][2], d[next_to_process][3])
            coord_proximal = (d[parent][1], d[parent][2], d[parent][3])
            if coord_distal == coord_proximal and d[next_to_process][4] == d[parent][4]:
                log_error(errors, "Two segments detected with same radius and coordinates", extra_info=f"Segments {next_to_process} and {parent}", fix="No fixes.")

            segpar = neuroml.SegmentParent(segments=parentID)
            thisSeg = neuroml.Segment(id=str(next_to_process),
                                      name=f'Comp_{str(next_to_process)}',
                                      distal=distalp,
                                      parent=segpar)
        else:
            thisSeg = neuroml.Segment(id=str(next_to_process),
                                      name=f'Comp_{str(next_to_process)}',
                                      proximal=proximalp,
                                      distal=distalp)

        nml_mor.segments.append(thisSeg)
        processed.append(next_to_process)

        available_points.remove(next_to_process)
        available_points += children[next_to_process]
        if not available_points:
            all_processed = True

    return nml_mor


def process_cables(segmentGroups, type_seg, nml_mor, nml_cell):
    '''
    This function incorporates the segment groups into the morphology object and adds them to bigger segment groups.
    The morphology object is then added to the cell object.

    Input: - segmentGroups: list with lists of segmentgroups [[point], [point], ...]
           - type_seg: dict {point (int): type morph. part (e.g. soma) (str)}
           - nml_mor: neuroml morphology object
           - nml_cell: neuroml cell object

    Returns: None
    '''

    cables = []

    # Create main segment groups
    all_cables = neuroml.SegmentGroup(id='all')
    soma_group = neuroml.SegmentGroup(id='soma_group', neuro_lex_id='SAO:1044911821')
    axon_group = neuroml.SegmentGroup(id='axon_group', neuro_lex_id='SAO:1770195789')
    dendrite_group = neuroml.SegmentGroup(id='dendrite_group', neuro_lex_id='SAO:1211023249')
    basal_group = neuroml.SegmentGroup(id='basal_group', neuro_lex_id='SAO:1079900774')
    apical_group = neuroml.SegmentGroup(id='apical_group', neuro_lex_id='SAO:273773228')

    custom_groups = {}  # Dictionary to hold custom segment groups
    counter = {}  # Dictionary to keep track of ids of groups

    for segmentGroup in segmentGroups:
        type_cable = type_seg[segmentGroup[0]]
        if type_cable not in counter:
            counter[type_cable] = 1
        else:
            counter[type_cable] += 1
        cable_id = f'{type_cable}_{counter[type_cable]}'
        this_cable = neuroml.SegmentGroup(id=cable_id, neuro_lex_id='SAO:864921383')

        for segment in reversed(segmentGroup):
            member = neuroml.Member(segments=segment)
            this_cable.members.append(member)

        cables.append(this_cable)
        cable_include = neuroml.Include(segment_groups=cable_id)
        all_cables.includes.append(cable_include)

        if type_cable == 'soma':
            soma_group.includes.append(cable_include)
        elif type_cable == 'axon':
            axon_group.includes.append(cable_include)
        elif type_cable == 'bas_dend':
            basal_group.includes.append(cable_include)
            dendrite_group.includes.append(cable_include)
        elif type_cable == 'ap_dend':
            apical_group.includes.append(cable_include)
            dendrite_group.includes.append(cable_include)
        else:
            custom_group_id = f'{type_cable}_group'
            if custom_group_id not in custom_groups:
                custom_group = neuroml.SegmentGroup(id=custom_group_id)
                custom_groups[custom_group_id] = custom_group
            custom_groups[custom_group_id].includes.append(cable_include)

    # Append all cables and segment groups to morphology
    for cable in cables:
        nml_mor.segment_groups.append(cable)

    for type in [all_cables, soma_group, axon_group, dendrite_group, basal_group, apical_group]:
        if type.includes:
            nml_mor.segment_groups.append(type)

    for custom_group in custom_groups.values():
        nml_mor.segment_groups.append(custom_group)

    nml_cell.morphology = nml_mor


def define_biophysical_properties(nml_cell, Cell_ID):
    '''
    This function defines some basic biophysical properties for the given cell.

    Input: - nml_cell: neuroml cell object
           - Cell_ID: unique ID of neuroml cell (str)

    Returns: None
    '''

    # Create biophysical properties object
    all_props = neuroml.BiophysicalProperties(id=f'{Cell_ID}_properties')

    # Create and configure membrane properties
    membrane_props = neuroml.MembraneProperties()
    membrane_props.spike_threshes.append(neuroml.SpikeThresh(value='0.0 mV'))
    membrane_props.specific_capacitances.append(neuroml.SpecificCapacitance(value='1.0 uF_per_cm2'))
    membrane_props.init_memb_potentials.append(neuroml.InitMembPotential(value='-60.0 mV'))

    # Create and configure intracellular properties
    intra_props = neuroml.IntracellularProperties()
    intra_props.resistivities.append(neuroml.Resistivity(value='0.03 kohm_cm'))

    # Assign properties to the object
    all_props.membrane_properties = membrane_props
    all_props.intracellular_properties = intra_props

    # Assign object to cell
    nml_cell.biophysical_properties = all_props

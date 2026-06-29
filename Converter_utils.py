import neuroml
import re
import os
import io
import csv
import neuroml.writers as writers


def construct_nml(input_data, write_nml=True, output_dir=''):
    '''
    The big function that calls all helper functions to construct the neuroml file.

    Input: - input_data: filepath to SWC file (str) or SWC data from API (tuple[filename (str), SWC data (bytes)])
           - write_nml: whether to write the neuroml file (bool)
           - output_dir: directory to write the neuroml file to (str)

    Returns: - nml_file: filepath to neuroml file (str)
             - nml_doc: neuroml document object
             - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}
    '''

    errors = {}
    nml_file = None

    # Extract input_data (tuple means API)
    if isinstance(input_data, tuple):
        filename = input_data[0]
        input_swc = input_data[1]
    else:
        filename = os.path.basename(input_data).split('.')[0]
        input_swc = input_data

    nml_id = create_id(filename)
    cell_id = f"{nml_id}_cell"
    nml_doc = neuroml.NeuroMLDocument(id=nml_id)
    nml_cell = neuroml.Cell(id=cell_id)

    d, comments = open_and_split(input_swc, errors)
    make_notes(comments, nml_doc)
    n, children, type_seg, root = classify_branches(d, errors)
    segmentGroups = find_segments(d, n, root)
    nml_mor, point_to_segment = process_segments(d, children, root, cell_id, errors)
    process_compartments(segmentGroups, type_seg, nml_mor, nml_cell, point_to_segment)
    define_biophysical_properties(nml_cell, cell_id)

    nml_doc.cells.append(nml_cell)

    if write_nml:
        nml_file = write_nml_file(nml_doc, filename, output_dir=output_dir)

    return nml_file, nml_doc, errors


class ConversionException(Exception):
    '''
    Exception class used to store the errors dictionary when the SWC file is invalid and an exception is raised as a consequence.
    '''

    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors


def log_error(errors, error_type, occurrence=1, extra_info=None, fix=None, stop=False):
    '''
    Logs errors detected in the SWC file to a dictionary and adds any additional information about the errors.

    Input: - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}
           - error_type: error message (str)
           - occurence (optional): amount of occurences (int)
           - extra_info (optional): extra information about the error (str)
           - fix (optional): measure implemented to fix the error (str)
           - stop (optional): should the conversion continue or not (bool)
    '''

    # Check if error_type is related to unknown SWC structure identifiers
    if error_type.startswith("Unknown structure identifier detected"):
        type_id = error_type[39:]
        if "Unknown structure identifier detected" not in errors:
            errors["Unknown structure identifier detected"] = {}

        if type_id not in errors["Unknown structure identifier detected"]:
            errors["Unknown structure identifier detected"][type_id] = {
                "occurrences": 0,
                "fix": None
            }

        errors["Unknown structure identifier detected"][type_id]["occurrences"] += occurrence
        if fix is not None:
            errors["Unknown structure identifier detected"][type_id]["fix"] = fix
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
    Takes SWC data and creates a dictionary with necessary information to generate the neuroml file.

    Input: - input_data: filepath to SWC file (str) or SWC data (bytes)
           - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}

    Returns: - d: dict {point (int): (structure_id, x_coord, y_coord, z_coord, radius, parent)}
             - comments: list of comments [comment (str)]
    '''

    d = {}
    line_nr = 0
    comments = []
    no_par = []
    invalid_lines = []

    # Extract input_data (bytes means API)
    if isinstance(input_data, bytes):
        f = io.BytesIO(input_data)
        f = io.TextIOWrapper(f, encoding='utf-8')
    else:
        f = open(input_data, 'r')

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
                        struc_ID = int(information[1])
                        x_coor = float(information[2])
                        y_coor = float(information[3])
                        z_coor = float(information[4])
                        rad = float(information[5])
                        par_ID = int(information[6]) - 1

                        if par_ID > seg_ID:
                            log_error(errors, "Parent ID referred to before being defined. Loops might be present", extra_info=f"Point {seg_ID + 1}, parent {par_ID + 1}", fix="No fixes. SWC file is invalid", stop=True)

                        if par_ID < 0:
                            par_ID = -1
                            no_par.append(str(seg_ID + 1))

                        d[seg_ID] = (struc_ID, x_coor, y_coor, z_coor, rad, par_ID)

    # Check if there are invalid lines in the SWC file
    if invalid_lines:
        log_error(errors, "Line in SWC file contains an invalid amount of columns (more or less than 7)", occurrence=len(invalid_lines), extra_info=f"Lines {', '.join(map(str, invalid_lines))}", fix="Skipped these lines")

    # Check if file has segments
    if not d:
        log_error(errors, "SWC file does not contain any segments", fix="No fixes. SWC file is invalid.", stop=True)

    # Check if file has more than one or zero segment(s) without a parent
    if len(no_par) == 0:
        log_error(errors, "Zero segments without parent (root segments) detected", fix="No fixes. SWC file is invalid.", stop=True)
    if len(no_par) > 1:
        log_error(errors, "More than one segment without parent (root segment) detected", extra_info=f"Points {', '.join(no_par)}", fix="No fixes. SWC file is invalid.", stop=True)

    return d, comments


def create_id(filename):
    '''
    Creates an nml id from the filename to conform to neuroml pattern restrictions.

    Inputs: filename (str)

    Returns: nml_id: neuroml id (str)
    '''

    nml_id = re.sub(r'[^a-zA-Z0-9_]', '_', filename)
    if nml_id[0].isdigit():
        nml_id = '_' + nml_id

    return nml_id


def make_notes(comments, nml_doc):
    '''
    Creates the notes listed at the top of the neuroml file. 
    Includes the original comments listed in the SWC file.

    Input: - comments: list of comments [comment (str)]
           - nml_doc: neuroml document object
    '''

    nml_doc.notes = "\n\n" + '*' * 40 + \
                     "\nThis NeuroML file was converted from SWC to NeuroML format by Sietse Reissenweber's converter. \
                     \nFor any questions regarding the conversion, you can email me at s.reissenweber12@gmail.com. \
                     \nThe notes listed below are the notes that were originally contained in the SWC file.\n" \
                     + '*' * 40 + "\n\n"

    nml_doc.notes += "#" * 40 + "\n\n"

    for comment in comments:
        nml_doc.notes += f'{comment}\n'

    nml_doc.notes += "\n" + "#" * 40 + "\n\n"


def classify_branches(d, errors):
    '''
    Classifies the segments into different types of structures, and determines the children of points.

    Input: - d: dict {point (int): (struc_ID, x_coord, y_coord, z_coord, radius, parent)}
           - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}

    Returns: - n: dict {amount of children (int): [points]}
             - children: dict {point (int): [children]}
             - type_seg: dict {point (int): type morph. structure (e.g. soma) (str)}
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
            if point in n[0]:  # endpoint
                d[point] = info[:4] + (0.000001,) + (info[5],)
                endpoints.append(point)
            else:  # internal point
                # Gather radii of all attached points (parent + children)
                attached_radii = []
                if info[5] != -1 and d[info[5]][4] > 0.0:
                    attached_radii.append(d[info[5]][4])
                for child in [p for p, i in d.items() if i[5] == point]:
                    if d[child][4] > 0.0:
                        attached_radii.append(d[child][4])

                if attached_radii:
                    avg_radius = sum(attached_radii) / len(attached_radii)
                    d[point] = info[:4] + (avg_radius,) + (info[5],)
                    internal_points.append(point)
                else:
                    # All attached points also have zero radius, fall back to small number
                    d[point] = info[:4] + (0.000001,) + (info[5],)
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
        else:  # Account for custom structure identifiers
            struc_id = f'custom_{info[0]}'
            type_seg[point] = struc_id
            log_error(errors, f"Unknown structure identifier detected: {struc_id}", fix=f"Added new type {struc_id} and new group {struc_id}_group")

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
        log_error(errors, "Internal point of zero radius detected", occurrence=len(internal_points), extra_info=f"Points {', '.join(map(str, internal_points))}", fix=f"Changed radius to average of attached points' radii (or small number if all attached points also have zero radius)")

    return n, children, type_seg, root


def find_segments(d, n, root):
    '''
    Organizes the segments into unbranched segment groups of the same structural type.

    Input: - d: dict {point (int): (struc_id, x_coord, y_coord, z_coord, radius, parent)}
           - n: dict {amount of children (int): [points]}
           - root: point without parent (int)

    Returns: - segmentGroups: list with lists of segmentgroups [[points], [points], ...]
    '''

    segmentGroups = []

    # Collect all soma points as single group
    soma_group = [point for point in d if d[point][0] == 1 and point != root]
    if soma_group:
        segmentGroups.append(soma_group)


    # Processing from leaf points to branch points:
    for leaf in n[0]:
        if d[leaf][0] == 1:
            continue
        toAdd = leaf
        group_type = d[toAdd][0]
        segGr = []

        while True:
            if toAdd == -1:
                break
            elif toAdd in n[2]:  # Found a branch point
                break
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
        if d[branch][0] == 1:
            continue
        toAdd = branch
        group_type = d[toAdd][0]
        segGr = []

        while True:
            if toAdd == -1:
                break
            elif toAdd in n[2] and toAdd != branch:
                break
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


def process_segments(d, children, root, mor_id, errors):
    '''
    Converts SWC points into NeuroML segments.
    Handles: - 1 point soma: sphere
             - 3 point soma: cylinder (outer -> center -> outer)
             - N point soma: soma chain
    
    Input: - d: dict {point (int): (struc_id, x_coord, y_coord, z_coord, radius, parent)}
           - children: dict {point (int): [children]}
           - root: point without parent (int)
           - mor_id: morphology id (str)
           - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}

    Returns: - nml_mor: neuroml morphology object
             - point_to_segment: dict {point (int): segment id (str)}
    '''

    nml_mor = neuroml.Morphology(id=f'{mor_id}')
    point_to_segment = {}

    # Collect soma points
    soma_point_set = set()
    def collect_soma_points(point):
        if d[point][0] == 1:
            soma_point_set.add(point)
            for child in children[point]:
                collect_soma_points(child)
    collect_soma_points(root)
    n_soma = len(soma_point_set)

    def make_point(p):
        return neuroml.Point3DWithDiam(
            x=str(d[p][1]),
            y=str(d[p][2]),
            z=str(d[p][3]),
            diameter=str(d[p][4] * 2)
        )

    # CASE 1: Single soma point -> sphere
    if n_soma == 1:
        log_error(
            errors,
            "Soma representation: single point sphere",
            fix="Represented as sphere (proximal == distal)"
        )

        p0 = list(soma_point_set)[0]
        somaSeg = neuroml.Segment(
            id=str(len(nml_mor.segments)),
            name="soma",
            proximal=make_point(p0),
            distal=make_point(p0)
        )
        nml_mor.segments.append(somaSeg)
        point_to_segment[p0] = somaSeg.id

    # CASE 2: Three point soma cylinder
    elif (
        n_soma == 3 and
        len([c for c in children[root] if c in soma_point_set]) == 2
    ):
        log_error(
            errors,
            "Soma representation: 3-point soma",
            fix="Converted into cylinder outer->center->outer"
        )

        center = root
        outer_points = [
            c for c in children[root]
            if c in soma_point_set
        ]
        bottom = outer_points[0]
        top = outer_points[1]

        # outer -> center
        rootSeg = neuroml.Segment(
            id=str(len(nml_mor.segments)),
            name="soma_root",
            proximal=make_point(bottom),
            distal=make_point(center)
        )

        nml_mor.segments.append(rootSeg)

        # The SWC root is located at the center.
        # All dendrites should attach here.
        point_to_segment[center] = rootSeg.id
        point_to_segment[bottom] = rootSeg.id

        # center -> outer
        extensionSeg = neuroml.Segment(
            id=str(len(nml_mor.segments)),
            name="soma_extension",
            proximal=make_point(center),
            distal=make_point(top),
            parent=neuroml.SegmentParent(
                segments=rootSeg.id
            )
        )
        nml_mor.segments.append(extensionSeg)
        point_to_segment[top] = extensionSeg.id

    # CASE 3: Other soma representations
    elif n_soma > 0:
        log_error(
            errors,
            f"Soma representation: {n_soma}-point soma",
            fix="Converted soma points into a chain"
        )

        # create ordered soma chain
        soma_points = [root]
        visited = {root}
        queue = list(children[root])

        while queue:
            p = queue.pop(0)
            if p in soma_point_set and p not in visited:
                soma_points.append(p)
                visited.add(p)
                queue.extend(children[p])

        # create chain
        for i in range(len(soma_points)-1):
            p1 = soma_points[i]
            p2 = soma_points[i+1]

            seg = neuroml.Segment(
                id=str(len(nml_mor.segments)),
                name=f"Soma_{p1}_{p2}",
                proximal=make_point(p1),
                distal=make_point(p2)
            )

            if i > 0:
                seg.parent = neuroml.SegmentParent(
                    segments=point_to_segment[p1]
                )
            nml_mor.segments.append(seg)

            # only distal point belongs to new segment
            point_to_segment[p2] = seg.id

        # root belongs to first segment
        point_to_segment[root] = "0"

    else:
        log_error(
            errors,
            "Soma representation: no soma points detected",
            fix="Root used as origin"
        )

    # Process dendrites / axons
    if n_soma == 0:
        available_points = [root]
    else:
        available_points = []
        for soma_point in soma_point_set:
            for child in children[soma_point]:
                if child not in soma_point_set:
                    available_points.append(child)

    while available_points:
        p = available_points.pop(0)
        parent = d[p][5]

        # root segment (no parent)
        if parent == -1:
            seg = neuroml.Segment(
                id=str(len(nml_mor.segments)),
                name=f"Comp_{p}",
                proximal=make_point(p),
                distal=make_point(p)
            )

        else:
            seg = neuroml.Segment(
                id=str(len(nml_mor.segments)),
                name=f"Comp_{p}",
                distal=make_point(p)
            )
            if parent in point_to_segment:

                seg.parent = neuroml.SegmentParent(
                    segments=point_to_segment[parent]
                )
            else:
                raise Exception(
                    f"No parent segment found for SWC point {p}"
                )

        nml_mor.segments.append(seg)
        point_to_segment[p] = seg.id
        available_points.extend(children[p])

    return nml_mor, point_to_segment


def process_compartments(segment_groups, type_seg, nml_mor, nml_cell, point_to_segment):
    '''
    Incorporates the segment groups into the morphology object and adds them to bigger segment groups.

    Input: - segment_groups: list with lists of segmentGroups [[point], [point], ...]
           - type_seg: dict {point (int): type morph. structurte (e.g. soma) (str)}
           - nml_mor: neuroml morphology object
           - nml_cell: neuroml cell object
           - point_to_segment: dict {point (int): segment id (str)}
    '''

    cables = []

    # Create main segment groups
    all_cables = neuroml.SegmentGroup(id='all')
    for segment_id in point_to_segment.values():
        all_cables.members.append(
            neuroml.Member(segments=str(segment_id))
        )
    soma_group = neuroml.SegmentGroup(id='soma_group', neuro_lex_id='SAO:1044911821')
    axon_group = neuroml.SegmentGroup(id='axon_group', neuro_lex_id='SAO:1770195789')
    dendrite_group = neuroml.SegmentGroup(id='dendrite_group', neuro_lex_id='SAO:1211023249')
    basal_group = neuroml.SegmentGroup(id='basal_group', neuro_lex_id='SAO:1079900774')
    apical_group = neuroml.SegmentGroup(id='apical_group', neuro_lex_id='SAO:273773228')

    custom_groups = {}  # Dictionary to hold custom segment groups
    counter = {}  # Dictionary to keep track of ids of groups

    for segment_group in segment_groups:
        type_cable = type_seg[segment_group[0]]
        if type_cable not in counter:
            counter[type_cable] = 1
        else:
            counter[type_cable] += 1
        cable_id = f'{type_cable}_{counter[type_cable]}'
        this_cable = neuroml.SegmentGroup(id=cable_id, neuro_lex_id='SAO:864921383')

        added_segments = set()

        for segment in reversed(segment_group):
            seg_id = str(point_to_segment[segment])

            if seg_id not in added_segments:
                member = neuroml.Member(segments=seg_id)
                this_cable.members.append(member)
                added_segments.add(seg_id)

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

    for seg_group in [all_cables, soma_group, axon_group, dendrite_group, basal_group, apical_group]:
        if seg_group.includes:
            nml_mor.segment_groups.append(seg_group)

    for custom_group in custom_groups.values():
        nml_mor.segment_groups.append(custom_group)

    nml_cell.morphology = nml_mor


def define_biophysical_properties(nml_cell, cell_id):
    '''
    Defines some basic biophysical properties for the given cell.

    Input: - nml_cell: neuroml cell object
           - cell_id: unique ID of neuroml cell (str)
    '''

    # Create biophysical properties object
    all_props = neuroml.BiophysicalProperties(id=f'{cell_id}_properties')

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


def write_nml_file(nml_doc, filename, output_dir=''):
    '''
    Writes the neuroml document object to a neuroml file in an optionally specified output directory.

    Input: - nml_doc: neuroml document object
           - filename: name of the SWC file (str)
           - output_dir (optional): directory in which the neuroml file will be saved (str)

    Returns: name of the newly created neuroml file (str)
    '''

    nml_file = f'{output_dir}/{filename}_converted.cell.nml' if output_dir else f'{filename}_converted.cell.nml'
    writers.NeuroMLWriter.write(nml_doc, nml_file)
    return os.path.basename(nml_file)


def log_metadata(neuron_data, status, errors):
    '''
    Logs the metadata of the neuron conversion process to a CSV file.
    
    Input: - neuron_data: dict containing neuron metadata (dict)
           - status: conversion status (str)
           - errors: dict {error message: {occurences: int, extra_info: [str], fix: str}}
    '''
    
    filename = "metadata.csv"
    exists = os.path.isfile(filename)

    # Flatten errors into plain strings
    error_types = "|".join(errors.keys()) if errors else ""

    with open(filename, "a", newline="") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "neuron_id",
                "neuron_name",
                "species",
                "cell_type",
                "brain_region",
                "status",
                "error_types",
            ]
        )

        if not exists:
            writer.writeheader()

        writer.writerow({
            "neuron_id":    neuron_data.get("neuron_id"),
            "neuron_name":  neuron_data.get("neuron_name"),
            "species":      neuron_data.get("species"),
            "cell_type":    "|".join(neuron_data.get("cell_type", []) or []),
            "brain_region": "|".join(neuron_data.get("brain_region", []) or []),
            "status":       status,
            "error_types":  error_types,
        })

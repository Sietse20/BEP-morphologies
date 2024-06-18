import neuroml
import neuroml.writers as writers
import math
import re
import os
import textwrap
import api


'''

BEFORE USING THIS PROGRAM
A few messages of how to use:

1. Make sure to change line 904 to contain your desired filepath, linking to the swc file to be converted.

---
2. Make sure that there are no comments on any same line as data in the file; only comments that start a new line with
#[This is a comment]
   will be detected as comments. Thus for example
23 2 -30.13182620  -5.46578126  -4.48630861   2.57324000 20 #[comment]
   wll give an error message.
---
3. Be sure to put the cell ID of your cell at the start of your file name, 
   separated from the rest of the file name by an underscore (_).
   Also be sure to not include any periods (.) in the file name besides for the .swc filetype indicator.
---
4. For people trying to read and understand the code, I'm sorry in advance :]
   I would recommend the function to start with to be the function 'construct_nml'.
   Any questions regarding the code? Feel free to reach out.

'''


print("Ready")


def convert_to_nml(path, output_dir=''):
    d, comments = open_and_split(path)
    filename = os.path.basename(path).split('.')[0]

    # Change pattern to be allowed by neuroml
    filename = re.sub(r'[^a-zA-Z0-9_]', '_', filename)
    if filename[0].isdigit():
        filename = '_' + filename

    cell_ID = f"{filename}_cell"

    nml_file = construct_nml(d, filename, cell_ID, comments, output_dir=output_dir)

    return nml_file


def open_and_split(path):
    d = {}
    line_nr = 0
    comments = []
    no_par = 0  # Variable used for checking amount of segments without parent

    with open(path, 'r+') as f:
        for line in f:
            line_nr += 1
            if not line:
                pass
            elif line[0] == '#':
                comments.append(line[1:].strip())
            else:
                information = [elem for elem in line.strip().split(' ') if elem]
                if not information:
                    pass
                else:
                    if len(information) != 7:
                        print(f"Line {line_nr} seems to have more/less columns than desired.")
                        if '#' in line:
                            print("Please consider removing all comments from lines that contain data, and make sure to not have indented comments.")
                    else:
                        seg_ID = int(information[0]) - 1
                        type_ID = int(information[1])
                        x_coor = float(information[2])
                        y_coor = float(information[3])
                        z_coor = float(information[4])
                        rad = float(information[5])
                        par_ID = int(information[6]) - 1

                        if par_ID < 0:
                            par_ID = -1
                            no_par += 1

                        d[seg_ID] = (type_ID, x_coor, y_coor, z_coor, rad, par_ID)
        
    # Check if cell has segments:
    if not d:
        raise Exception("Could not process SWC file, cell does not contain any segments.")
    
    # Check if cell has more than one or zero segment(s) without a parent
    if no_par == 0:
        raise Exception("SWC file contains zero segments without a parent (root segments).")
    if no_par > 1:
        raise Exception("SWC file contains more than 1 segment without a parent (root segments).")

    return d, comments


def construct_nml(d, filename, cell_ID, comments, output_dir=''):
    '''

    This function is the leading function! This function is the one that manages all the other functions, and which gives directions to the program.
    To understand the code, understanding the general process of conversion is needed - this function is the one to look at.

    First; we need to identify key points in the morphology, being; the soma, branchpoints (where branches split into more), and leaves (final segments to a branch).
    The soma has multiple ways of being encoded in an swc file; we first need to fix the morphology dictionary to eliminate this factor.
    Then, from each of those non-soma key points, we move towards the soma until we hit either the soma or another branch point. This leaves us with "linear" segmentGroups.
    After this, we can use those segmentGroups to define the cell morphology, but we need to take into account mistakes in the morphology (circular branches for example).
    This is also done automatically by the code.
    Finally, we need to give the cell some basic biophysical parameters.

    '''

    nml_doc = neuroml.NeuroMLDocument(id=filename)
    nml_cell = neuroml.Cell(id=cell_ID)
    make_notes(comments, nml_cell)
    n, children, type_seg, types, root = classify_types_branches_and_leafs(d)
    segmentGroups = find_segments(d, n, cell_ID, children)
    nml_mor = process_segments(d, children, root, cell_ID)
    nml_cell = process_cables(segmentGroups, type_seg, nml_mor, nml_cell)
    nml_cell = define_biophysical_properties(nml_cell, cell_ID)
    nml_doc.cells.append(nml_cell)
    if output_dir:
        nml_file = f'{output_dir}/{filename}_converted.cell.nml'
    else:
        nml_file = f'{filename}_converted.cell.nml'
    writers.NeuroMLWriter.write(nml_doc, nml_file)

    return os.path.basename(nml_file)


def make_notes(comments, nml_cell):
    nml_cell.notes = "\n\n" + '*' * 40 + \
                     "\nThis NeuroML file was converted from SWC to NeuroML format by Sietse Reissenweber's converter. \
                     \nFor any questions regarding the conversion, you can email me at s.reissenweber12@gmail.com. \
                     \nThe notes listed below are the notes that were originally contained in the SWC file.\n" \
                     + '*' * 40 + "\n\n"

    nml_cell.notes += "#" * 40 + "\n"

    for comment in comments:
        nml_cell.notes += f'{comment}\n'

    nml_cell.notes += "#" * 40 + "\n\n"


def classify_types_branches_and_leafs(d):
    '''

    This function classifies the segments into different types, and determines the children of points
    Returns: - n: dict
             - etc

    '''

    n = {0: [],
         1: [],
         2: []}
    root = -float("Inf")
    children = {}
    type_seg = {}
    types = {'bas_dend': [],
             'axon': [],
             'soma': [],
             'ap_dend': []}

    for point, info in d.items():
        # Create dict n:
        number_of_children = 0
        for info2 in d.values():
            if info2[5] == point:
                number_of_children += 1
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
                print("Endpoint of zero diameter detected.")
            else:
                print("Point of zero diameter detected in branch.")

        # Create dicts type_seg and types:
        if info[0] == 1:
            type_seg[point] = 'soma'
            types['soma'].append(point)
        elif info[0] == 2:
            type_seg[point] = 'axon'
            types['axon'].append(point)
        elif info[0] == 3:
            type_seg[point] = 'bas_dend'
            types['bas_dend'].append(point)
        elif info[0] == 4:
            type_seg[point] = 'ap_dend'
            types['ap_dend'].append(point)
        else:  # Account for custom types
            type_seg[point] = f'custom_{info[0]}'
            if f'custom_{info[0]}' not in types:
                print(f"Unknown type: type {info[0]} for point {point}")
                types[f'custom_{info[0]}'] = [point]
            else:
                types[f'custom_{info[0]}'].append(point)

        # Find root:
        if info[5] == -1:
            root = point
            if type_seg[root] != 'soma':
                raise Exception("Warning: spherical root segment does not belong to soma_group.")

        children[point] = []

    # Create dict children:
    for point, info in d.items():
        if point != root:
            children[info[5]].append(point)

    return n, children, type_seg, types, root


def find_segments(d, n, cell_ID, children):
    '''
    Finds segments
    '''

    segmentGroups = []

    # Processing from leaf points to branch points:
    for leaf in n[0]:
        toAdd = leaf
        group_type = d[toAdd][0]
        segGr = []
        all_loops = []
        segmentFound = False

        if toAdd == 0:
            segmentFound = True
            segGr.append(toAdd)

        while segmentFound is False:
            isin = False
            for sg in segmentGroups:  # Check if segment is already found in another segmentgroup
                if toAdd in sg:
                    isin = True
            if toAdd in segGr and d[toAdd][5] != -1:
                isin = True

            if isin is True and toAdd not in n[2]:
                all_loops.append(segGr)
                break
            elif toAdd == 0 and toAdd in n[2]:  # Start new segmentgroup at branching point, even if root
                segmentFound = True
            elif toAdd == 0:
                segmentFound = True
                segGr.append(toAdd)
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

        if all_loops:
            print(f"Loop found! this is the segment groups: {all_loops}")

        for loop in all_loops:
            segmentGroups = adjustSegmentGroups(loop, segmentGroups, children, d)

        if segGr:
            segmentGroups.append(segGr)

    # Processing from branch points to other branch points:
    for branch in n[2]:
        toAdd = branch
        group_type = d[toAdd][0]
        segGr = []
        segmentFound = False
        all_loops = []

        if toAdd == 0:
            segmentFound = True
            segGr.append(toAdd)

        while segmentFound is False:
            isin = False
            for sg in segmentGroups:
                if toAdd in sg:
                    isin = True

            if (toAdd in segGr or isin is True) and toAdd != 0 and toAdd not in n[2]:
                all_loops.append(segGr)
                print("it reaches this step")
                break
            elif toAdd == 0 and toAdd in n[2]: 
                segmentFound = True
            elif toAdd == 0:
                segmentFound = True
                segGr.append(toAdd)
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

        if all_loops:
            print(all_loops)

        for loop in all_loops:
            segmentGroups = adjustSegmentGroups(loop, segmentGroups, children, d)

        if segGr:
            segmentGroups.append(segGr)

    # Calculate amount of points processed
    N = 0
    for seggroup in segmentGroups:
        N += len(seggroup)

    if N != len(d):
        print("Number of processed segments:", N)
        print("Number of segments expected:", len(d))
        print("Watch out! Number of processed segments does not match. Loops might be present!")
        print("The following numbers all correspond to the ID of the segments in the SWC file.")
        print("---------------------")
        print(f"The segments that are absent in the processed neuron {cell_ID} are:")
        non_present_segments = []
        for point in d:
            found = False
            for seggr in segmentGroups:
                for seg in seggr:
                    if seg == point:
                        print(f"Found {point}")
                        found = True
            if found is False:
                print(f"Did not find {point}")
                non_present_segments.append(point)
        check_for_loops(segmentGroups, d, non_present_segments, n, children)

    return segmentGroups


def adjustSegmentGroups(loop, segmentGroups, children, d):
    node = loop[0]
    loopnew = []
    available = []
    loop = []
    loopfound = False
    while loopfound is False:
        loopnew.append(node)
        print(node)
        node = d[node][5]
        if node in loopnew:
            loopfound = True

    for segment in loopnew:
        loop.append(segment)
        available.append(segment)

    fully_adjusted = False
    to_remove = []

    while fully_adjusted is False:
        to_check = available[0]
        print(f"{to_check} will be checked now")
        for segmentgr in segmentGroups:
            if to_check in segmentgr:
                print(f"{to_check} was found in a segment group")
                if segmentgr not in to_remove:
                    print(f"{to_check} caused a deletion!")
                    to_remove.append(segmentgr)
                    print(f"To remove are now {to_check}")
        if children[to_check] != []:
            for chh in children[to_check]:
                if chh not in loop:
                    available.append(chh)
                    print(f"Appended {chh} since {to_check} was gone.")
            print("Done")
        available.remove(to_check)
        if available == []:
            fully_adjusted = True

    print(f"To remove are {to_remove}")

    segmentGroupsProxy = segmentGroups
    for seggr in to_remove:
        for seg in seggr:
            for segmentgroup in segmentGroupsProxy:
                if seg in segmentgroup:
                    if segmentgroup in segmentGroups:
                        segmentGroups.remove(segmentgroup)

    return segmentGroups


def check_for_loops(segmentGroups, d, non_present_segments, n, children):
    # Only occurs if a mismatch in numbers is detected, which indicates the presence of loops.
    # This is a large chunk of code, but really not important to understand if only used on regular neurons.

    print('---------------------')
    # print(n[2])
    # print(non_present_segments)
    branch_in = False
    branches = []
    for absseg in non_present_segments:
        if absseg in n[2]:
            branch_in = True
            branches.append(absseg)

    if branch_in is True:
        # locate the loop(s)
        hadall = False
        had = []
        point_to_test = branches[0]
        i = 1
        while hadall is False:
            loop_found = False
            had_this = []
            loopy = []
            while loop_found is False:
                if point_to_test in had or point_to_test in had_this:
                    print("There is a loop present containing the following segments:")

                    inloop = False

                    for seg in had_this+had:
                        if seg == point_to_test:
                            inloop = True
                            loopy.append(seg)

                    thislompyfound = False
                    while thislompyfound is False:
                        if d[loopy[-1]][5] not in loopy:
                            loopy.append(d[loopy[-1]][5])
                        else:
                            thislompyfound = True

                    for item in loopy:
                        print("Segment: %s" %(item+1))

                    print("To this loop, branches are attached containing the following segments:")
                    available = []
                    for seggy in loopy:
                        for child in children[seggy]:
                            if child not in loopy:
                                available.append(child)
                    # print(available, "are available")
                    allfound = False
                    while allfound is False:
                        next_print = min(available)
                        print(f"Segment: {next_print + 1}")
                        if next_print in branches:
                            branches.remove(next_print)
                        had.append(next_print)
                        available.remove(next_print)
                        for cc in children[next_print]:
                            available.append(cc)
                        if len(available) == 0:
                            allfound = True

                    for item in had:
                        if item in non_present_segments:
                            non_present_segments.remove(item)
                    had = []

                    print("---------------------")
                    stillLeft = False

                    for segm in non_present_segments:
                        if segm not in had and segm not in had_this:
                            if stillLeft is False:
                                print("The following segments have still been unassigned:")
                            stillLeft = True
                            print(f"Segment: {segm + 1}")

                    if stillLeft is False:
                        print("All missing segments have been analysed. Thanks for your patience.")

                    loop_found = True

                else:
                    had_this.append(point_to_test)
                    point_to_test = d[point_to_test][5]
            had = had + had_this
            if len(had) == len(non_present_segments):
                hadall = True
            else:
                if i < len(branches):
                    point_to_test = branches[i]
                    i = i + 1
                else:
                    # here the entire code for finding a loop without branch again
                    for item in had:
                        if item in non_present_segments:
                            non_present_segments.remove(item)
                    had = []
                    hadall_complete_loops = False
                    point_to_test = non_present_segments[0]

                    while hadall_complete_loops is False:
                        pathfound = False
                        while pathfound is False:
                            if point_to_test in had:
                                print("???????")
                            had.append(point_to_test)
                            point_to_test = d[point_to_test][5]
                            if point_to_test == non_present_segments[0]:
                                pathfound = True
                        if len(had) == len(non_present_segments):
                            hadall_complete_loops = True
                            print("There is a loop present with all last mentioned segments.")
                        else:
                            print("There is a loop present containing the following segments:")
                            for seg in had:
                                print(f"Segment: {seg + 1}")
                                non_present_segments.remove(seg)
                            print("---------------------")
                            had = []
                            point_to_test = non_present_segments[0]
                            print("The following segments are still not assigned:")
                            for seg in non_present_segments:
                                print(f"Segment: {seg + 1}")

                    hadall = True

    else:
        print(non_present_segments)
        point_to_test = non_present_segments[0]
        had = []
        hadall = False
        while hadall is False:
            pathfound = False
            while pathfound is False:
                if point_to_test in had:
                    print("??????")
                had.append(point_to_test)
                point_to_test = d[point_to_test][5]
                if point_to_test == non_present_segments[0]:
                    pathfound = True
            if len(had) == len(non_present_segments):
                hadall = True
                print("There is a loop present containing all last mentioned segments.")
            else:
                print("There is a loop present containing the following segments:")
                for seg in had:
                    print(f"Segment: {seg + 1}")
                    non_present_segments.remove(seg)
                print("---------------------")
                had = []
                point_to_test = non_present_segments[0]
                print("The following segments are still not assigned:")
                # for seg in non_present_segments:
                # print("Segment: %s" %(seg+1))

    print("---------------------")


def process_segments(d, children, root, Cell_ID):
    '''
    We now process all segments one by one
    '''

    nml_mor = neuroml.Morphology(id=f'{Cell_ID}_morphology')

    available_points = [root]
    processed = []
    all_processed = False

    while all_processed is False:
        next_to_process = min(available_points)

        if next_to_process in processed:
            print(f"Please, take a look at segment {next_to_process}, since it is being processed twice!")

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
            # Only one segment may be spherical and must belong to the soma_group SegmentGroup:
            coord_distal = (d[next_to_process][1], d[next_to_process][2], d[next_to_process][3])
            coord_proximal = (d[parent][1], d[parent][2], d[parent][3])
            if coord_distal == coord_proximal and d[next_to_process][4] == d[parent][4]:
                print(f"Warning: 2 segments detected with same radius and coordinates, see point {next_to_process + 1}.")
            
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
    Group the different segments together and organize them into cables.
    '''

    cablenumber = 1
    cables = {}
    type_cab = {}

    # Create main segment groups
    all_cables = neuroml.SegmentGroup(id='all')
    soma_group = neuroml.SegmentGroup(id='soma_group', neuro_lex_id='SAO:1044911821')
    axon_group = neuroml.SegmentGroup(id='axon_group', neuro_lex_id='SAO:1770195789')
    dendrite_group = neuroml.SegmentGroup(id='dendrite_group', neuro_lex_id='SAO:1211023249')
    basal_group = neuroml.SegmentGroup(id='basal_group', neuro_lex_id='SAO:1079900774')
    apical_group = neuroml.SegmentGroup(id='apical_group', neuro_lex_id='SAO:273773228')

    custom_groups = {}  # Dictionary to hold custom segment groups

    for segmentGroup in segmentGroups:
        type_cable = ''
        cable_id = f'{type_seg[segmentGroup[0]]}_{cablenumber}'
        this_cable = neuroml.SegmentGroup(id=cable_id, neuro_lex_id='SAO:864921383')

        for segment in reversed(segmentGroup):
            member = neuroml.Member(segments=segment)
            this_cable.members.append(member)
            type_this_seg = type_seg[segment]
            if type_cable and type_cable != type_this_seg:
                print(f"Error; cable {cablenumber} has multiple types!")
            else:
                type_cable = type_this_seg

        cables[cablenumber] = this_cable
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

        type_cab[cablenumber] = type_cable
        cablenumber += 1

    # Check if cell contains soma segmentgroup
    if not soma_group.includes:
        raise Exception("Warning: Cell is not valid because it does not contain any soma segments.")

    # Append all cables and segment groups to morphology
    for cable in cables.values():
        nml_mor.segment_groups.append(cable)

    for type in [all_cables, basal_group, apical_group, soma_group, axon_group, dendrite_group]:
        if type.includes:
            nml_mor.segment_groups.append(type)

    for custom_group in custom_groups.values():
        nml_mor.segment_groups.append(custom_group)

    nml_cell.morphology = nml_mor

    return nml_cell


def define_biophysical_properties(nml_cell, Cell_ID):
    '''
    Define biophysical properties for the given cell
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

    return nml_cell


def print_statistics(d, segment_groups):
    '''
    Prints the relevant statistics we want to know.
    '''

    total_area = 0
    total_volume = 0

    for group in segment_groups:
        for segment in group:
            par = d[segment][5]

            if par == -1:
                # Spherical segment
                radius = d[segment][4]
                segment_area = 4 * math.pi * radius**2
                segment_volume = 4/3 * math.pi * radius**3
            else:
                # Cylindrical segment
                radius = d[segment][4]
                radius_par = d[par][4]
                x, y, z = d[segment][1], d[segment][2], d[segment][3]
                xpar, ypar, zpar = d[par][1], d[par][2], d[par][3]
                distance = math.sqrt((x - xpar)**2 + (y - ypar)**2 + (z - zpar)**2)

                if radius != radius_par:  # Frustum
                    s = math.sqrt((radius_par - radius)**2 + distance**2)
                    segment_area = math.pi * (radius_par + radius) * s
                    segment_volume = 1/3 * math.pi * distance * (radius_par**2 + radius**2 + (radius_par * radius))
                else:  # Cylinder
                    segment_area = 2 * math.pi * radius * distance
                    segment_volume = math.pi * (radius**2) * distance

            total_area += segment_area
            total_volume += segment_volume

    print(f"The total area of this neuron is: {total_area}")
    print(f"The total volume of this neuron is: {total_volume}")
    print(f"The area to volume ratio (A/V) of this neuron is: {total_area/total_volume}")
    print(">-------<")


# Converting from API:

# range_api = (1, 10)

# for neuron_id in range(*range_api):
#     swc_file = api2.create_swc_file(neuron_id, output_dir=output_dir_swc)
#     try:
#         nml_file = convert_to_nml(swc_file, output_dir=output_dir_nml)
#         print(f'Converted {swc_file.split('/')[-1]} to the following file: {nml_file}\n')
#     except Exception as e:
#         print(f'Error converting {swc_file}: {e}\n')


# Converting from a map:

# path_swc = 'swc_no_api'
# path_nml = 'nml_no_api'

# total_errors = 0
# exception_counts = {}

# # Use os.walk to iterate through all directories and subdirectories
# file_paths = []
# for root, dirs, files in os.walk(path_swc):
#     for file in files:
#         if file.endswith('.CNG.swc'):
#             file_paths.append(os.path.join(root, file))

# total_files = len(file_paths)

# for file_path in file_paths:
#     swc_file = os.path.basename(file_path)
#     print(f'Processing file: {swc_file}')
#     try:
#         nml_file_name = convert_to_nml(file_path, output_dir=path_nml)
#         print(f'Converted {swc_file} to the following file: {nml_file_name}\n')
#     except Exception as e:
#         exception_message = str(e)
#         if exception_message in exception_counts:
#             exception_counts[exception_message] += 1
#         else:
#             exception_counts[exception_message] = 1
#         total_errors += 1
#         print(f'Error converting {swc_file}: {e}\n')


# print(f'From {total_files} total files: \nConversion successful for {total_files - total_errors} files. \nConversion unsuccessful for {total_errors} files.')
# print("\nSummary of Exception Counts:")
# for exception_type, count in exception_counts.items():
#     print(f"{exception_type}: {count} times")


# Converting single file:

path = 'swc_no_api/GGN_20170309_sc.swc'
output_dir = ''

swc_file = os.path.basename(path)
try:
    nml_file = convert_to_nml(path, output_dir='')
    print(f'Converted {swc_file} to the following file: {nml_file}\n')
except Exception as e:
    print(f'Error converting {swc_file}: {e}\n')

import neuroml
import neuroml.writers as writers
import math
import re
import api2


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


def convert_to_nml(path, output_dir):
    d = open_and_split(path)
    file = path.split('/')[-1]
    cell_ID = file.split('_')[0]

    # Check if id is allowed by neuroml
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    regex = re.compile(pattern)
    if not bool(regex.match(cell_ID)):
        raise Exception("Change filename to match format [a-zA-Z_][a-zA-Z0-9_]*")

    nml_file = construct_nml(d, cell_ID, file, output_dir)

    return nml_file


def fix_dict(d, types, children):
    '''

    This function exists to fix any types of somas that don't work in NeuroML.
    At the moment, incorporated (and thus able to be converted are:

    1) Somas indicated by a soma-outline, both one and multiple

    '''

    hadcoords = []
    outline = False
    multiple_outline = False

    for soma_seg in types['soma']:
        x = d[soma_seg][1]
        y = d[soma_seg][2]
        z = d[soma_seg][3]
        coor = (x, y, z)
        if coor in hadcoords:
            if outline is True:
                multiple_outline = True
            outline = True
        hadcoords.append(coor)

    hadcoords = []
    tot_x = 0
    tot_y = 0
    tot_z = 0
    amount_of_points = 0

    if outline is True:
        print("Points of the soma are treated as soma outline!")
        print(">-------<")

        for seg in types['soma']:
            x = d[seg][1]
            y = d[seg][2]
            z = d[seg][3]
            coor = (x, y, z)

            if coor not in hadcoords:
                tot_x = tot_x + x
                tot_y = tot_y + y
                tot_z = tot_z + z
                amount_of_points = amount_of_points + 1
            hadcoords.append(coor)

        # print("The amount of points is: %s" %amount_of_points)
        Cx = tot_x/amount_of_points
        Cy = tot_y/amount_of_points
        Cz = tot_z/amount_of_points

        tot_dis = 0
        hadcoords = []
        # print("Center of mass: %s %s %s" %(Cx,Cy,Cz))

        for seg in types['soma']:
            # print("Segment: %s" %seg)
            x = d[seg][1]
            y = d[seg][2]
            z = d[seg][3]
            coor = (x, y, z)
            # print("Coor: %s %s %s" %(x,y,z))
            distance = ((Cx - x)**2 + (Cy - y)**2 + (Cz - z)**2)**(1/2)
            # print("Distance: %s" %distance)

            if coor not in hadcoords:
                tot_dis = tot_dis + distance
                # print("The total distance becomes: %s" %tot_dis)
            hadcoords.append(coor)

        rs = (tot_dis/amount_of_points)*(5/8)

        to_sub = len(types['soma']) - 3

        d_new = {}
        d_new[0] = (1, Cx, Cy, Cz, rs, -1)
        d_new[1] = (1, Cx, Cy+rs, Cz, rs, 0)
        d_new[2] = (1, Cx, Cy-rs, Cz, rs, 0)

        for entry in d:
            if d[entry][0] != 1:
                type_seg = d[entry][0]
                x_seg = d[entry][1]
                y_seg = d[entry][2]
                z_seg = d[entry][3]
                rad_seg = d[entry][4]
                par_seg = d[entry][5]

                if d[par_seg][0] == 1:
                    par_seg = 0
                else:
                    par_seg = par_seg - to_sub

                new_ID = entry - to_sub
                d_new[new_ID] = (type_seg, x_seg, y_seg, z_seg, rad_seg, par_seg)

        # print("The dictionary:")
        # print(d)
        # print("Has been refined to dictionary:")
        # print(d_new)

        n, children, type_seg, types, root = classify_types_branches_and_leafs(d_new)

        return d_new, n, children, type_seg, types, root


def open_and_split(path):
    d = {}
    line_nr = 0

    with open(path, 'r+') as f:
        for line in f:
            line_nr += 1
            if not line or line[0] == '#':
                pass
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

                        d[seg_ID] = (type_ID, x_coor, y_coor, z_coor, rad, par_ID)

    return d


def construct_nml(d, cell_ID, filename, output_dir):
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

    generic_file_name = filename.split('.')[0]
    nml_doc = neuroml.NeuroMLDocument(id=generic_file_name)
    nml_cell = neuroml.Cell(id=cell_ID)
    n, children, type_seg, types, root = classify_types_branches_and_leafs(d)
    # d, n, children, type_seg, types, root = fix_dict(d, types, children)
    segmentGroups = find_segments(d, n, cell_ID, children)
    nml_mor = process_segments(d, children, root, cell_ID)
    nml_cell = process_cables(segmentGroups, type_seg, nml_mor, nml_cell)
    nml_cell = define_biophysical_properties(nml_cell, cell_ID)
    nml_doc.cells.append(nml_cell)
    nml_file = f'{output_dir}/{generic_file_name}_converted.cell.nml'
    writers.NeuroMLWriter.write(nml_doc, nml_file)
    print_statistics(d, segmentGroups)

    return nml_file


def classify_types_branches_and_leafs(d: dict[int, tuple]):
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
    types = {'dend': [],
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
            type_seg[point] = 'dend'
            types['dend'].append(point)
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
    all_dendrites = neuroml.SegmentGroup(id='all_dend', neuro_lex_id='GO:0030425')
    all_axons = neuroml.SegmentGroup(id='all_axon', neuro_lex_id='GO:0030424')
    all_somas = neuroml.SegmentGroup(id='all_soma', neuro_lex_id='GO:0043025')

    for segmentGroup in segmentGroups:
        type_cable = ''
        cable_id = f'Cable_{cablenumber}'
        this_cable = neuroml.SegmentGroup(id=cable_id, neuro_lex_id='sao864921383')

        for segment in reversed(segmentGroup):
            member = neuroml.Member(segments=segment)
            this_cable.members.append(member)
            type_this_seg = type_seg[segment]
            if type_cable and type_cable != type_this_seg:
                print(f"Error; cable {cablenumber - 1} has multiple types!")
            else:
                type_cable = type_this_seg

        cables[cablenumber] = this_cable
        cable_include = neuroml.Include(segment_groups=cable_id)
        all_cables.includes.append(cable_include)

        if type_cable == 'soma':
            all_somas.includes.append(cable_include)
        elif type_cable == 'axon':
            all_axons.includes.append(cable_include)
        elif type_cable == 'dend':
            all_dendrites.includes.append(cable_include)

        type_cab[cablenumber] = type_cable
        cablenumber += 1

    # Append all cables and segment groups to morphology
    for cable in cables.values():
        nml_mor.segment_groups.append(cable)

    nml_mor.segment_groups.extend([all_cables, all_dendrites, all_somas, all_axons])

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


# Indicate if you want to use the api
# use_api = False
# range_api = (1, 10)
# if use_api:
#     for neuron_id in range(*range_api):
#         swc_file = api2.create_swc_file(neuron_id, 'map swc files')
#         nml_file_name = convert_to_nml(swc_file, 'map nml files')
#         print(f'Converted the following file: {nml_file_name}')
# else:
#     for neuron_id in range(1, 10):
#         swc_file = f'map_swc_files/neuron_{neuron_id}.swc'  # Insert the path of the swc-file here
#         nml_file_name = convert_to_nml(swc_file, 'map_nml_files')
#         print(f'Converted the following file: {nml_file_name}')

swc_file = 'NML_files_working/STRESS_1_N5_1_CNG.swc'  # Insert the path of the swc-file here
nml_file_name = convert_to_nml(swc_file, 'NML_files_working')
print(f'Converted the following file: {nml_file_name}')

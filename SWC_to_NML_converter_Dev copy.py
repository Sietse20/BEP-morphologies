#!/usr/bin/env python
# coding: utf-8

# In[76]:


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


# In[77]:


# Importing packages that are needed

import os
import neuroml
import neuroml.writers as writers
import math
import api2


# In[78]:


def convert_to_nml(path, output_dir):
    d = open_and_split(path)
    file = path.split('/')[-1]
    cell_ID = file.split('_')[0]
    nml_file = construct_nml(d, cell_ID, file, output_dir)
    
    return nml_file


# In[95]:


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
        coor = (x,y,z)
        if coor in hadcoords:
            if outline == True:
                multiple_outline = True
            outline = True
        hadcoords.append(coor)
        
    hadcoords = []
    tot_x = 0
    tot_y = 0
    tot_z = 0
    amount_of_points = 0
    
    if outline == True:
        print("Points of the soma are treated as soma outline!")
        print(">-------<")
        
        for seg in types['soma']:
            x = d[seg][1]
            y = d[seg][2]
            z = d[seg][3]
            coor = (x,y,z)
            
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
        CoM = (Cx,Cy,Cz)
        
        tot_dis = 0
        hadcoords = []
        # print("Center of mass: %s %s %s" %(Cx,Cy,Cz))
        
        for seg in types['soma']:
            # print("Segment: %s" %seg)
            x = d[seg][1]
            y = d[seg][2]
            z = d[seg][3]
            coor = (x,y,z)
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
        
        n,children,type_seg,types,root = classify_types_branches_and_leafs(d_new)
        
        return d_new,n,children,type_seg,types,root
        


# In[80]:


def open_and_split(path):
    d = {}
    lines = []
    f = open(path, 'r+')
    lines = f.read().split('\n')
    important_lines = []
    for l in lines:
        if l != '':
            if l[0] != '#':
                important_lines.append(l)
    number_of_comments = len(lines) - len(important_lines)
    entry = 0
    for l in important_lines:
        entry += 1
        tempinf = l.split(' ')
        information = []
        for piece in tempinf:
            if piece != '':
                information.append(piece)
        if len(information) != 7:
            print("Line " + str(entry + number_of_comments) + " seems to have more columns than desired.")
            if '#' in l:
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
    
    print(d)
    return d


# In[81]:


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
    nml_doc = neuroml.NeuroMLDocument(id=f"{generic_file_name}")
    nml_cell = neuroml.Cell(id=f"{cell_ID}")
    n,children,type_seg,types,root = classify_types_branches_and_leafs(d)
    # d,n,children,type_seg,types,root = fix_dict(d,types,children)
    segmentGroups = find_segments(d,n,cell_ID,children)
    nml_mor = process_segments(d,children,root,cell_ID)
    nml_cell = process_cables(segmentGroups,type_seg,nml_mor,nml_cell)
    nml_cell = define_biophysical_properties(nml_cell,cell_ID)
    nml_doc.cells.append(nml_cell)
    nml_file = f'{output_dir}/{generic_file_name}_converted.cell.nml'
    writers.NeuroMLWriter.write(nml_doc, nml_file)
    # print_statistics(d, segmentGroups)
    
    return nml_file


# In[82]:


def classify_types_branches_and_leafs(d):
    # Find branch points and leaf points

    n = {}
    n[0] = []
    n[1] = []
    n[2] = []
    n['soma'] = []
    root = -2 # Is going to be positive!!!!!

    children = {}

    type_seg = {}
    types = {}
    types['dend'] = []
    types['axon'] = []
    types['soma'] = []
    types['ap_dend'] = []

    for point in range(0,len(d)):

        number_of_children = 0
        for count in range(0,len(d)):
            if d[count][5] == point:
                number_of_children += 1
        if number_of_children == 0:
            n[0].append(point)
        elif number_of_children == 1:
            n[1].append(point)
        else:
            n[2].append(point)
        

        if d[point][0] == 1:
            type_seg[point] = 'soma'
            types['soma'].append(point)
        elif d[point][0] == 2:
            type_seg[point] = 'axon'
            types['axon'].append(point)
        elif d[point][0] == 3:
            type_seg[point] = 'dend'
            types['dend'].append(point)
        elif d[point][0] == 4:
            type_seg[point] = 'ap_dend'
            types['ap_dend'].append(point)
        else:
            type_seg[point] = f'custom_{d[point][0]}'
            if f'custom_{d[point][0]}' not in types:
                print("Unknown type: type %s for point %s" %(d[point][0], point))
                types[f'custom_{d[point][0]}'] = [point]
            else:
                types[f'custom_{d[point][0]}'].append(point)


        if d[point][5] == -1:
            root = point # The root will become positive at some point
        children[point] = []

    for counter in range(0,len(d)):
        if counter != root:
            children[d[counter][5]].append(counter)    

            
    # print(n)
    # print("Root: %s" %root)
    # print(children)
    # print(type_seg)
    

    return n,children,type_seg,types,root

    # Elements in n[0] are leaf points, n[1] are normal points, n[2] are branch points, n['soma'] are soma segments


# In[83]:


def find_segments(d,n,cell_ID,children):
    # Now find the segments;

    segmentGroups = []
    N = 0

    for leaf in n[0]:
        toAdd = leaf
        group_type = d[toAdd][0]
        segGr = []
        all_loops = []
        segmentFound = False
        if toAdd == 0:
            segmentFound = True
            segGr.append(toAdd)
        while segmentFound == False:
            # print("Segment: %s is being processed." %toAdd)
            # print("%s is the segGr array at the moment." %segGr)
            # print("%s is the segmentGroups array at the moment." %segmentGroups)
            
            isin = False
            for i in segmentGroups:
                if toAdd in i:
                    isin = True
            if toAdd in segGr and d[toAdd][5] != -1:
                isin = True
                
            if isin == True and toAdd not in n[2]:
                # print("Loop: processing skipped.")
                all_loops.append(segGr)
                
                break
            elif toAdd == 0 and toAdd in n[2]: #??????????????????
                segmentFound = True
            elif toAdd == 0:
                segmentFound = True
                segGr.append(toAdd)
            elif d[toAdd][0] != group_type:
                segmentGroups.append(segGr)
                N += len(segGr)
                segGr = []
                segGr.append(toAdd)
                group_type = d[toAdd][0]
                toAdd = d[toAdd][5]
            elif toAdd in n[2]:
                segmentFound = True
            else:
                segGr.append(toAdd)
                toAdd = d[toAdd][5]
        
        if all_loops:
            print(all_loops)

        for loop in all_loops:
            segmentGroupsNew = adjustSegmentGroups(loop,segmentGroups,children,d)
            segmentGroups = segmentGroupsNew
        
        if segGr != []:
            segmentGroups.append(segGr)
            N += len(segGr)

    for branch in n[2]:
        toAdd = branch
        group_type = d[toAdd][0]
        segGr = []
        segmentFound = False
        all_loops = []
        if toAdd == 0:
            segmentFound = True
            segGr.append(toAdd)
        while segmentFound == False:
            # print("Segment: %s is being processed." %toAdd)
            # print("%s is the segGr array at the moment." %segGr)
            # print("%s is the segmentGroups array at the moment." %segmentGroups)
            isin = False
            for i in segmentGroups:
                if toAdd in i:
                    print(branch)
                    print(toAdd)
                    print(toAdd in n[2])
                    print(i)
                    isin = True
            if (toAdd in segGr or isin == True) and toAdd != 0 and toAdd not in n[2]:
                # print("Loop: processing skipped.")
                print(f'isin:{isin}')
                print(f'toAdd in segGr:{toAdd in segGr}')
                all_loops.append(segGr)
                break
            elif toAdd == 0 and toAdd in n[2]:
                segmentFound = True
            elif toAdd == 0:
                segmentFound = True
                segGr.append(toAdd)
            elif d[toAdd][0] != group_type:
                segmentGroups.append(segGr)
                N += len(segGr)
                segGr = []
                segGr.append(toAdd)
                group_type = d[toAdd][0]
                toAdd = d[toAdd][5]
            elif toAdd in n[2] and toAdd != branch:
                if toAdd == 428 and branch == 441:
                    print('elif segmentfound true')
                segmentFound = True
            else:
                if toAdd == 428 and branch == 441:
                    print('else')
                segGr.append(toAdd)
                toAdd = d[toAdd][5]

        if all_loops:
            print(all_loops)
       
        for loop in all_loops:
            segmentGroupsNew = adjustSegmentGroups(loop,segmentGroups,children,d)
            segmentGroups = segmentGroupsNew        
        
        if segGr != []:
            segmentGroups.append(segGr)
    
    N = 0
    for seggroup in segmentGroups:
        N += len(seggroup)
            
    print(segmentGroups)
    print(len(segmentGroups))
    
    if N != len(d):
        print("Number of processed segments:", N)
        print("Number of segments expected:", len(d))
        print("Watch out! Number of processed segments does not match. Loops might be present!")
        print("The following numbers all correspond to the ID of the segments in the SWC file.")
        print("---------------------")
        print("The segments that are absent in the processed neuron %s are:" %(cell_ID))
        non_present_segments = []
        for item in d:
            found = False
            for segmgr in segmentGroups:
                for seg in segmgr:
                    if seg == item:
                        print("Found",item)
                        found = True
                        # print("Found %s" %item)
            if found == False:
                print("Not found", item)
                non_present_segments.append(item)
        check_for_loops(segmentGroups,d,non_present_segments,n,children)

    # In some cases, non_present_segments does not contain ALL segments that aren't present. Especially when

    '''
    print(segmentGroups)
    '''
    
    return segmentGroups

    # We now get an array with arrays indicating the different segment groups


# In[84]:


def adjustSegmentGroups(loop, segmentGroups, children,d):
    # print(children)
    
    # print(segmentGroups, "begin")
    # print("Loop: %s" %loop)
    
    node = loop[0]
    loopnew = []
    available = []
    loop = []
    loopfound = False
    while loopfound == False:
        loopnew.append(node)
        print(node)
        node = d[node][5]
        if node in loopnew:
            loopfound = True
    # loop = loopnew
    
    # available = loopnew # loop is interconnected with available and idk why :(
    
    for segment in loopnew:
        loop.append(segment)
        available.append(segment)
    
    # print(loop)
    
    fully_adjusted = False
    to_remove = []
    # print(available)
    while fully_adjusted == False:
        # print(available)
        # print(loop)
        to_check = available[0]
        print("%s will be checked now" %to_check)
        for segmentgr in segmentGroups:
            if to_check in segmentgr:
                print("%s was found in a segment group" %to_check)
                if segmentgr not in to_remove:
                    print("%s caused a deletion!" %to_check)
                    to_remove.append(segmentgr)
                    print("To remove are now %s" %to_remove)
        if children[to_check] != []:
            for chh in children[to_check]:
                if chh not in loop:
                    available.append(chh)
                    print("Appended %s since %s was gone." %(chh,to_check)) 
            print("Done")
        available.remove(to_check)
        if available == []:
            fully_adjusted = True
    
    print("To remove are %s" %to_remove)
    
    segmentGroupsProxy = segmentGroups
    for seggr in to_remove:
        for seg in seggr:
            for segmentgroup in segmentGroupsProxy:
                if seg in segmentgroup:
                    if segmentgroup in segmentGroups:
                        segmentGroups.remove(segmentgroup)
    
    # print(segmentGroups)
    
    return segmentGroups


# In[85]:


def check_for_loops(segmentGroups, d, non_present_segments,n,children):
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
    
    # print("I'm now entering loop. State:",branch_in)
    if branch_in == True:
        # locate the loop(s)
        hadall = False
        had = []
        point_to_test = branches[0]
        i = 1
        while hadall == False:
            loop_found = False
            had_this = []
            loopy = []
            while loop_found == False:
                if point_to_test in had or point_to_test in had_this:
                    print("There is a loop present containing the following segments:")
                    
                    
                    inloop = False
                    
                    for seg in had_this+had:
                        if seg == point_to_test:
                            inloop = True
                            loopy.append(seg)
                    
                    thislompyfound = False
                    while thislompyfound == False:
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
                    while allfound == False:
                        next_print = min(available)
                        print("Segment: %s" %(next_print+1))
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
                            if stillLeft == False:
                                print("The following segments have still been unassigned:")
                            stillLeft = True
                            print("Segment: %s" %(segm+1))
                    
                    if stillLeft == False:
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

                    while hadall_complete_loops == False:
                        pathfound = False
                        while pathfound == False:
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
                                print("Segment: %s" %(seg+1))
                                non_present_segments.remove(seg)
                            print("---------------------")
                            had = []
                            point_to_test = non_present_segments[0]
                            print("The following segments are still not assigned:")
                            for seg in non_present_segments:
                                print("Segment: %s" %(seg+1))
                    
                    hadall = True
                    
    else:
        print(non_present_segments)
        point_to_test = non_present_segments[0]
        had = []
        hadall = False
        while hadall == False:
            pathfound = False
            while pathfound == False:
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
                    print("Segment: %s" %(seg+1))
                    non_present_segments.remove(seg)
                print("---------------------")
                had = []
                point_to_test = non_present_segments[0]
                print("The following segments are still not assigned:")
                # for seg in non_present_segments:
                    # print("Segment: %s" %(seg+1))
                    
                    
    print("---------------------")


# In[86]:


def process_segments(d,children,root,Cell_ID):
    # We now process all segments one by one
    
    nml_mor = neuroml.Morphology(id='%s_morphology' %Cell_ID)

    available_points = [root]
    segments = {}
    processed = []
    all_processed = False
    while all_processed == False:
        next_to_process = min(available_points)
        if next_to_process in processed:
            print("Please, take a look at segment %s, since it is being processed twice!" %next_to_process)
        if next_to_process == root:
            Soma_Root = neuroml.Point3DWithDiam(x=str(d[next_to_process][1]),
                                               y=str(d[next_to_process][2]),
                                               z=str(d[next_to_process][3]),
                                               diameter=str(d[next_to_process][4]*2))
            distalp = Soma_Root
            proximalp = Soma_Root
        else:
            distalp = neuroml.Point3DWithDiam(x=str(d[next_to_process][1]),
                                            y=str(d[next_to_process][2]),
                                            z=str(d[next_to_process][3]),
                                            diameter=str(d[next_to_process][4]*2))
            parent = d[next_to_process][5]
            proximalp = neuroml.Point3DWithDiam(x=str(d[parent][1]),
                                              y=str(d[parent][2]),
                                              z=str(d[parent][3]),
                                              diameter=str(d[parent][4]*2))

        parentID = d[next_to_process][5]
        if parentID != -1:
            segpar = neuroml.SegmentParent(segments=parentID)
            parentSeg = segments[parentID]

            thisSeg = neuroml.Segment(id=str(next_to_process),name='Comp_%s' %str(next_to_process),
                                 distal=distalp,
                                 parent=segpar)
        else:
            thisSeg = neuroml.Segment(id=str(next_to_process),name='Comp_%s' %str(next_to_process),
                                 proximal=proximalp,
                                 distal=distalp)

        nml_mor.segments.append(thisSeg)
        segments[next_to_process] = thisSeg
        processed.append(next_to_process)

        available_points.remove(next_to_process)
        available_points = available_points + children[next_to_process]
        if available_points == []:
            all_processed = True
            
    return nml_mor
            
    # We now have processed all segments into neuroml Segment classes.


# In[87]:


def process_cables(segmentGroups,type_seg,nml_mor,nml_cell):
    # Now we'll group the different segments together

    cablenumber = 1
    cables = {}

    all_cables = neuroml.SegmentGroup(id='all')
    all_dendrites = neuroml.SegmentGroup(id='all_dend', neuro_lex_id='GO:0030425')
    all_axons = neuroml.SegmentGroup(id='all_axon', neuro_lex_id='GO:0030424')
    all_somas = neuroml.SegmentGroup(id='all_soma', neuro_lex_id='GO:0043025')

    type_cab = {}

    for segmentGroup in segmentGroups:
        type_cable = ''
        thisCable = neuroml.SegmentGroup(id='Cable_%s' %cablenumber, neuro_lex_id='sao864921383')
        for qq in range(0,len(segmentGroup)):
            seg = segmentGroup[-1-qq]
            thismem = neuroml.Member(segments=seg)
            thisCable.members.append(thismem)
            type_this_seg = type_seg[seg]
            if type_cable != '':
                if type_cable != type_this_seg:
                    print("Error; cable %s has multiple types!" %cablenumber)
            else:
                type_cable = type_this_seg
        cables[cablenumber] = thisCable
        thiscab_include = neuroml.Include(segment_groups='Cable_%s' %cablenumber)
        all_cables.includes.append(thiscab_include)
        if type_cable == 'soma':
            all_somas.includes.append(thiscab_include)
        elif type_cable == 'axon':
            all_axons.includes.append(thiscab_include)
        elif type_cable == 'dend':
            all_dendrites.includes.append(thiscab_include)

        type_cab[cablenumber] = type_cable

        cablenumber += 1


    for cab in range(1,len(cables)+1):
        nml_mor.segment_groups.append(cables[cab])

    nml_mor.segment_groups.append(all_cables)
    nml_mor.segment_groups.append(all_dendrites)
    nml_mor.segment_groups.append(all_somas)
    nml_mor.segment_groups.append(all_axons)

    nml_cell.morphology = nml_mor
    
    return nml_cell
    
    # We have now processed all segments


# In[88]:


def define_biophysical_properties(nml_cell, Cell_ID):
    # Create the Biophysical properties:

    all_prop = neuroml.BiophysicalProperties(id='%s_properties' %Cell_ID)

    membraneprop = neuroml.MembraneProperties()
    intraprop = neuroml.IntracellularProperties()

    spthr = neuroml.SpikeThresh(value='0.0 mV')
    specCap = neuroml.SpecificCapacitance(value='1.0 uF_per_cm2')
    initmembpot = neuroml.InitMembPotential(value='-60.0 mV')

    resi = neuroml.Resistivity(value='0.03 kohm_cm')

    membraneprop.spike_threshes.append(spthr)
    membraneprop.specific_capacitances.append(specCap)
    membraneprop.init_memb_potentials.append(initmembpot)

    intraprop.resistivities.append(resi)

    all_prop.membrane_properties = membraneprop
    all_prop.intracellular_properties = intraprop

    nml_cell.biophysical_properties = all_prop
    
    return nml_cell


# In[97]:


def print_statistics(d, segmentGroups):
    # Here the statistics that we want to know can be printed
    
    total_area = 0
    total_volume = 0
    
    for Group in segmentGroups:
        for seg in Group:
            isroot = False
            par = d[seg][5]
            if par == -1:
                isroot = True
            
            if isroot == True:
                radius = d[seg][4]
                segment_area = 4*math.pi*(radius**2)
                segment_volume = (4/3)*math.pi*(radius**3)
                total_area = total_area + segment_area
                total_volume = total_volume + segment_volume
            elif isroot == False:
                radius = d[seg][4]
                radius_par = d[par][4]
                x, y, z = d[seg][1], d[seg][2], d[seg][3]
                xpar, ypar, zpar = d[par][1], d[par][2], d[par][3]
                distance = math.sqrt((x-xpar)**2 + (y-ypar)**2 + (z-zpar)**2)
                if radius != radius_par:
                    f = math.sqrt((distance-radius+radius_par)*(distance+radius-radius_par))/distance
                    segment_area = math.pi*(f**2)*((distance/abs(radius-radius_par))+1)*abs(radius**2 - radius_par**2)

                    segment_volume = (1/3)*math.pi*(f**4)*(distance/abs(radius_par-radius))*abs(radius**3 - radius_par**3)

                    
                else:
                    segment_area = 2*math.pi*radius*distance
                    segment_volume = math.pi*(radius**2)*distance
                
                total_area = total_area + segment_area
                total_volume = total_volume + segment_volume
    
    print("The total area of this neuron is: %s" %total_area)
    print("The total volume of this neuron is: %s" %total_volume)
    print("The area to volume ratio (A/V) of this neuron is: %s" %(total_area/total_volume))
    print(">-------<")


# In[98]:
for neuron_id in range(1, 10):
    swc_file = api2.create_swc_file(neuron_id, 'map swc files')
    nml_file_name = convert_to_nml(swc_file, 'map nml files')
    print('Converted the following file: %s' %nml_file_name)


# swc_file = 'neuron_1.swc' # Insert the path of the swc-file here
# nml_file_name = convert_to_nml(swc_file)
# print('Converted the following file: %s' %nml_file_name)


# In[ ]:





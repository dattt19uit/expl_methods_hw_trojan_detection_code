# linux (-i stay in interpreter): python3 -i s27_test2.py
#
# dot -Tpng s27.dot > s27_dot.png
# dot -Nshape=box graph.dot -Tpng -o graph.png    # default node shape
# eog s27_dot.png
# evince nand2.eps
# exec(open('s27_test2.py').read())    # include a file

import sys
import os
# Add circuitgraph from xai_shared package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'circuitgraph'))
import circuitgraph as cg

import sys
import os
import time

import networkx as nx
import pylab as plt        # not used
from   networkx.drawing.nx_agraph import graphviz_layout, to_agraph
import pygraphviz as pgv   # not used

# https://graphviz.org/doc/info/shapes.html
def graph_cells(c, filename="netlistx_graph", boxes=['SDFFSRX1', 'DFFARX1', 'DFFASX1', 'DFFNX2', 'DFFX2', 'SDFFX1', 'LSDNENX1', 'LSDNX1', 'ff']):
    #flops_cycle()
    #
    c.graph.graph['edges']={'arrowsize':'4.0'}
    #c.graph.graph['graph']={'rankdir':'LR'}
    c.graph.add_nodes_from(c.outputs(),style='filled',fillcolor='green',shape='house',orientation=180) 
    c.graph.add_nodes_from(c.inputs(), style='filled',fillcolor='yellow',shape='house',orientation=180)
    for cell in c.blackboxes:                   # U7
        cell_name    = c.blackboxes[cell].name  # NAND2X1
        print(cell_name)
        if cell_name in boxes:
            for port in c.blackboxes[cell].inputs() | c.blackboxes[cell].outputs():  # set union, not list addition
                cell_port = f"{cell}.{port}"
                print("   ", cell_port)
                if cell_port in c.graph.nodes:
                   print("   ***", cell_port)
                   c.graph.add_nodes_from([cell_port],style='filled',fillcolor='lightblue',shape='rectangle',orientation=0)

    # returns a pygraphviz graph from a networkx graph c.graph
    A = to_agraph(c.graph)  # same as nx.nx_agraph.to_agraph(c.graph) where c.graph is directed or undirected
    #
    #A.add_subgraph(['DFF_0_Q_reg.D','DFF_0_Q_reg.CK','DFF_0_Q_reg.Q'], name = 'cluster1', color='red')
    #A.add_subgraph(['DFF_1_Q_reg.D','DFF_1_Q_reg.CK','DFF_1_Q_reg.Q'], name = 'cluster2', color='red')
    #A.add_subgraph(['DFF_2_Q_reg.D','DFF_2_Q_reg.CK','DFF_2_Q_reg.Q'], name = 'cluster3', color='red')
    #
    #A.add_subgraph(['DFF_0_Q_reg.D','DFF_0_Q_reg.CK','DFF_0_Q_reg.Q'], name = 'cluster1', color='red', label='DFF_0_Q_reg')
    #A.add_subgraph(['DFF_1_Q_reg.D','DFF_1_Q_reg.CK','DFF_1_Q_reg.Q'], name = 'cluster2', color='red', label='DFF_1_Q_reg')
    #A.add_subgraph(['DFF_2_Q_reg.D','DFF_2_Q_reg.CK','DFF_2_Q_reg.Q'], name = 'cluster3', color='red', label='DFF_2_Q_reg')
    #
    # Big graphs: too slow
    # A.layout('dot'); A.layout() same as A.layout('neato'); A.layout('fdp -Goverlap=true')
    # sfdp Error: remove_overlap: Graphviz not built with triangulation library
    # ValueError: Program fdp -Goverlap=true is not one of: tred, fdp, osage, gvpr, patchwork, sfdp, ccomps, gc,
    #                          unflatten, neato, circo, dot, sccmap, nop, acyclic, gvcolor, twopi
    #
    A.layout('dot')              # graphviz layout engine: dot=directed graphs
    A.write(filename + '.dot')
    # linux: eog s27.png &
    A.draw(filename + '.pdf')    # draw graph A with matplotlib
    #A.draw('RS232-T1300_180nm_uart.pdf', format='pdf')
    #png = A.draw('RS232-T1300_180nm_uart.svg', format='svg')
    #png[0:10]

# Useful for debugging: https://www.w3schools.com/python/python_regex.asp#findall
def flops_cycle(c):
    try:
        t = nx.find_cycle(c.graph, orientation="original")
        print("cycle:", t)
        [u for u,v,w in t]
        w = [(u,v) for u,v,w in t]
        c.graph.add_edges_from(w,color='green')
    except nx.exception.NetworkXNoCycle:
        print('no cycle')

def zero_nodes(c):
    total=0
    r =[]
    for n in c.graph.nodes: # can't delete nodes while in for loop
        if c.graph.out_degree(n)==0 and c.graph.in_degree(n)==0:
            r.append(n)
            total = total + 1
    print(r)
    for i in range(total):
        c.graph.remove_node(r[i])
    print('total=', total)

# Difficult cases, how to count nets, RS232-T1000
#    assign \test_point/TM  = test_mode;  # wire=input
#    assign test_so = rec_dataH_temp[7];  # output=wire
# Q==>Out       ('rec_dataH_reg_0_.Q'      ==> 'rec_dataH[0]'),
# Q==>Wire=>Out ('rec_dataH_temp_reg_7_.Q' ==> 'rec_dataH_temp[7]' ==> 'test_so')                                                                
#
def stats(c):
    print("blackboxes=", len(list(c.blackboxes)))
    print("nodes=", len(c.graph.nodes))
    print("edges=", len(c.graph.edges))
    PI = [n for n in c.graph.nodes if c.graph.nodes[n]['type']=='input']
    print("PI=", len(PI), len(list(c.inputs())),  len(c.graph.in_edges(PI)), len(c.graph.out_edges(PI))) # primary inputs
    PO = [n for n in c.graph.nodes if c.graph.nodes[n]['output']==True]
    print("PO=", len(PO), len(list(c.outputs())), len(c.graph.in_edges(PO)), len(c.graph.out_edges(PO))) # primary outputs
    w_nodes = len([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='wire'])                    #=280
    w_in    = len(c.graph.in_edges([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='wire']))  #=280
    w_out   = len(c.graph.out_edges([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='wire'])) #=535
    print(f"wires={w_nodes:4d}, in_edges={w_in:4d}, out_edges={w_out:4d}")
    # c.graph.nodes['tie_0']  # {'type': '0', 'output': False}
    w_nodes = len([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='0'])                    #=280
    w_in    = len(c.graph.in_edges([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='0']))  #=280
    w_out   = len(c.graph.out_edges([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='0'])) #=535
    print(f"tie_0={w_nodes:4d}, in_edges={w_in:4d}, out_edges={w_out:4d}")
    w_nodes = len([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='1'])                    #=280
    w_in    = len(c.graph.in_edges([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='1']))  #=280
    w_out   = len(c.graph.out_edges([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='1'])) #=535
    print(f"tie_1={w_nodes:4d}, in_edges={w_in:4d}, out_edges={w_out:4d}")
    w_nodes = len([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='x'])                    #=280
    w_in    = len(c.graph.in_edges([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='x']))  #=280
    w_out   = len(c.graph.out_edges([n for n in c.graph.nodes if c.graph.nodes[n]['type']=='x'])) #=535
    print(f"tie_x={w_nodes:4d}, in_edges={w_in:4d}, out_edges={w_out:4d}")
    zeros = 0
    ins   = 0
    outs  = 0
    bufs  = 0
    nots  = 0
    nands = 0
    nors  = 0
    ands  = 0
    ors   = 0
    xors  = 0

    for n in c.graph.nodes: # can't delete nodes while in for loop
        if c.graph.out_degree(n)==0 and c.graph.in_degree(n)==0:
            zeros = zeros + 1
        if c.graph.out_degree(n)==0 and c.graph.in_degree(n)!=0:
            ins = ins + 1
        if c.graph.out_degree(n)!=0 and c.graph.in_degree(n)==0:
            outs = outs + 1
        if c.graph.nodes[n]['type']=='buf':
            bufs = bufs + 1
        if c.graph.nodes[n]['type']=='not':
            nots = nots + 1
        if c.graph.nodes[n]['type']=='nand':
            nands = nands + 1
        if c.graph.nodes[n]['type']=='and':
            ands = ands + 1
        if c.graph.nodes[n]['type']=='nor':
            nors = nors + 1
        if c.graph.nodes[n]['type']=='or':
            ors = ors + 1
        if c.graph.nodes[n]['type']=='xor':
            xors = xors + 1

    print(f"{zeros:4d} isolates")
    print(f"{ins:4d} ins")
    print(f"{outs:4d} outs")
    print(f"{bufs:4d} bufs")
    print(f"{nots:4d} nots")
    print(f"{nands:4d} nands")
    print(f"{ands:4d} ands")
    print(f"{nors:4d} nors")
    print(f"{ors:4d} ors")
    print(f"{xors:4d} xors")
    print(f"{nots+nands+ands+nors+ors+xors:4d} primative logic")

    print("")
    cn        = "CellName"
    D         = "Declared"    # Declared cells, original total when first read in
    U         = "Instance"    # Cell instances currently in graph, i.e. remove_cells(['wire'])
    fanin     = "Fanin"       # in ports edges, fanin
    fanout    = "Fanout"      # out ports edges, fanout
    Uout_port = "OutPort"     # actual connected out ports to anything
    UoutW_port= "OutWire"     # actual connected out ports to a wire
    print(f"{cn:12s} {D:>8s} {U:>8s} {fanin:>8s} {fanout:>8s} {Uout_port:>8s} {UoutW_port:>8s}")
    D_total      = 0        # declared total
    U_total      = 0
    fanin_total  = 0
    fanout_total = 0
    Uout_total   = 0
    UoutW_total  = 0
    Uout_unconnected = []
    Uin_unconnected  = []
    for cn in list_cell_names(c):            # declared cn in {'AND2X4', 'DFFASX1', 'XOR2X2', 'MUX21X1', 'NBUFFX16',
        declared   = list_cell_instances(c, [cn]) # declared cell instance dictionary: ci = ['U304', 'U303', 'U128', 'U127', 
        U_graph    = []                        # list of actual instances
        Uin_graph  = []                        # list of actual input ports to instances
        Uout_graph = []                        # list of actual output ports to instances
        UoutW_graph = []
        for U in declared:                     # for every declared instance U = 'U304'; check it it still exists
            outputs = c.blackboxes[U].outputs()   # declared outputs
            for port in outputs:                  # for every declared output port = [Q, QN, ...]
                Uout = f"{U}.{port}"                  # declared ='U304.Q'
                if Uout in c.graph.nodes:             # if declared 'U304.Q' in the graph
                   # print(Uout, outputs, Uout_graph)
                   if c.graph.out_edges(Uout)==0:          # if connected edge
                      Uout_unconnected.append(Uout)
                   else:
                      Uout_graph.append(Uout)               # then count all actual out ports
                      for u,w in c.graph.out_edges(Uout):
                          if c.graph.nodes[w]['type']=='wire':
                              UoutW_graph.append(Uout)
                   if U not in U_graph:               # if declared 'U304' in the graph
                      U_graph.append(U)                   # actual cell count, U304
                else:
                    Uout_unconnected.append(Uout)
            inputs = c.blackboxes[U].inputs()
            for port in inputs:                # port = [IN1, IN2, ...]
                Uin = f"{U}.{port}"                # ='U304.IN1'
                if Uin in c.graph.nodes:           # if declared 'U304.IN1' in the graph
                   if c.graph.in_edges(Uin)==0:          # if connected edge
                      Uin_unconnected.append(Uin)
                   else:
                      Uin_graph.append(Uin)              # count all in ports
                   if U not in U_graph:
                      U_graph.append(U)                  # actual cell count, U304
                else:
                    Uin_unconnected.append(Uin)
        D_total       += len(declared)
        U_total       += len(U_graph)
        fanin          = len(c.graph.in_edges(Uin_graph))+len(c.graph.in_edges(Uout_graph)) # BBs by default are empty, outputs disconnected
        fanin_total   += fanin                           # merge_cells(), outputs will have fanin
        fanout         = len(c.graph.out_edges(Uout_graph))+len(c.graph.out_edges(Uin_graph)) # 
        fanout_total  += fanout
        Uout_port      = len(Uout_graph)
        Uout_total    += Uout_port
        UoutW_port     = len(UoutW_graph)
        UoutW_total   += UoutW_port
        print(f"{cn:12s} {len(declared):8d} {len(U_graph):8d} {fanin:8d} {fanout:8d} {Uout_port:8d} {UoutW_port:8d}")
    print(f"total cells  {D_total:8d} {U_total:8d} {fanin_total:8d} {fanout_total:8d} {Uout_total:8d} {UoutW_total:8d}")
    print("")
    #print("UoutW total=",      UoutW_total)
    #print("UoutW total=",      UoutW_graph)
    print("Uout_unconnected=",  len(Uout_unconnected))
    #print("Uout_unconnected=", Uout_unconnected)
    print("Uin_unconnected=",   len(Uin_unconnected))
    #print("Uin_unconnected=",  Uin_unconnected)

    W_unconnected = []  # wire must be connected to a single output and one or more input signals
    for n in c.graph.nodes:
        if c.graph.nodes[n]['type']=='wire':   # instances in graph
            if c.graph.in_edges(n)==0 or c.graph.out_edges(n)==0:  # could be two inputs connected
                W_unconnected.append(n)
            # add code for detecting a single output and at least an input
    print("W_unconnected=", len(W_unconnected))
    print("W_unconnected=", W_unconnected)

# list_cell_instances(['AND2X4']) # = ['U304', 'U303', 'U128', 'U127', 'U126', 'U125', 'U124', 'U108', 'U90', 'U89', 'U88', 'U87']
# list_cell_instances(['ff'])     # = ['DFF_0_Q_reg', 'DFF_1_Q_reg', 'DFF_2_Q_reg']
#
def list_cell_instances(c, cell_names):
    return [ bb for bb in c.blackboxes if c.blackboxes[bb].name in cell_names]
#    [ bb for bb in c.blackboxes if c.blackboxes[bb].name in ['ff']]
#    instances = []
#    for bb in c.blackboxes:
#        bb_name    = c.blackboxes[bb].name
#        if c.blackboxes[bb].name in cell_names:
#            instances.append(bb_name)

# list_cell_names([])                  ==> {'ff'}
# list_cell_names().difference({'ff'})
# list_cell_names()-{'ff'}             ==> set()
# list_cell_names([])                  ==> {'AND2X4', 'DFFASX1', 'XOR2X2', 'MUX21X1', 'NBUFFX16',
def list_cell_names(c):
    return { c.blackboxes[bb].name for bb in c.blackboxes}

def add_blackbox_primitives(c):
    return { c.blackboxes[bb].name for bb in c.blackboxes}

# [print(n,c.graph.nodes[n]['type']) for n in c.graph.nodes ] # type=input, output, bb_input, bb_output, wire, buf, not, ...
# [print(n,c.graph.nodes[n]['type']) for n in c.graph.nodes if c.graph.nodes[n]['type'] in cell_primitives ]
#
def list_primitive_instances(c):
    return [n for n in c.graph.nodes if c.graph.nodes[n]['type'] in cell_primitives ]

def remove_blackboxes(c, cell_names):
    cell_instances = list_cell_instances(cell_names)  # ['U7', 'U300']
    new_edges = []
    removals  = []

    for cell in cell_instances:  # ['U7', 'U300'] # RuntimeError: dictionary changed size during iteration
        for cell_out in c.blackboxes[cell].outputs():               # Multiple outputs, Q, QN
            n = f"{cell}.{cell_out}"
            if n in c.graph.nodes and c.graph.out_degree(n)!=0 and c.graph.in_edges(n)!=0:
                destination = []
                for _, dst in c.graph.out_edges(n):
                    destination.append(dst)
                for src, _ in c.graph.in_edges(n):
                    for dst in destination:
                        new_edges.append((src, dst))
                if n not in removals:
                    removals.append(n)
            else:
                print("Error: wire does not have a source or destination", n)
                exit()

    c.graph.add_edges_from(new_edges)
    #print("removals", len(removals))
    for n in removals:
        c.graph.remove_node(n)
    print("total removals", len(removals))

def join_cells(c):   # makes it easier to read graph1() .png
    for bb in c.blackboxes:
        bb_outputs = c.blackboxes[bb].outputs()          # 'Y', 'Q', 'QN'
        for bb_out in bb_outputs:
            bb_out_pin = f"{bb}.{bb_out}"                # U300.Y
            if bb_out_pin in c.graph.nodes:
                for bb_in in c.blackboxes[bb].inputs():  # 'A', 'B', 'D', 'CK'
                    bb_in_pin = f"{bb}.{bb_in}"          # U300.A
                    if bb_in_pin in c.graph.nodes:
                        if (bb_in_pin, bb_out_pin) not in c.graph.edges:
                            c.graph.add_edge(bb_in_pin, bb_out_pin)  # edge(U300.A, U300.Y)

def unjoin_cells(c):   # makes it easier to read graph1() .png
    for bb in c.blackboxes:
        bb_outputs = c.blackboxes[bb].outputs()          # 'Y', 'Q', 'QN'
        for bb_out in bb_outputs:
            bb_out_pin = f"{bb}.{bb_out}"                # U300.Y
            if bb_out_pin in c.graph.nodes:
                for bb_in in c.blackboxes[bb].inputs():  # 'A', 'B', 'D', 'CK'
                    bb_in_pin = f"{bb}.{bb_in}"          # U300.A
                    if bb_in_pin in c.graph.nodes:
                        if (bb_in_pin, bb_out_pin) in c.graph.edges:
                            c.graph.remove_edge(bb_in_pin, bb_out_pin)  # edge(U300.A, U300.Y)

# remove logis but keep input, output and wire
#     remove_cell_names(['nand', 'nor', 'not', 'buf', 'ff', 'NAND2X1'])
# remove_cell_names(list_cell_names())
# remove_cell_names(['wire'])
#
def remove_cells(c, node_types):
    total     = 0
    node_list = []
    for n in c.graph.nodes:  # Avoid RuntimeError: dictionary changed size during iteration
        if c.graph.nodes[n]['type'] in node_types:
            if n not in node_list:
                node_list.append(n)
        elif n.split('.')[0] in c.blackboxes:   # U1.A, U1.B, U1.Y
            if c.blackboxes[n.split('.')[0]].name in node_types:
                if n not in node_list:
                    node_list.append(n)
    #### print(node_list)
    for n in node_list:
        if c.graph.out_degree(n)!=0 and c.graph.in_edges(n)!=0:
            destination = []
            for _, dst in c.graph.out_edges(n):
                if dst not in destination:     # may have repeating destination nodes
                    destination.append(dst)
            for src, _ in c.graph.in_edges(n): # may have repeating src nodes
                for dst in destination:
                    if (src, dst) not in c.graph.edges:
                        c.graph.add_edge(src, dst)
            if n in c.graph.nodes:
                total = total + 1
                c.graph.remove_node(n)
        else:
            # unconnected blackbox buf: no edges, U1.A and U1.Y
            # connected blackbox buf: edge (U1.A, U1.Y)
            print(f"Warning: {n} does not have a source or destination: black box not connected, join_cells, merge_cells", n)
            #exit()
    #print("total node removals", total, len(node_list))
    print("total node removals", total)

# merge_cells(c, list_cell_names())
#
# nl.list_cell_names(c) ==> set ==> {'DFFARX1', 'NOR2X4', 'NOR3X0', 'INVX32', 'NAND2X4'}
#
# Bug #1: Need to remove unconnected outputs, wires in remove_wires
#
# Bug #2: Need to merge .Q and .QN: only .QN gets inputs connected, .Q has no inputs
#
# DFFARX1 DFF_4_Q_reg(.CLK (clk),.D (n_6),  .Q (n_31), .QN(n_30),  .RSTB(1'b1)); // Dual Node Test .Q, .QN
#
def merge_cells(c, Include_Cells):                 # merge_blackboxes([]), assumes empty blackboxes
    total = 0
    for U in c.blackboxes:                                # cell instance ['U7', 'U300']
        U_name    = c.blackboxes[U].name                  # cell name: NAND2X1
        if U_name in Include_Cells:                       # cell DFFARX1 has ports Q and QN, NAN2X1 has only Q
            for U_out in c.blackboxes[U].outputs():       # Multiple output ports, Q, QN
                N_out = f"{U}.{U_out}"                    # Graphical Node output port, U300.Q
                # print('$$$ N_out=', N_out)
                if N_out in c.graph.nodes:
                    Wires = []
                    for (Port,W) in c.graph.out_edges(N_out):
                        # print('$$$*** N_out=', N_out, Port, "Wire=", W, c.graph.out_edges(W))
                        if W not in c.outputs():               # primary output (PO) is disconnected
                            if len(c.graph.out_edges(W))==0:       # disconnected wire due to .Q() or .QN() from lark parsing
                                # print('   $$$*** N_out=', N_out, Port, "Wire=", W)
                                if W not in Wires:
                                    Wires.append(W)
                    for W in Wires:
                        c.graph.remove_node(W)     # solves bug #1, remove wire node and edges
                        total = total + 1             # ...then later in this code .Q will be removed
                    c.graph.nodes[N_out]['label']=f"{U} {U_name}" # Marking does not changed size of dictionary
                    if c.graph.in_degree(N_out)!=0:               # internally connected Output port, or called this function before
                        print(f"Warning already internally connected, skipping merge of {N_out}")
                    elif c.graph.out_degree(N_out)==0:            # Unconnected Output port, Example, QN of a flip Flop,
                        #print("delete", N_out, c.graph.out_degree(N_out), c.graph.in_degree(N_out))
                        c.graph.remove_node(N_out)                # removes isolated node or internally connected input
                        total = total + 1
                    else: # Output port is connected
                        for U_in in c.blackboxes[U].inputs():
                            N_in = f"{U}.{U_in}"
                            #print("U_in", U_in, N_in)
                            if N_in in c.graph.nodes:             # primitive blackboxes will have more ports than instances
                                Dst_N_in = [d for (s,d) in c.graph.in_edges(N_in) if s==N_in] # should return an empty list
                                for N in Dst_N_in:                # verify internal blackbox cell connections
                                    N_outputs = [f"{U}.{U_out}" for U_out in c.blackboxes[U].outputs()]
                                    if N not in N_outputs:  # Due join_blackboxes()
                                        print(f"Error: input node {N_in} has wrong output cell connection, ", Dst_N_in, N_outputs)
                                for in_src, _ in c.graph.in_edges(N_in):
                                    #print('edge', in_src, s_out)
                                    if (in_src, N_out) not in c.graph.edges:
                                        c.graph.add_edge(in_src, N_out)
            for U_in in c.blackboxes[U].inputs():   # Solves Q/QN bug #2
                N_in = f"{U}.{U_in}"
                if N_in in c.graph.nodes:    # protect overdeletion from multiple calls to merge_cells
                    c.graph.remove_node(N_in)
                    total = total + 1

    print("total input cell nodes removed", total)

# metric_ffo('n_2') # ['n_2', 'n_5', 'n_7', 'n_10', 'n_21', 'DFF_1_Q_reg.D']
# list(nx.shortest_simple_paths(c.graph, 'n_2', 'DFF_0_Q_reg.D')) # 0
# list(nx.shortest_simple_paths(c.graph, 'n_2', 'DFF_1_Q_reg.D')) # 6
# list(nx.shortest_simple_paths(c.graph, 'n_2', 'DFF_r_Q_reg.D')) # 0

# define FFi to be the minimum gate level to any flip-flop inputs from the target net n
# *** What if no FF found? combinatorial circuit, s27.v, is mixed
#
# It returns a generator which returns one path at a time from shortest to longest.
#   X = [ [path1], [path2], ... ]
#   X = nx.shortest_simple_paths(G, 0, 5); k = 5; for counter, path in enumerate(X): print(path) if counter == k-1: break
#
# For digraphs this returns a shortest directed path.
# To find paths in the reverse direction use G.reverse(copy=False) first to flip the edge orientation.
# https://networkx.org/documentation/networkx-1.2/reference/generated/networkx.shortest_path.html#networkx.shortest_path
#
# shortest_simple_paths(G, source, target, weight=None)
# This procedure is based on algorithm by Jin Y. Yen [1]. Finding the first K paths requires O(K*N^3) operations.
# [1] Jin Y. Yen, "Finding the K Shortest Loopless Paths in a Network", Management Science, Vol. 17, No. 11, Theory Series (Jul., 1971), pp. 712-716.
# https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.simple_paths.shortest_simple_paths.html
# Dijkstra's algorithm:  O(E + VlogV)
#
def metric_paths(G, start, end, cache=None): # must not have cycle!
    # Caching optimization: avoid re-computing same searches
    if cache is None:
        cache = {}
    
    # Create cache key from start node and targets (converted to hashable frozenset)
    cache_key = (start, frozenset(end))
    if cache_key in cache:
        print(f"    len(start)={len(start)} len(end)={len(end)}, start={start} [CACHED]")
        return cache[cache_key]
    
    print(f"    len(start)={len(start)} len(end)={len(end)}, start={start}")
    # print(f"    end={end}")
    s = []
    for f in end:
        # print(f"    b={start} f={f}")
        try:
            # Use shortest_path instead of shortest_simple_paths for O(V+E) complexity instead of exponential
            p = nx.shortest_path(G, start, f)
            if len(p)>0:
                if len(p)<len(s) or len(s)==0:
                    s = p
        except nx.exception.NetworkXNoPath:
            # print("    NetworkXNoPath")
            pass
        except nx.exception.NodeNotFound:
            # print("    NodeNotFound")
            pass
    print("    return=",s)
    cache[cache_key] = s
    return s

# merge_cells(list_cell_names())
# remove_cells(['not'])
#
def write_metrics(c, trojans, filename):
    start_time = time.perf_counter()
    timing_breakdown = {}
    
    # Phase 1: Initialization
    phase_start = time.perf_counter()
    
    # Build trojan instance set for pin-agnostic matching.
    # Config lists trojan nodes with 90nm pin names (e.g. U293.QN) but 180nm
    # netlists use different pins (e.g. U293.Y). Matching on the instance name
    # (before the '.') makes detection work across technology libraries.
    trojan_instances = set()
    for t in trojans:
        inst = t.split('.', 1)[0] if '.' in t else t
        trojan_instances.add(inst)
    
    Line = 0
    PI = c.inputs()
    PO = c.outputs()
    FF = []                 # flip flops
    for n in c.graph.nodes:
        S = n.split('.', 1)
        U = S[0] if len(S)>=1 else ''   # instance
        P = S[1] if len(S)>=2 else ''   # port
        if U in c.blackboxes:
            # Include all flip-flops and latches for proper metric calculation
            if c.blackboxes[U].name in ['SDFFSRX1', 'DFFARX1', 'DFFASX1', 'DFFNX2', 'DFFX2', 'SDFFX1', 'LSDNENX1', 'LSDNX1', 'ff']:
                FF.append(n)
    timing_breakdown['1_initialization'] = time.perf_counter() - phase_start

    # Phase 2: Graph setup
    phase_start = time.perf_counter()
    GC = c.graph
    GR = nx.DiGraph.reverse(c.graph)
    timing_breakdown['2_graph_reverse'] = time.perf_counter() - phase_start
    
    # Phase 3: Pre-compute all shortest path lengths (OPTIMIZATION: O(V^2 log V) once vs O(N*V*E) repeated searches)
    phase_start = time.perf_counter()
    print(f"\nPre-computing all shortest path lengths...")
    print(f"  Graph nodes: {len(GR.nodes)}, edges: {len(GR.edges)}")
    
    # Compute all-pairs shortest path lengths for both graphs
    # This replaces 4*N individual searches with O(V^2 log V) pre-computation
    all_lengths_GR = dict(nx.all_pairs_dijkstra_path_length(GR, weight=None))
    all_lengths_GC = dict(nx.all_pairs_dijkstra_path_length(GC, weight=None))
    
    print(f"  Pre-computation complete in {time.perf_counter() - phase_start:.3f}s")
    timing_breakdown['3_precompute_paths'] = time.perf_counter() - phase_start
    
    # Phase 4: File setup
    phase_start = time.perf_counter()
    fp = open(filename, "w") 
    fp.write(f"Line,type,name,net,LGFi,ffi,ffo,PI,PO,Trojan\n")
    timing_breakdown['4_file_setup'] = time.perf_counter() - phase_start
    
    # Phase 5: Main metric calculation loop (OPTIMIZED: O(1) lookups instead of O(V+E) searches)
    loop_start = time.perf_counter()
    metrics_time = 0
    path_lookup_time = 0
    write_time = 0
    
    for net in c.graph.nodes:
        Line += 1
        
        # Timing: fanin calculation
        t0 = time.perf_counter()
        gates = list(c.graph.predecessors(net)) # First Logic level fanin
        fanin = []
        for g in gates:
            p = list(c.graph.predecessors(g))   # Second level fanin
            fanin  = fanin + p
        LGFi = len(fanin)
        metrics_time += time.perf_counter() - t0
        
        # Timing: path lookups (OPTIMIZED: O(1) dictionary lookup vs O(V+E) search)
        t0 = time.perf_counter()
        
        # Get pre-computed distances for this node (O(1) dictionary lookup)
        distances_from_net_GR = all_lengths_GR.get(net, {})
        distances_from_net_GC = all_lengths_GC.get(net, {})
        
        # Find shortest distance to flip-flops (ffi and ffo)
        if net in FF:    # Directed graph, make sure shortest path flipflop net will not see itself
            F = [f for f in FF if f != net]
            ffi_dist = min([distances_from_net_GR.get(f, 99999) for f in F if f in distances_from_net_GR], default=99999)
        else:
            ffi_dist = min([distances_from_net_GR.get(f, 99999) for f in FF if f in distances_from_net_GR], default=99999)
        
        ffo_dist = min([distances_from_net_GC.get(f, 99999) for f in FF if f in distances_from_net_GC], default=99999)
        
        # Find shortest distance to primary inputs/outputs
        nPI_dist = min([distances_from_net_GR.get(p, 99999) for p in PI if p in distances_from_net_GR], default=99999)
        nPO_dist = min([distances_from_net_GC.get(p, 99999) for p in PO if p in distances_from_net_GC], default=99999)
        
        path_lookup_time += time.perf_counter() - t0
        
        # Timing: metric computation (using pre-computed distances)
        t0 = time.perf_counter()
        # Match trojan by instance name (pin-agnostic) to handle 90nm/180nm differences
        net_inst = net.split('.', 1)[0] if '.' in net else net
        Trojan = 1 if net_inst in trojan_instances else 0
        
        # Convert distances to path lengths (distance + 1 = path length)
        # Original logic: path length 0 = node itself, 1 = one hop, 2+ = longer paths
        # Distance 0 = same node, distance 1 = one edge, etc.
        # So for metrics: subtract 1 from distance to get "hops" (edges beyond node itself)
        # But if distance is 99999 (no path), keep as 99999
        
        nPO = 0 if net in PO else (99999 if nPO_dist >= 99999 else max(0, nPO_dist - 1))
        nPI = 0 if net in PI else (99999 if nPI_dist >= 99999 else max(0, nPI_dist - 1))
        
        # For flip-flop distances: 
        # - 99999 = no path
        # - Use nPI/nPO if no FF path found
        ffi = nPI if ffi_dist >= 99999 else (0 if ffi_dist <= 1 else ffi_dist - 1)
        ffo = nPO if ffo_dist >= 99999 else (0 if ffo_dist <= 1 else ffo_dist - 1)
        
        if net in ['tie_0', 'tie_1', 'tie_x']:
            nPI = 0
            ffi = 0
        
        ctype = 'PI' if net in PI else 'PO' if net in PO else 'ff' if net in FF else 'nn'
        S = net.split('.', 1)
        U = S[0] if len(S)>=1 else ''   # instance
        cname = c.blackboxes[U].name if U in c.blackboxes else 'net'
        metrics_time += time.perf_counter() - t0

        # Timing: file write
        t0 = time.perf_counter()
        fp.write(f"{Line:07},{ctype},{cname},{net},{LGFi},{ffi},{ffo},{nPI},{nPO},{Trojan}\n")
        write_time += time.perf_counter() - t0
    
    timing_breakdown['5_loop_total'] = time.perf_counter() - loop_start
    timing_breakdown['5a_fanin_metrics'] = metrics_time
    timing_breakdown['5b_path_lookups'] = path_lookup_time
    timing_breakdown['5c_file_writes'] = write_time
    
    fp.close()
    
    # Phase 6: Report timing
    total_time = time.perf_counter() - start_time
    timing_breakdown['6_total'] = total_time
    
    # Print timing summary with optimization comparison
    print(f"\n{'='*70}")
    print(f"CIRCUIT METRICS EXTRACTION TIMING (OPTIMIZED)")
    print(f"{'='*70}")
    print(f"Circuit nodes: {len(c.graph.nodes)}, Flip-flops: {len(FF)}")
    print(f"\nPhase Breakdown:")
    print(f"  1. Initialization:        {timing_breakdown['1_initialization']:8.3f}s")
    print(f"  2. Graph reverse:         {timing_breakdown['2_graph_reverse']:8.3f}s")
    print(f"  3. Pre-compute paths:     {timing_breakdown['3_precompute_paths']:8.3f}s  <- NEW: O(V^2 log V)")
    print(f"  4. File setup:            {timing_breakdown['4_file_setup']:8.3f}s")
    print(f"  5. Main loop (total):     {timing_breakdown['5_loop_total']:8.3f}s")
    print(f"     a. Fanin/metrics:      {timing_breakdown['5a_fanin_metrics']:8.3f}s ({100*timing_breakdown['5a_fanin_metrics']/timing_breakdown['5_loop_total']:.1f}%)")
    print(f"     b. Path lookups:       {timing_breakdown['5b_path_lookups']:8.3f}s ({100*timing_breakdown['5b_path_lookups']/timing_breakdown['5_loop_total']:.1f}%)  <- OPTIMIZED: O(1)")
    print(f"     c. File writes:        {timing_breakdown['5c_file_writes']:8.3f}s ({100*timing_breakdown['5c_file_writes']/timing_breakdown['5_loop_total']:.1f}%)")
    print(f"\nTotal time:                 {total_time:8.3f}s")
    print(f"Time per node:              {1000*total_time/len(c.graph.nodes):8.3f}ms")
    print(f"{'='*70}\n")
    
    return timing_breakdown

# c = nl.read_netlist('./s27_90nm.v', name='s27', fmt='verilog', blackboxes=BB, techlib='90nm')
def read_netlist(filename, name, fmt='verilog', blackboxes=None, techlib='default'):
    BB = []
    if techlib == '180nm':
        BUFX1   = cg.BlackBox(name="BUFX1",    inputs=["A"], outputs=["Y"])
        INVX1   = cg.BlackBox(name="INVX1",    inputs=["A"], outputs=["Y"])
        NOR2X1  = cg.BlackBox(name="NOR2X1",   inputs=["A", "B"], outputs=["Y"])
        NAND2X1 = cg.BlackBox(name="NAND2X1",  inputs=["A", "B"], outputs=["Y"])
        AND2X1  = cg.BlackBox(name="AND2X1",   inputs=["A", "B"], outputs=["Y"])
        XOR2X1  = cg.BlackBox(name="XOR2X1",   inputs=["A", "B"], outputs=["Y"])
        OR2X1   = cg.BlackBox(name="OR2X1",    inputs=["A", "B"], outputs=["Y"])
        MX2X1   = cg.BlackBox(name="MX2X1",    inputs=["A", "B", "S0"], outputs=["Y"])
        NAND3X1 = cg.BlackBox(name="NAND3X1",  inputs=["A", "B", "C"], outputs=["Y"])
        OR4X1   = cg.BlackBox(name="OR4X1",    inputs=["A", "B", "C", "D"], outputs=["Y"])
        NAND4X1 = cg.BlackBox(name="NAND4X1",  inputs=["A", "B", "C", "D"], outputs=["Y"])
        OAI21X1 = cg.BlackBox(name="OAI21X1",  inputs=["A0", "A1", "B0"], outputs=["Y"])
        AOI21X1 = cg.BlackBox(name="AOI21X1",  inputs=["A0", "A1", "B0"], outputs=["Y"])
        AOI22X1 = cg.BlackBox(name="AOI22X1",  inputs=["A0", "A1", "B0", "B1"], outputs=["Y"])
        SDFFSRX1= cg.BlackBox(name="SDFFSRX1", inputs=["D", "CK", "SN", "RN", "SI", "SE"], outputs=["Q", "QN"])

        BB = [BUFX1, INVX1, NOR2X1, NAND2X1, AND2X1, XOR2X1, OR2X1, MX2X1,
             NAND3X1, OR4X1, NAND4X1, OAI21X1, AOI21X1, AOI22X1, SDFFSRX1]

    elif techlib == '90nm':
        # 90nm
        # https://web.engr.oregonstate.edu/~traylor/ece474/reading/SAED_Cell_Lib_Rev1_4_20_1.pdf
        #
        NBUFFX2  = cg.BlackBox(name="NBUFFX2",  inputs=["IN"],         outputs=["Q"])
        NBUFFX16 = cg.BlackBox(name="NBUFFX16", inputs=["IN"],         outputs=["Q"])
        INVX0    = cg.BlackBox(name="INVX0",    inputs=["IN"],         outputs=["QN"])
        INVX8    = cg.BlackBox(name="INVX8",    inputs=["IN"],         outputs=["QN"])
        INVX32   = cg.BlackBox(name="INVX32",   inputs=["IN"],         outputs=["QN"])
        NOR2X0   = cg.BlackBox(name="NOR2X0",   inputs=["IN1", "IN2"], outputs=["QN"])
        NOR2X4   = cg.BlackBox(name="NOR2X4",   inputs=["IN1", "IN2"], outputs=["QN"])
        NOR2X1   = cg.BlackBox(name="NOR2X1",   inputs=["IN1", "IN2"], outputs=["QN"])
        NOR2X2   = cg.BlackBox(name="NOR2X2",   inputs=["IN1", "IN2"], outputs=["QN"])
        NAND2X0  = cg.BlackBox(name="NAND2X0",  inputs=["IN1", "IN2"], outputs=["QN"])
        NAND2X1  = cg.BlackBox(name="NAND2X1",  inputs=["IN1", "IN2"], outputs=["QN"])
        NAND2X4  = cg.BlackBox(name="NAND2X4",  inputs=["IN1", "IN2"], outputs=["QN"])
        AND2X1   = cg.BlackBox(name="AND2X1",   inputs=["IN1", "IN2"], outputs=["Q"])
        AND2X4   = cg.BlackBox(name="AND2X4",   inputs=["IN1", "IN2"], outputs=["Q"])
        AND2X2   = cg.BlackBox(name="AND2X2",   inputs=["IN1", "IN2"], outputs=["Q"])
        OR2X1    = cg.BlackBox(name="OR2X1",    inputs=["IN1", "IN2"], outputs=["Q"])
        XOR2X1   = cg.BlackBox(name="XOR2X1",   inputs=["IN1", "IN2"], outputs=["Q"])
        XOR2X2   = cg.BlackBox(name="XOR2X2",   inputs=["IN1", "IN2"], outputs=["Q"])
        XNOR2X1  = cg.BlackBox(name="XNOR2X1",  inputs=["IN1", "IN2"], outputs=["Q"])
        ISOLORX8 = cg.BlackBox(name="ISOLORX8", inputs=["D", "ISO"],   outputs=["Q"])
        ISOLANDX1= cg.BlackBox(name="ISOLANDX1",inputs=["D", "ISO"],   outputs=["Q"])
        MUX21X1  = cg.BlackBox(name="MUX21X1",  inputs=["IN1", "IN2", "S"],   outputs=["Q"])
        MUX21X2  = cg.BlackBox(name="MUX21X2",  inputs=["IN1", "IN2", "S"],   outputs=["Q"])
        NOR3X0   = cg.BlackBox(name="NOR3X0",   inputs=["IN1", "IN2", "IN3"], outputs=["QN"])
        NAND3X0  = cg.BlackBox(name="NAND3X0",  inputs=["IN1", "IN2", "IN3"], outputs=["QN"])
        NAND3X4  = cg.BlackBox(name="NAND3X4",  inputs=["IN1", "IN2", "IN3"], outputs=["QN"])
        NAND3X1  = cg.BlackBox(name="NAND3X1",  inputs=["IN1", "IN2", "IN3"], outputs=["QN"])
        AND3X1   = cg.BlackBox(name="AND3X1",   inputs=["IN1", "IN2", "IN3"], outputs=["Q"])
        OR3X1    = cg.BlackBox(name="OR3X1",    inputs=["IN1", "IN2", "IN3"], outputs=["Q"])
        XOR3X1   = cg.BlackBox(name="XOR3X1",   inputs=["IN1", "IN2", "IN3"], outputs=["Q"])
        XNOR3X1  = cg.BlackBox(name="XNOR3X1",  inputs=["IN1", "IN2", "IN3"], outputs=["Q"])
        NOR4X0   = cg.BlackBox(name="NOR4X0",   inputs=["IN1", "IN2", "IN3", "IN4"], outputs=["QN"])
        NOR4X1   = cg.BlackBox(name="NOR4X1",   inputs=["IN1", "IN2", "IN3", "IN4"], outputs=["QN"])
        NAND4X0  = cg.BlackBox(name="NAND4X0",  inputs=["IN1", "IN2", "IN3", "IN4"], outputs=["QN"])
        NAND4X1  = cg.BlackBox(name="NAND4X1",  inputs=["IN1", "IN2", "IN3", "IN4"], outputs=["QN"])
        AND4X1   = cg.BlackBox(name="AND4X1",   inputs=["IN1", "IN2", "IN3", "IN4"], outputs=["Q"])
        OR4X1    = cg.BlackBox(name="OR4X1",    inputs=["IN1", "IN2", "IN3", "IN4"], outputs=["Q"])
        OR4X4    = cg.BlackBox(name="OR4X4",    inputs=["IN1", "IN2", "IN3", "IN4"], outputs=["Q"])
        AOI21X1  = cg.BlackBox(name="AOI21X1",  inputs=["IN1", "IN2", "IN3"],                      outputs=["QN"])
        AOI21X2  = cg.BlackBox(name="AOI21X2",  inputs=["IN1", "IN2", "IN3"],                      outputs=["QN"])
        AOI22X1  = cg.BlackBox(name="AOI22X1",  inputs=["IN1", "IN2", "IN3", "IN4"],               outputs=["QN"])
        AOI22X2  = cg.BlackBox(name="AOI22X2",  inputs=["IN1", "IN2", "IN3", "IN4"],               outputs=["QN"])
        AOI221X1 = cg.BlackBox(name="AOI221X1", inputs=["IN1", "IN2", "IN3", "IN4", "IN5"],        outputs=["QN"])
        AOI222X1 = cg.BlackBox(name="AOI222X1", inputs=["IN1", "IN2", "IN3", "IN4", "IN5", "IN6"], outputs=["QN"])
        OAI21X1  = cg.BlackBox(name="OAI21X1",  inputs=["IN1", "IN2", "IN3"],                      outputs=["QN"])
        OAI21X2  = cg.BlackBox(name="OAI21X2",  inputs=["IN1", "IN2", "IN3"],                      outputs=["QN"])
        OAI22X1  = cg.BlackBox(name="OAI22X1",  inputs=["IN1", "IN2", "IN3", "IN4"],               outputs=["QN"])
        OAI22X2  = cg.BlackBox(name="OAI22X2",  inputs=["IN1", "IN2", "IN3", "IN4"],               outputs=["QN"])
        OAI221X1 = cg.BlackBox(name="OAI221X1", inputs=["IN1", "IN2", "IN3", "IN4", "IN5"],        outputs=["QN"])
        OAI222X1 = cg.BlackBox(name="OAI222X1", inputs=["IN1", "IN2", "IN3", "IN4", "IN5", "IN6"], outputs=["QN"])
        AO21X1   = cg.BlackBox(name="AO21X1",   inputs=["IN1", "IN2", "IN3"],                      outputs=["Q"])
        AO22X1   = cg.BlackBox(name="AO22X1",   inputs=["IN1", "IN2", "IN3", "IN4"],               outputs=["Q"])
        AO221X1  = cg.BlackBox(name="AO221X1",  inputs=["IN1", "IN2", "IN3", "IN4", "IN5"],        outputs=["Q"])
        AO222X1  = cg.BlackBox(name="AO222X1",  inputs=["IN1", "IN2", "IN3", "IN4", "IN5", "IN6"], outputs=["Q"])
        OA21X1   = cg.BlackBox(name="OA21X1",   inputs=["IN1", "IN2", "IN3"],                      outputs=["Q"])
        OA22X1   = cg.BlackBox(name="OA22X1",   inputs=["IN1", "IN2", "IN3", "IN4"],               outputs=["Q"])
        OA221X1  = cg.BlackBox(name="OA221X1",  inputs=["IN1", "IN2", "IN3", "IN4", "IN5"],        outputs=["Q"])
        OA222X1  = cg.BlackBox(name="OA222X1",  inputs=["IN1", "IN2", "IN3", "IN4", "IN5", "IN6"], outputs=["Q"])
        DFFARX1  = cg.BlackBox(name="DFFARX1",  inputs=["D", "CLK", "RSTB"],         outputs=["Q", "QN"])
        DFFASX1  = cg.BlackBox(name="DFFASX1",  inputs=["D", "CLK", "SETB"],         outputs=["Q", "QN"])
        DFFNX2   = cg.BlackBox(name="DFFNX2",  inputs=["D", "CLK"],                 outputs=["Q", "QN"])
        SDFFX1   = cg.BlackBox(name="SDFFX1",   inputs=["D", "CLK", "SI", "SE"],     outputs=["Q", "QN"])
        LSDNENX1 = cg.BlackBox(name="LSDNENX1", inputs=["D", "ENB"],                 outputs=["Q"])
        LSDNX1   = cg.BlackBox(name="LSDNX1",   inputs=["D"],                        outputs=["Q"])
        HADDX1   = cg.BlackBox(name="HADDX1",   inputs=["A", "B"],                  outputs=["CO", "S"])
        DFFX2    = cg.BlackBox(name="DFFX2",    inputs=["D", "CLK"],                 outputs=["Q", "QN"])
        NOR3X1   = cg.BlackBox(name="NOR3X1",   inputs=["IN1", "IN2", "IN3"],        outputs=["QN"])
        HighActiveRegionDetection = cg.BlackBox(name="HighActiveRegionDetection", inputs=["clk", "In0", "In1", "In2", "In3", "In4", "In5", "In6", "In7"], outputs=["Trigger_out"])
        TrojanTrigger = cg.BlackBox(name="TrojanTrigger", inputs=["A", "B", "C", "D"], outputs=["Y"])

        BB = [NBUFFX2,  NBUFFX16,  INVX0, INVX8, INVX32,
              NOR2X0,   NOR2X4,    NOR2X1, NOR2X2,
              NAND2X0,  NAND2X1,   NAND2X4,
              AND2X1,   AND2X4,    AND2X2,
              OR2X1,    XOR2X1,    XOR2X2, XNOR2X1,
              ISOLORX8, ISOLANDX1, 
              MUX21X1,  MUX21X2,
              NOR3X0,   NAND3X0,   NAND3X4, NAND3X1,  AND3X1,  OR3X1,    XOR3X1, XNOR3X1, OAI21X2, NOR3X1, 
              NOR4X0,   NOR4X1,   NAND4X0,  NAND4X1, AND4X1,  OR4X1,    OR4X4,
              AOI21X1,  AOI21X2,   AOI22X1, AOI22X2, AOI221X1, AOI222X1, 
              OAI21X1,  OAI21X2,   OAI22X1, OAI22X2, OAI221X1, OAI222X1, 
              AO21X1,              AO22X1,           AO221X1,  AO222X1, 
              OA21X1,              OA22X1,           OA221X1,  OA222X1, 
              DFFARX1,  DFFASX1,   DFFNX2,  DFFX2, SDFFX1,  LSDNENX1,LSDNX1,   HADDX1, HighActiveRegionDetection, TrojanTrigger]

    elif techlib == 'default':
        bb_ff           = cg.BlackBox(name="ff",   inputs=["CK", "D"], outputs=["Q"])
        bb_not          = cg.BlackBox(name="not",  inputs=["A"], outputs=["Y"])
        bb_buf          = cg.BlackBox(name="buf",  inputs=["A"], outputs=["Y"])
        bb_nand         = cg.BlackBox(name="nand", inputs=['A','B','C','D','E','F','G','H','I'], outputs=["Y"])
        bb_nor          = cg.BlackBox(name="nor",  inputs=['A','B','C','D','E','F','G','H','I'], outputs=["Y"])

        BB              = [bb_ff, bb_not, bb_buf, bb_nand, bb_nor]
   
    if blackboxes:
        BB.append(blackboxes)

    c = cg.from_file(filename, name=name, fmt=fmt, 
                     blackboxes=BB, warnings=False, error_on_warning=False, fast=False)
    return c



"""Utils for parsing verilog with Lark."""
import csv
from pathlib import Path

from lark import Lark, Transformer

from circuitgraph import Circuit, primitive_gates

import lark                # lark.Token('Identifier', 'signal[1]')

def _get_context_window(text, index):
    """
    Find the line containing an index.

    Parameters
    ----------
    text: str
            The text to search in
    index: int
            The index to search around

    Returns
    -------
    str
            The line that `index` is contained in.

    """
    previous_newline = max(0, text.rfind("\n", 0, index))
    next_newline = text.find("\n", index)
    context = text[previous_newline:next_newline]
    context += "\n" + " " * (index - previous_newline - 1) + "^"
    return context


class VerilogParsingError(Exception):
    """Raised if there is an issue parsing the verilog."""

    def __init__(self, message, token, text):
        super().__init__()
        self.message = message
        self.token = token
        self.line = getattr(token, "line", "?")
        self.column = getattr(token, "column", "?")
        index = getattr(token, "pos_in_stream", None)
        if index:
            self.context = _get_context_window(text, index)
        else:
            self.context = "?"

    def __str__(self):
        """Print the line and column of the error."""
        self.message += f" (line {self.line}, column {self.column}):\n"
        self.message += self.context
        return self.message


class VerilogParsingWarning(Exception):
    """Potentially raised if there is a warning parsing verilog."""


class _VerilogCircuitGraphTransformer(Transformer):
    """A lark.Transformer for parsing a verilog netlist."""

    def __init__(
        self, text, blackboxes, warnings=False, error_on_warning=False, csv_output_dir=None
    ):
        """
        Initialize a new transformer.

        Parameters
        ----------
        text: str
                The netlist that the transformer will be used on, used for
                error messages.
        blackboxes: list of circuitgraph.BlackBox
                The blackboxes present in the netlist that will be parsed.
        warnings: bool
                If True, warnings about unused nets will be printed.
        error_on_warning: bool
                If True, unused nets will cause raise `VerilogParsingWarning`
                exceptions.
        csv_output_dir: str or pathlib.Path, optional
                Directory in which to write ``nodes.csv`` and ``edges.csv``
                for the parsed circuit.

        """
        super().__init__()
        self.c = Circuit()
        self.text = text
        self.blackboxes = blackboxes
        self.warnings = warnings
        self.error_on_warning = error_on_warning
        self.csv_output_dir = Path(csv_output_dir) if csv_output_dir else None
        self.tie_0 = self.c.add("tie_0", "0")
        self.tie_1 = self.c.add("tie_1", "1")
        self.tie_x = self.c.add("tie_x", "x")
        self.gate_expressions = set()
        self.io = set()            # module port list
        self.inputs = set()        # declared input ports with vectors
        self.outputs = set()       # declared output ports with vectors
        self.wires = set()         # declared wires with vectors
        self.inputs_ports = set()  # NEW declared input ports
        self.outputs_ports = set() # NEW declared output ports
        self.null_ports = 0        # .QN() unused ports

    # Helper functions
    def add_node(self, n, node_type, fanin=None, fanout=None, uid=False):
        """So that nodes are of type `str`, not `lark.Token`."""
        #print("Transformer #1 add_node=", n, node_type, fanin, fanout, uid)
        
        #print("*** Transformer add_node=", n, [str(n) for n in self.wires])
        w = [str(n) for n in self.wires]   # bad implementation
        o = [str(n) for n in self.io]   # bad implementation
        if n in w and n not in o:
            #print(';;;', n,o, list(self.outputs))
            #print('   ;;;', list(self.inputs))
            node_type = 'wire'
        if not fanin:
            fanin = []
        elif type(fanin) not in [list, set]:
            fanin = [fanin]
        if not fanout:
            fanout = []
        elif type(fanout) not in [list, set]:
            fanout = [fanout]

        fanin = [str(i) for i in fanin]
        fanout = [str(i) for i in fanout]
        node_type = str(node_type)
        #print("Transformer #2 c.add_node=", n, node_type, fanin, fanout, uid)
        return self.c.add(
            str(n),
            node_type,
            fanin=fanin,
            fanout=fanout,
            uid=uid,
            add_connected_nodes=True,
            allow_redefinition=True,
        )

    #
    # NAND2X1 U7 ( .A(xmit_dataH[6]), .B(xmit_dataH[7]), .Y(rec_dataH[7]) );
    #
    # NAND2X1 = cg.BlackBox(name="NAND2X1", inputs=["A", "B"], outputs=["Y"])
    # c = cg.from_file('./s00_test3.v', name='uart', fmt='verilog',
    #     blackboxes=[NAND2X1], warnings=True, error_on_warning=True, fast=False)

    # add_blackbox: name=U7
    #  connections={Token('IDENTIFIER', 'A'): Token('IDENTIFIER', 'xmit_dataH[6]'),
    #               Token('IDENTIFIER', 'B'): Token('IDENTIFIER', 'xmit_dataH[7]'), 
    #               Token('IDENTIFIER', 'Y'): Token('IDENTIFIER', 'rec_dataH[7]')}
    def add_blackbox(self, blackbox, name, connections=None):
        #print("add_blackbox:", name, connections)
        if not connections:         # Token to Token dictionary, dict of Token:Token
            connections = {}
        formatted_connections = {}  # convert to string to string dictionary, dict of str:str
        for key in connections:     # for every .A, .B, .C
            formatted_connections[str(key)] = str(connections[key]) # build temporary dictionary .A => xmit_dataH[6]
            if str(connections[key]) not in self.c:
                #print("add_blackbox: add buf", str(connections[key]))
                self.c.add(str(connections[key]), "buf")
        # circuit.py/add_blackbox: self.c.add U7 {'A': 'xmit_dataH[6]', 'B': 'xmit_dataH[7]', 'Y': 'rec_dataH[7]'}
        #### print("_VerilogCircuitGraphTransformer: add_blackbox: self.c.add", str(name), formatted_connections)
        self.c.add_blackbox(blackbox, str(name), formatted_connections) # go to Class Circuit, circuit.py

    def warn(self, message):
        ###if self.error_on_warning:
        ###    raise VerilogParsingWarning(message)
        print(f"Warning: {message}")

    def check_for_warnings(self):
        for wire in self.wires:
            if wire not in self.c.nodes(): # declared but not used in circuit anywhere
                self.warn(f"{wire} declared as wire but isn't connected.")

        for n in self.c.nodes():
            if (
                self.c.type(n) != "bb_input"
                and not self.c.is_output(n)
                and not self.c.fanout(n)
            ):
                self.warn(f"{n} doesn't drive any nets.")
            elif self.c.type(n) not in [
                "input",
                "0",
                "1",
                "bb_output",
            ] and not self.c.fanin(n):
                self.warn(f"{n} doesn't have any drivers.")

    def write_graph_csv(self):
        """Write a structural graph that preserves Verilog nets and cell instances.

        CircuitGraph represents a blackbox instance through separate
        ``bb_input`` and ``bb_output`` pin nodes, without an edge through the
        blackbox. That representation is appropriate for the parser, but it
        splits a netlist visualisation into many disconnected components. The
        CSV representation instead uses the original instance as one node and
        records the connected pin name and direction on every edge.
        """
        if self.csv_output_dir is None:
            return

        self.csv_output_dir.mkdir(parents=True, exist_ok=True)

        raw_nodes = {}
        raw_edges = []

        # Keep every real signal node and its attributes. bb_* nodes are
        # parser-internal port nodes and are represented by the ``port`` edge
        # attribute below rather than as separate CSV nodes.
        for node, attributes in self.c.graph.nodes(data=True):
            if attributes.get("type") not in {"bb_input", "bb_output"}:
                raw_nodes[str(node)] = {"kind": "net", **attributes}

        for instance, blackbox in self.c.blackboxes.items():
            instance = str(instance)
            if instance in raw_nodes:
                raise ValueError(
                    f"Cannot export structural CSV: instance name '{instance}' "
                    "collides with a signal name."
                )
            raw_nodes[instance] = {
                "kind": "cell",
                "type": blackbox.name,
                "cell_type": blackbox.name,
            }

            # Reconstruct each original named/positional port connection:
            # net -> instance for input ports and instance -> net for outputs.
            for port in blackbox.inputs():
                port_node = f"{instance}.{port}"
                if port_node in self.c.graph:
                    for source, _ in self.c.graph.in_edges(port_node):
                        raw_edges.append(
                            (str(source), instance, {"kind": "connection", "port": port, "direction": "input"})
                        )
            for port in blackbox.outputs():
                port_node = f"{instance}.{port}"
                if port_node in self.c.graph:
                    for _, target in self.c.graph.out_edges(port_node):
                        raw_edges.append(
                            (instance, str(target), {"kind": "connection", "port": port, "direction": "output"})
                        )

        # Preserve direct connections created by continuous assignments and
        # primitive expressions. Connections touching bb_* pins were already
        # emitted above with their original cell instance and port.
        for source, target, attributes in self.c.graph.edges(data=True):
            source_type = self.c.graph.nodes[source].get("type")
            target_type = self.c.graph.nodes[target].get("type")
            if source_type not in {"bb_input", "bb_output"} and target_type not in {"bb_input", "bb_output"}:
                raw_edges.append((str(source), str(target), {"kind": "direct", **attributes}))

        # Attributes are not necessarily uniform. Build a complete schema so
        # no source attribute is discarded from either CSV.
        node_attributes = sorted(
            {
                attribute
                for attributes in raw_nodes.values()
                for attribute in attributes
            }
        )
        edge_attributes = sorted(
            {
                attribute
                for _, _, attributes in raw_edges
                for attribute in attributes
            }
        )

        with open(self.csv_output_dir / "nodes.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["node", *node_attributes])
            for node in sorted(raw_nodes):
                attributes = raw_nodes[node]
                writer.writerow([str(node), *(attributes.get(attribute, "") for attribute in node_attributes)])

        with open(self.csv_output_dir / "edges.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["source", "target", *edge_attributes])
            for source, target, attributes in sorted(
                raw_edges, key=lambda edge: (edge[0], edge[1], edge[2].get("port", ""))
            ):
                writer.writerow(
                    [str(source), str(target), *(attributes.get(attribute, "") for attribute in edge_attributes)]
                )

    # 1. Source text
    def start(self, description):
        return description

    def module(self, module_name_and_list_of_ports_and_module_items):
        self.c.name = str(module_name_and_list_of_ports_and_module_items[0])

        # Check if ports list matches with inputs and outputs
        if not self.inputs_ports <= self.io:
            #print("module self.inputs=", len(self.inputs), self.inputs)
            #print("module self.inputs_ports=", len(self.inputs_ports), self.inputs_ports)
            #print("module self.io=", len(self.io), self.io)
            i = (self.inputs_ports - self.io).pop()
            #print("module self.i=", i)
            raise VerilogParsingError(
                f"{i} declared as output but not in port list", i, self.text
            )
        if not self.outputs_ports <= self.io:
            #print("module self.outputs=", self.outputs)
            #print("module self.outputs_ports=", len(self.outputs_ports), self.outputs_ports)
            #print("module self.io=", self.io)
            o = (self.outputs_ports - self.io).pop()
            raise VerilogParsingError(
                f"{o} declared as output but not in port list", o, self.text
            )
        if not self.io <= (self.inputs_ports | self.outputs_ports):
            v = (self.io - (self.inputs_ports | self.outputs_ports)).pop()
            raise VerilogParsingError(
                f"{v} in port list but was not declared as input or output",
                v,
                self.text,
            )

        # Relabel outputs using drivers
        # Warning: if no output gate, crashes, because last gate is output
        #print("module self.inputs=", len(self.inputs), self.inputs)
        #print("module self.outputs=",len(self.outputs), self.outputs)
        #print("module self.io=", len(self.io), self.io)
        for o in self.outputs:
            #print('   >>> o=',o, 'str(o)=', str(o))
            #print("   >>> module self.outputs=",len(self.outputs), self.outputs)
            self.c.set_output(str(o))

        # Remove tie_0, tie_1 if not used
        if not self.c.fanout(self.tie_0):
            self.c.remove(self.tie_0)
        if not self.c.fanout(self.tie_1):
            self.c.remove(self.tie_1)
        if not self.c.fanout(self.tie_x):
            self.c.remove(self.tie_x)

        # Check for warnings
        if self.warnings:
            self.check_for_warnings()

        # Export before downstream processing merges cells or removes wire nodes.
        self.write_graph_csv()

        return self.c

    def list_of_ports(self, ports): # Missing vector indexes on ports
        #print("list_of_ports=", ports)
        for port in ports:
            self.io.add(port)

    # 2. Declarations
    # list_of_variables = [[Token('INT', '7'), Token('INT', '0')], [Token('IDENTIFIER', 'sys_clk')]]
    # list_of_variables = [None, [Token('IDENTIFIER', 'uart_XMIT_dataH')]]
    def input_declaration(self, list_of_variables):
        #print("input_declaration: list_of_variables[0]=", list_of_variables[0])
        #print("input_declaration: list_of_variables[1]=", list_of_variables[1])
        # [list_of_variables] = list_of_variables[1]
        var_list = list_of_variables[1]
        self.inputs_ports.update(var_list)         # needed for port list, unindexed
        #print("input_declaration: var_list=", var_list)
        vector = list_of_variables[0]
        #print("input_declaration: vector=", vector)
        if vector:
            #self.inputs.update(var_list)           # set(inputs) += var_list, needed for port list, unindexed
            i = int(str(vector[0]))
            j = int(str(vector[1]))
            low  = min(i, j)
            high = max(i, j)
            #print("input_declaration: n=", low, high)
            for variable in var_list:
                for n in range(low, high+1):
                    var = str(variable)+"["+str(n)+"]"
                    #print("input_declaration: variable=", var, [lark.Token('IDENTIFIER', var)])
                    self.inputs.update([lark.Token('IDENTIFIER', var)])    # set(inputs) += var_list[index]
                    self.add_node(var, "input")    # add_node(self, n, node_type, fanin=None, fanout=None, uid=False)
        else:
            self.inputs.update(var_list)           # set(inputs) += var_list, needed for port list, unindexed
            for variable in var_list:
                #print("input_declaration: variable=", variable)
                self.add_node(variable, "input")   # add_node(self, n, node_type, fanin=None, fanout=None, uid=False)
        #print("input_declaration: self.inputs=", self.inputs)

    def output_declaration(self, list_of_variables):
        # Previous version, output port had to be mapped to a gate
        #
        #print("output_declaration: list_of_variables=", list_of_variables)
        var_list = list_of_variables[1]
        self.outputs_ports.update(var_list)         # needed for port list, unindexed
        #print("output_declaration: var_list=", var_list)
        vector = list_of_variables[0]
        #print("output_declaration: vector=", vector)
        if vector:
            #self.outputs.update(var_list)           # set(outputs) += var_list, needed for port list, unindexed 
            i = int(str(vector[0]))
            j = int(str(vector[1]))
            low  = min(i, j)
            high = max(i, j)
            #print("output_declaration: n=", low, high)
            for variable in var_list:
                for n in range(low, high+1):
                    var = str(variable)+"["+str(n)+"]"
                    #print("output_declaration: variable=", var)
                    self.outputs.update([lark.Token('IDENTIFIER', var)])        # set(outputs) += var_list[index]
                    self.add_node(var, "buf")    # NEW add_node(self, n, node_type, fanin=None, fanout=None, uid=False)
        else:
            self.outputs.update(var_list)           # set(outputs) += var_list, needed for port list, unindexed
            for var in var_list:
                self.add_node(var, "buf")    # NEW add_node(self, n, node_type, fanin=None, fanout=None, uid=False)
        #print("output_declaration: self.outputs=", self.outputs)

    def net_declaration(self, list_of_variables):
        var_list = list_of_variables[1]
        vector = list_of_variables[0]
        #print("net_declaration: vector=", vector)
        if vector:
            self.wires.update(var_list)           # set(wires) += var_list, needed for port list, unindexed
            i = int(str(vector[0]))
            j = int(str(vector[1]))
            low  = min(i, j)
            high = max(i, j)
            #print("net_declaration: n=", low, high)
            for variable in var_list:
                for n in range(low, high+1):
                    var = str(variable)+"["+str(n)+"]"
                    #print("net_declaration: variable=", var)
                    self.wires.update([lark.Token('IDENTIFIER', var)])        # set(wires) += var_list[index]
        else:
            self.wires.update(var_list)           # set(wires) += var_list, needed for port list, unindexed
        #print("net_declaration: self.wires=", self.wires)

    def list_of_variables(self, identifiers):
        #print("list_of_variables identifiers=", identifiers)
        return identifiers

    def vector_declaration(self, vector_index):
        #print("array_index=", vector_index)
        return vector_index

    # 3. Primitive Instances
    # These are merged with module isntantiations

    # 4. Module Instantiations
    # module_instantiation: name_of_module module_instance ("," module_instance)* ";"
    #
    # DFFARX1 DFF_0_Q_reg (.CLK (clk),.D (n_12), .Q (G5), .RSTB(1'b1));
    #
    # module_instance: name_of_instance "(" list_of_module_connections ")"
    #
    def module_instantiation(self, name_of_module_and_module_instances):
        # *** module_instantiation= [
        #  Token('IDENTIFIER', 'ff'),               # name_of_module
        #     (Token('IDENTIFIER', 'DFF_0_Q_reg'),  # module_instances, name
        #         {Token('IDENTIFIER', 'CK'): Token('IDENTIFIER', 'clk'),
        #          Token('IDENTIFIER', 'D'): Token('IDENTIFIER', 'n_12'),
        #          Token('IDENTIFIER', 'Q'): Token('IDENTIFIER', 'G5')
        #         })]
        # *** module_instantiation= [
        #  Token('IDENTIFIER', 'nand'),             # name_of_module
        #     (Token('IDENTIFIER', 'g546__7837'),   # module_instances, name
        #         [Token('IDENTIFIER', 'n_11'),     # module_instances, ports[0]
        #          Token('IDENTIFIER', ' G0'),      # module_instances, ports[1:]
        #          Token('IDENTIFIER', 'n_9')
        #     ])]
        #
        #### print("*** module_instantiation=", name_of_module_and_module_instances)
        name_of_module   = name_of_module_and_module_instances[0]       # Token('IDENTIFIER', 'XOR2X1')
        module_instances = name_of_module_and_module_instances[1:]
        #### print("   *** name_of_module =",   name_of_module)
        #### print("   *** module_instances =", module_instances)
        # from circuitgraph import Circuit, primitive_gates
        # primitive_gates  # ['buf', 'and', 'or', 'xor', 'not', 'nand', 'nor', 'xnor']
        # Check if this is a primitive gate
        #if name_of_module in primitive_gates:    # Token('IDENTIFIER', 'XOR2X1'), Token('IDENTIFIER', 'nand')
        if False: # primitive gates are now blackboxes
            for name, ports in module_instances: # name=Token('IDENTIFIER', 'g546__7837'), ports=[Token('IDENTIFIER', 'n_11'), ...]
                if isinstance(ports, dict):      # if ports is not a dictionary then
                    raise VerilogParsingError(
                        "Primitive gates cannot use named port connections",
                        name,
                        self.text,
                    )
                self.add_node(ports[0], name_of_module, fanin=ports[1:]) # name_of_module='nand'
                # 
                # print("module_instantiation add_node=", ports[0], name_of_module, ports[1:])
                # add_node= G17  not  [Token('IDENTIFIER', 'n_20')] 
                # add_node= n_11 nand [Token('IDENTIFIER', 'G0'), Token('IDENTIFIER', 'n_9')]
                # add_node= n_10 nor  [Token('IDENTIFIER', 'n_7'), Token('IDENTIFIER', 'n_8')]
        # Otherwise, try to parse as blackbox
        else:
           #list(c.blackboxes)                      # ['DFF_0_Q_reg', 'DFF_1_Q_reg', 'DFF_2_Q_reg']
           # c.blackboxes['DFF_0_Q_reg'].name       # 'ff'
           # c.blackboxes['DFF_0_Q_reg'].input_set  # {'CK', 'D'}
           # c.blackboxes['DFF_0_Q_reg'].output_set # {'Q'}
           # c.blackboxes['DFF_0_Q_reg'].outputs()  # {'Q'}
           # c.blackboxes['DFF_0_Q_reg'].inputs()   # {'CK', 'D'}
           #
            try:
                bb = {i.name: i for i in self.blackboxes}[name_of_module]
            except KeyError as e:
                raise VerilogParsingError(
                    f"Blackbox {name_of_module} not in list of defined blackboxes.",
                    name_of_module,
                    self.text,
                ) from e
            for name, connections in module_instances:  # Token('IDENTIFIER', 'U227'), { dictionary }
                if not isinstance(connections, dict):   # if connections is not a dictionary {...}
                    # NEW: Handle positional port connections for blackboxes
                    # Convert positional list to named dict using blackbox port order
                    # Use inputs_ordered() and outputs_ordered() to preserve port definition order
                    # For hierarchical modules like HighActiveRegionDetection:
                    # inputs=['clk','In0','In1',...], outputs=['Trigger_out']
                    try:
                        # Get all ports in order: inputs then outputs (preserves module definition order)
                        port_list_ordered = bb.inputs_ordered() + bb.outputs_ordered()
                        if len(connections) == len(port_list_ordered):
                            # Map positional args to named ports in definition order
                            # Use plain string keys (not Lark Token) to avoid later token/key mismatches
                            named_connections = {}
                            for i, port_signal in enumerate(connections):
                                port_name = port_list_ordered[i]
                                named_connections[port_name] = port_signal
                            connections = named_connections
                        else:
                            raise VerilogParsingError(
                                f"Blackbox {name_of_module} instantiation has {len(connections)} ports but expected {len(port_list_ordered)}",
                                name,
                                self.text,
                            )
                    except AttributeError:
                        # Fallback for older BlackBox objects without inputs_ordered/outputs_ordered methods
                        # This shouldn't happen in normal usage but provides backward compatibility
                        raise VerilogParsingError(
                            f"Blackbox {name_of_module} is missing ordered port methods. Update BlackBox class.",
                            name,
                            self.text,
                        )
                    except Exception as e:
                        if not isinstance(e, VerilogParsingError):
                            raise VerilogParsingError(
                                f"Failed to convert positional to named ports for blackbox {name_of_module}: {e}",
                                name,
                                self.text,
                            ) from e
                        raise
                
                # Normalize connection keys to plain strings (handle Lark Token keys)
                try:
                    norm_connections = {}
                    for k, v in connections.items():
                        # Normalize key: prefer Token.value when available, else str()
                        if k is None:
                            key = None
                        else:
                            key = getattr(k, "value", None) if hasattr(k, "value") else None
                            if key is None:
                                key = str(k)

                        # Normalize value: prefer Token.value when available, else str()
                        if v is None:
                            val = None
                        else:
                            val = getattr(v, "value", None) if hasattr(v, "value") else None
                            if val is None:
                                val = str(v)

                        norm_connections[key] = val
                    connections = norm_connections
                except Exception:
                    # If normalization fails, keep original connections and let later checks raise
                    pass

                # If the provided connection keys don't match the blackbox port names,
                # attempt a positional fallback: map the provided signals (in
                # insertion order) to the blackbox's ordered input+output port list.
                try:
                    provided_keys = set(connections.keys())
                    expected_keys = set(bb.inputs()) | set(bb.outputs())
                    # If there is no overlap between provided keys and expected
                    # keys, but the counts match, assume positional mapping.
                    if provided_keys and provided_keys.isdisjoint(expected_keys):
                        port_list_ordered = bb.inputs_ordered() + bb.outputs_ordered()
                        vals = list(connections.values())
                        if len(vals) == len(port_list_ordered):
                            new_conn = {}
                            for i, p in enumerate(port_list_ordered):
                                new_conn[p] = vals[i]
                            connections = new_conn
                except Exception:
                    # On any failure here, keep the normalized connections and
                    # let subsequent checks raise informative errors.
                    pass

                for output in bb.outputs():             # for each blackbox output (e.g. Trigger_out)
                    if output in connections:           # if it exists in port mappings
                        net = connections[output]
                        if net in self.wires or net in self.inputs or net in self.outputs:
                            t = "buf"
                        else:
                            #### print("+++ module_instantiation: undeclared net =", net, name)
                            t = "wire"
                        self.add_node(connections[output], t)   # create a blackbox output node for n22
                # c.add_blackbox(bb, name="mux_i", connections={"in_0": "i0", "in_1": "i1", "sel_0": "s", "out": "o"})
                self.add_blackbox(bb, name, connections)    

    # module_instance: name_of_instance "(" list_of_module_connections ")"
    #
    # DFF_0_Q_reg (.CLK (clk),.D (n_12), .Q (G5), .RSTB(1'b1)
    #
    def module_instance(self, name_of_instance_and_list_of_module_connecetions):
        (
            name_of_instance,
            list_of_module_connecetions,
        ) = name_of_instance_and_list_of_module_connecetions
        return (name_of_instance, list_of_module_connecetions)

    # list_of_module_connections: module_port_connection ("," module_port_connection)*
    #                           | named_port_connection ("," named_port_connection)*
    #
    # named_port_connection ==> .CLK (clk),.D (n_12), .Q (G5), .RSTB(1'b1)
    #
    def list_of_module_connections(self, module_port_connections):
        #### print("+++ list_of_module_connections=", module_port_connections)
        # list_of_module_connections=
        #    [{Token('IDENTIFIER', 'CK'): Token('IDENTIFIER', 'clk')},
        #     {Token('IDENTIFIER', 'D'): Token('IDENTIFIER', 'n_12')},
        #     {Token('IDENTIFIER', 'Q'): Token('IDENTIFIER', 'G5')}]
        #
        # list_of_module_connections= [Token('IDENTIFIER', 'G17'), Token('IDENTIFIER', 'n_20')] 
        # list_of_module_connections= [Token('IDENTIFIER', 'n_10'), Token('IDENTIFIER', 'n_7'), Token('IDENTIFIER', 'n_8')]
        #
        if isinstance(module_port_connections[0], dict):
            d = {}                              # convert dictionaty list [] into a dictionary set {}
            for m in module_port_connections:   # m = {Token('IDENTIFIER', 'Q'): Token('IDENTIFIER', 'G5')}
                d.update(m)                     # Add to set
            #### print("    ===1 list_of_module_connections: d=", d)
            # d = {Token('IDENTIFIER', 'CK'): Token('IDENTIFIER', 'clk'), ... }
            return d
        else: # convert primative gates to named port connections
            i = 0
            s = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P']
            d = {}
            d[lark.Token('IDENTIFIER','Y')] = module_port_connections[0]  # = Token('IDENTIFIER', 'G17')
            for m in module_port_connections[1:]:
                d[lark.Token('IDENTIFIER',s[i])] = m
                i = i + 1
            #### print("    ===2 list_of_module_connections: d=", d)
            return d
        #return module_port_connections

    # module_port_connection: expression
    #
    def module_port_connection(self, expression):
        return expression[0]

    # named_port_connection: "." IDENTIFIER "(" ")"
    #                      | "." IDENTIFIER "(" expression ")"
    #
    # .CLK (clk) or .Q (G5) or .QN() unused flipflop output
    #
    def named_port_connection(self, identifier_and_expression):
        # print("named_port_connection(identifier_and_expression)=", identifier_and_expression)
        if len(identifier_and_expression)==1:
            [identifier]     = identifier_and_expression
            self.null_ports += 1
            wire             = f"null_ports_nnnn{self.null_ports}"  # unique wire name
            expression       = lark.Token('Identifier', wire)
        else:
            [identifier, expression] = identifier_and_expression
        return {identifier: expression}

    # 5. Behavioral Statements
    def assignment(self, lvalue_and_expression):
        [lvalue, expression] = lvalue_and_expression
        if lvalue not in [self.tie_0, self.tie_1, self.tie_x]:
            if expression in self.gate_expressions:
                self.c.relabel({expression: str(lvalue)})
            else:
                self.add_node(lvalue, "buf", fanin=expression)

    # 6. Specify Section

    # 7. Expressions
    def expression(self, s):
        return s[0]

    def constant_zero(self, value):
        return self.tie_0

    def constant_one(self, value):
        return self.tie_1

    def constant_x(self, value):
        return self.tie_x

    def not_gate(self, items):
        io = "_".join(items)
        node = self.add_node(f"not_{io}", "not", fanin=items[0], uid=True)
        self.gate_expressions.add(node)
        return node

    def xor_gate(self, items):
        io = "_".join(items)
        node = self.add_node(f"xor_{io}", "xor", fanin=[items[0], items[1]], uid=True)
        self.gate_expressions.add(node)
        return node

    def xnor_gate(self, items):
        io = "_".join(items)
        node = self.add_node(f"xnor_{io}", "xnor", fanin=[items[0], items[1]], uid=True)
        self.gate_expressions.add(node)
        return node

    def and_gate(self, items):
        io = "_".join(items)
        node = self.add_node(f"and_{io}", "and", fanin=[items[0], items[1]], uid=True)
        self.gate_expressions.add(node)
        return node

    def or_gate(self, items):
        io = "_".join(items)
        node = self.add_node(f"or_{io}", "or", fanin=[items[0], items[1]], uid=True)
        self.gate_expressions.add(node)
        return node

    def ternary(self, items):
        io = "_".join(items)
        n = self.add_node(f"mux_n_{io}", "not", fanin=items[0], uid=True)
        a0 = self.add_node(f"mux_a0_{io}", "and", fanin=[n, items[2]], uid=True)
        a1 = self.add_node(f"mux_a1_{io}", "and", fanin=[items[0], items[1]], uid=True)
        node = self.add_node(f"mux_o_{io}", "or", fanin=[a0, a1], uid=True)
        self.gate_expressions.add(node)
        return node


def parse_verilog_netlist(
    netlist, blackboxes, warnings=False, error_on_warning=False, csv_output_dir=None
):
    """
    Parse a verilog netlist into a Circuit.

    Parameters
    ----------
    netlist: str
            The verilog netlist to parse.
    blackboxes: list of circuitgraph.BlackBox
            The blackboxes present in the netlist.
    warnings: bool
            If True, warnings about unused nets will be printed.
    error_on_warning: bool
            If True, unused nets will cause raise `VerilogParsingWarning`
            exceptions.
    csv_output_dir: str or pathlib.Path, optional
            Directory in which to write ``nodes.csv`` and ``edges.csv``.

    Returns
    -------
    circuitgraph.Circuit
            The parsed circuit.

    """
    transformer = _VerilogCircuitGraphTransformer(
        netlist, blackboxes, warnings, error_on_warning, csv_output_dir
    )
    with open(Path(__file__).parent.absolute() / "verilog.lark") as f:
        parser = Lark(f, parser="lalr", transformer=transformer)
    [c] = parser.parse(netlist)
    return c

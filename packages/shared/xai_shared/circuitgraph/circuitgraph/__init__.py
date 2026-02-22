"""
Tools for working with circuits as graphs.

Python package `circuitgraph` provides a data structure for the generation,
manipulation, and evaluation of Boolean circuits. The circuits are represented
in a graph format based on the `networkx` package.

Features include:

- parsing of generic verilog modules
- easy circuit composition
- synthesis interface to Genus and Yosys
- SAT, #SAT, and approx-#SAT solver integration via `pysat` and `approxmc`
- implementations of common circuit transformations

Look at the examples in `circuitgraph.circuit.Circuit` for a quickstart guide.

"""
from .circuit import (
    BlackBox,
    Circuit,
    primitive_gates,
    addable_types,
    supported_types,
)
from .io import (
    generic_flop,
    dc_flops,
    from_file,
    from_lib,
    genus_flops,
    to_file,
)
from .utils import lint, visualize
from . import logic, props, sat, tx, utils

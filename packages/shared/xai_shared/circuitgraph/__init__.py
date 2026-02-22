# Vendored and modified copy of circuitgraph v0.2.1
# Original: https://github.com/circuitgraph/circuitgraph
# Copyright (c) 2020 Ruben Purdy, MIT License (see LICENSE in this directory)
# Modifications: added 'wire' type support, extended Verilog parser for
#   Trust-Hub gate-level netlists, blackbox port handling changes.
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from circuitgraph import *


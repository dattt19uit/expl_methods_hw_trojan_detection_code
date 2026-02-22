"""
Blackbox cell definitions for Trust-Hub circuits.

These definitions are needed because the failing circuits (s15850, s35932, s38417, s38584)
use specialized cell variants (with drive strength suffixes like X0, X1, X2, X4, X8) that
are not included in netlistx's default '90nm' technology library.

Each cell is defined with its input/output port names extracted from the actual Verilog netlists.
netlistx treats these as black boxes (structure unknown), focusing on connectivity rather than internals.

Generated from analysis of:
  - s15850-T100: 39 unique cell types
  - s35932-T100, T300: 16 unique cell types  
  - s38417-T100, T200: 44 unique cell types
  - s38584-T300: 43 unique cell types
"""

BLACKBOX_DEFINITIONS = {
    # Basic Logic Gates with Drive Strength Variants
    'AND2X1': {'ports': ['IN1', 'IN2', 'Q']},
    'AND2X2': {'ports': ['IN1', 'IN2', 'Q']},
    'AND3X1': {'ports': ['IN1', 'IN2', 'IN3', 'Q']},
    'AND4X1': {'ports': ['IN1', 'IN2', 'IN3', 'IN4', 'Q']},
    
    'OR2X1': {'ports': ['IN1', 'IN2', 'Q']},
    'OR3X1': {'ports': ['IN1', 'IN2', 'IN3', 'Q']},
    'OR4X1': {'ports': ['IN1', 'IN2', 'IN3', 'IN4', 'Q']},
    
    'NAND2X0': {'ports': ['IN1', 'IN2', 'QN']},
    'NAND2X1': {'ports': ['IN1', 'IN2', 'QN']},
    'NAND3X0': {'ports': ['IN1', 'IN2', 'IN3', 'QN']},
    'NAND3X1': {'ports': ['IN1', 'IN2', 'IN3', 'QN']},
    'NAND4X0': {'ports': ['IN1', 'IN2', 'IN3', 'IN4', 'QN']},
    'NAND4X1': {'ports': ['IN1', 'IN2', 'IN3', 'IN4', 'QN']},
    
    'NOR2X0': {'ports': ['IN1', 'IN2', 'QN']},
    'NOR2X2': {'ports': ['IN1', 'IN2', 'QN']},
    'NOR3X0': {'ports': ['IN1', 'IN2', 'IN3', 'QN']},
    'NOR3X1': {'ports': ['IN1', 'IN2', 'IN3', 'QN']},
    'NOR4X0': {'ports': ['IN1', 'IN2', 'IN3', 'IN4', 'QN']},
    'NOR4X1': {'ports': ['IN1', 'IN2', 'IN3', 'IN4', 'QN']},
    
    # XOR / XNOR Gates
    'XOR2X1': {'ports': ['IN1', 'IN2', 'Q']},
    'XOR3X1': {'ports': ['IN1', 'IN2', 'IN3', 'Q']},
    'XNOR2X1': {'ports': ['IN1', 'IN2', 'QN']},
    'XNOR3X1': {'ports': ['IN1', 'IN2', 'IN3', 'QN']},
    
    # Inverter with Drive Strength Variants
    'INVX0': {'ports': ['INP', 'ZN']},
    'INVX8': {'ports': ['INP', 'ZN']},
    
    # Buffer with Drive Strength
    'NBUFFX2': {'ports': ['A', 'Z']},
    
    # AOI/OAI (And-Or-Invert / Or-And-Invert) Cells
    'AO21X1': {'ports': ['A1', 'A2', 'B', 'Q']},
    'AO22X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'Q']},
    'AO221X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'C', 'Q']},
    'AO222X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'Q']},
    
    'OA21X1': {'ports': ['A', 'B1', 'B2', 'Q']},
    'OA22X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'Q']},
    'OA221X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'C', 'Q']},
    'OA222X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'Q']},
    
    'AOI21X1': {'ports': ['A1', 'A2', 'B', 'QN']},
    'AOI22X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'QN']},
    'AOI221X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'C', 'QN']},
    'AOI222X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'QN']},
    
    'OAI21X1': {'ports': ['A', 'B1', 'B2', 'QN']},
    'OAI22X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'QN']},
    'OAI221X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'C', 'QN']},
    'OAI222X1': {'ports': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'QN']},
    
    # Flip-Flops with Drive Strength Variants
    'DFFX2': {'ports': ['CLK', 'D', 'Q']},  # Primary issue for s35932
    'DFFNX2': {'ports': ['CLK', 'D', 'QN']},
    'DFFARX1': {'ports': ['CLK', 'D', 'RSTB', 'Q']},
    'SDFFX1': {'ports': ['CLK', 'D', 'SE', 'SI', 'Q']},
    
    # Multiplexer
    'MUX21X1': {'ports': ['A', 'B', 'S', 'Z']},
    'MUX21X2': {'ports': ['A', 'B', 'S', 'Z']},
    
    # Special Cells
    'ISOLANDX1': {'ports': ['A', 'ISOLATE', 'Z']},
    'LSDNX1': {'ports': ['GN', 'Q', 'QN']},
    'LSDNENX1': {'ports': ['GN', 'E', 'Q', 'QN']},
    
    # Arithmetic Cells
    'HADDX1': {'ports': ['A', 'B', 'CO', 'S']},
    
    # NAND/NOR with specific variants
    'NAND3X4': {'ports': ['IN1', 'IN2', 'IN3', 'QN']},
}


def get_blackboxes():
    """Return the complete blackbox definitions dictionary."""
    return BLACKBOX_DEFINITIONS


def print_cell_summary():
    """Print a summary of all defined blackbox cells."""
    cells = BLACKBOX_DEFINITIONS
    print(f"Total cells defined: {len(cells)}\n")
    print("Organized by category:\n")
    
    categories = {
        'Basic Gates': ['AND', 'OR', 'NAND', 'NOR', 'XOR', 'XNOR', 'INVX', 'NBUFF'],
        'AOI/OAI': ['AO', 'OA', 'AOI', 'OAI'],
        'Flip-Flops': ['DFF', 'SDFF'],
        'Multiplexers': ['MUX'],
        'Special': ['ISOL', 'LSDN', 'HADD'],
    }
    
    for category, patterns in categories.items():
        matching = [c for c in cells if any(p in c for p in patterns)]
        if matching:
            print(f"{category} ({len(matching)}):")
            for cell in sorted(matching):
                ports = cells[cell]['ports']
                print(f"  {cell:15s} -> {', '.join(ports)}")
            print()


if __name__ == '__main__':
    print_cell_summary()

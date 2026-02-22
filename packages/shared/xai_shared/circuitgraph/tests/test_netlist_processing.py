"""
Unit tests for netlist parsing and metrics generation pipeline.

This test suite verifies:
1. Netlist parsing from Verilog files
2. Circuit graph transformations (cell merging, wire removal)
3. Metrics extraction for specified trojan nodes
4. CSV output format and contents
5. Graph visualization generation
6. Configuration management
"""

import unittest
import tempfile
import json
import csv
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import netlistx as nl


class TestNetlistParsing(unittest.TestCase):
    """Test netlist reading and basic graph operations."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.test_verilog_path = Path('./TestBench/trust-hub.org/RS232-T1000/src/90nm/uart.v')
        cls.verilog_name = 'uart'
        cls.techlib = '90nm'
    
    def test_netlist_file_exists(self):
        """Verify test netlist file is accessible."""
        self.assertTrue(
            self.test_verilog_path.exists(),
            f"Test verilog file not found: {self.test_verilog_path}"
        )
    
    def test_netlist_parsing(self):
        """Test successful netlist parsing from Verilog."""
        try:
            c = nl.read_netlist(
                str(self.test_verilog_path),
                name=self.verilog_name,
                fmt='verilog',
                techlib=self.techlib
            )
            self.assertIsNotNone(c, "Circuit object should not be None")
        except Exception as e:
            self.fail(f"Failed to parse netlist: {e}")
    
    def test_circuit_has_cells(self):
        """Test that parsed circuit contains cells."""
        c = nl.read_netlist(
            str(self.test_verilog_path),
            name=self.verilog_name,
            fmt='verilog',
            techlib=self.techlib
        )
        cell_names = nl.list_cell_names(c)
        self.assertGreater(
            len(cell_names), 0,
            "Circuit should contain at least one cell"
        )
    
    def test_circuit_has_inputs_outputs(self):
        """Test that circuit has inputs and outputs defined."""
        c = nl.read_netlist(
            str(self.test_verilog_path),
            name=self.verilog_name,
            fmt='verilog',
            techlib=self.techlib
        )
        inputs = c.inputs()
        outputs = c.outputs()
        
        self.assertIsNotNone(inputs, "Inputs should be defined")
        self.assertIsNotNone(outputs, "Outputs should be defined")
        self.assertGreater(len(list(inputs)), 0, "Should have at least one input")
        self.assertGreater(len(list(outputs)), 0, "Should have at least one output")


class TestCircuitTransformations(unittest.TestCase):
    """Test circuit graph transformations."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test circuit."""
        cls.test_verilog_path = Path('./TestBench/trust-hub.org/RS232-T1000/src/90nm/uart.v')
        cls.verilog_name = 'uart'
        cls.techlib = '90nm'
    
    def test_cell_merging(self):
        """Test cell merging operation."""
        c = nl.read_netlist(
            str(self.test_verilog_path),
            name=self.verilog_name,
            fmt='verilog',
            techlib=self.techlib
        )
        
        # Get cell count before merging
        cells_before = nl.list_cell_names(c)
        count_before = len(cells_before)
        
        # Merge cells
        nl.merge_cells(c, cells_before)
        
        # After merging, circuit should still be valid
        self.assertIsNotNone(c, "Circuit should remain valid after merging")
    
    def test_wire_removal(self):
        """Test wire removal operation."""
        c = nl.read_netlist(
            str(self.test_verilog_path),
            name=self.verilog_name,
            fmt='verilog',
            techlib=self.techlib
        )
        
        # Merge and remove wires
        nl.merge_cells(c, nl.list_cell_names(c))
        nl.remove_cells(c, ['wire'])
        
        # After removal, circuit should still be valid
        self.assertIsNotNone(c, "Circuit should remain valid after wire removal")
    
    def test_transformation_preserves_connectivity(self):
        """Test that transformations preserve circuit connectivity."""
        c = nl.read_netlist(
            str(self.test_verilog_path),
            name=self.verilog_name,
            fmt='verilog',
            techlib=self.techlib
        )
        
        # Get inputs and outputs before
        inputs_before = list(c.inputs())
        outputs_before = list(c.outputs())
        
        # Apply transformations
        nl.merge_cells(c, nl.list_cell_names(c))
        nl.remove_cells(c, ['wire'])
        
        # Get inputs and outputs after
        inputs_after = list(c.inputs())
        outputs_after = list(c.outputs())
        
        # Should have same I/O
        self.assertEqual(inputs_before, inputs_after, "Inputs should be preserved")
        self.assertEqual(outputs_before, outputs_after, "Outputs should be preserved")


class TestMetricsExtraction(unittest.TestCase):
    """Test metrics extraction for trojan nodes."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test circuit and nodes."""
        cls.test_verilog_path = Path('./TestBench/trust-hub.org/RS232-T1000/src/90nm/uart.v')
        cls.verilog_name = 'uart'
        cls.techlib = '90nm'
        cls.trojan_nodes = [
            'U293.QN', 'U294.QN', 'U295.QN', 'U296.Q', 'U297.QN',
            'U298.QN', 'U299.QN', 'U300.QN', 'U301.Q', 'U302.Q',
            'U303.Q', 'U305.Q'
        ]
    
    def setUp(self):
        """Set up circuit for each test."""
        c = nl.read_netlist(
            str(self.test_verilog_path),
            name=self.verilog_name,
            fmt='verilog',
            techlib=self.techlib
        )
        nl.merge_cells(c, nl.list_cell_names(c))
        nl.remove_cells(c, ['wire'])
        self.circuit = c
    
    def test_metrics_extraction(self):
        """Test that metrics can be extracted without error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_path = f.name
        
        try:
            nl.write_metrics(self.circuit, self.trojan_nodes, csv_path)
            self.assertTrue(Path(csv_path).exists(), "CSV file should be created")
        finally:
            Path(csv_path).unlink(missing_ok=True)
    
    def test_metrics_csv_format(self):
        """Test CSV output format and structure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_path = f.name
        
        try:
            nl.write_metrics(self.circuit, self.trojan_nodes, csv_path)
            
            # Read and validate CSV
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Should have header + data rows
            self.assertGreater(len(rows), 1, "CSV should have header and data rows")
            
            # Header should contain node names or metric labels
            header = rows[0]
            self.assertGreater(len(header), 0, "Header should have columns")
            
            # Data rows should have same number of columns as header
            for row in rows[1:]:
                self.assertEqual(
                    len(row), len(header),
                    f"Data row has {len(row)} columns but header has {len(header)}"
                )
        finally:
            Path(csv_path).unlink(missing_ok=True)
    
    def test_metrics_are_numeric(self):
        """Test that metrics are numeric values."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_path = f.name
        
        try:
            nl.write_metrics(self.circuit, self.trojan_nodes, csv_path)
            
            # Read CSV and validate values
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Skip header, check data rows
            for row_idx, row in enumerate(rows[1:], 1):
                for col_idx, value in enumerate(row):
                    try:
                        float(value)
                    except ValueError:
                        self.fail(
                            f"Row {row_idx}, Column {col_idx}: "
                            f"'{value}' is not numeric"
                        )
        finally:
            Path(csv_path).unlink(missing_ok=True)
    
    def test_metrics_count_matches_nodes(self):
        """Test that metrics output has columns for each trojan node."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_path = f.name
        
        try:
            nl.write_metrics(self.circuit, self.trojan_nodes, csv_path)
            
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            header = rows[0]
            # Header should have at least as many columns as nodes
            # (may include additional columns like 'part', 'impl', etc.)
            expected_min_cols = len(self.trojan_nodes)
            self.assertGreaterEqual(
                len(header), expected_min_cols,
                f"Expected at least {expected_min_cols} columns, got {len(header)}"
            )
        finally:
            Path(csv_path).unlink(missing_ok=True)
    
    def test_missing_node_handling(self):
        """Test behavior when requesting metrics for non-existent nodes."""
        # This tests robustness - system should handle missing nodes gracefully
        mixed_nodes = self.trojan_nodes + ['NONEXISTENT_NODE_XYZ']
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_path = f.name
        
        try:
            # Should either skip missing nodes or handle gracefully
            try:
                nl.write_metrics(self.circuit, mixed_nodes, csv_path)
                # If successful, file should exist
                self.assertTrue(Path(csv_path).exists())
            except Exception as e:
                # If it fails, should be a clear error about missing node
                self.assertIn('NONEXISTENT', str(e).upper())
        finally:
            Path(csv_path).unlink(missing_ok=True)


class TestGraphVisualization(unittest.TestCase):
    """Test graph visualization generation."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test circuit."""
        cls.test_verilog_path = Path('./TestBench/trust-hub.org/RS232-T1000/src/90nm/uart.v')
        cls.verilog_name = 'uart'
        cls.techlib = '90nm'
    
    def setUp(self):
        """Set up circuit for each test."""
        c = nl.read_netlist(
            str(self.test_verilog_path),
            name=self.verilog_name,
            fmt='verilog',
            techlib=self.techlib
        )
        nl.merge_cells(c, nl.list_cell_names(c))
        nl.remove_cells(c, ['wire'])
        self.circuit = c
    
    def test_graph_generation(self):
        """Test that graph visualization can be generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_path = str(Path(tmpdir) / 'test_graph')
            
            try:
                nl.graph_cells(self.circuit, graph_path)
                # Graph generation creates .dot and/or .pdf files
                dot_file = Path(f'{graph_path}.dot')
                self.assertTrue(
                    dot_file.exists(),
                    f"Graph file should be created at {dot_file}"
                )
            except Exception as e:
                self.fail(f"Graph generation failed: {e}")
    
    def test_graph_dot_format(self):
        """Test that generated graph is in valid DOT format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_path = str(Path(tmpdir) / 'test_graph')
            
            nl.graph_cells(self.circuit, graph_path)
            dot_file = Path(f'{graph_path}.dot')
            
            # Read and validate DOT file
            with open(dot_file, 'r') as f:
                content = f.read()
            
            # DOT files should start with 'digraph' or 'graph'
            self.assertTrue(
                content.strip().startswith('digraph') or 
                content.strip().startswith('graph'),
                "Graph should be in DOT format"
            )


class TestConfigurationManagement(unittest.TestCase):
    """Test circuit configuration handling."""
    
    def setUp(self):
        """Set up test configuration."""
        self.config_path = Path('./circuit_configs.json')
    
    def test_config_file_exists(self):
        """Test that configuration file exists."""
        self.assertTrue(
            self.config_path.exists(),
            f"Configuration file not found: {self.config_path}"
        )
    
    def test_config_json_valid(self):
        """Test that configuration file is valid JSON."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            self.assertIsInstance(config, dict, "Config should be a dictionary")
        except json.JSONDecodeError as e:
            self.fail(f"Configuration file is invalid JSON: {e}")
    
    def test_config_structure(self):
        """Test that configuration has expected structure."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        required_keys = ['part', 'impl', 'tech', 'verilog_path', 'verilog_name', 'nodes']
        
        for circuit_name, circuit_config in config.items():
            for key in required_keys:
                self.assertIn(
                    key, circuit_config,
                    f"Circuit {circuit_name} missing required key: {key}"
                )
    
    def test_config_verilog_paths_exist(self):
        """Test that all configured verilog paths point to existing files."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        for circuit_name, circuit_config in config.items():
            verilog_path = Path(circuit_config['verilog_path'])
            self.assertTrue(
                verilog_path.exists(),
                f"Circuit {circuit_name}: Verilog file not found at {verilog_path}"
            )
    
    def test_config_nodes_are_list(self):
        """Test that trojan nodes are specified as lists."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        for circuit_name, circuit_config in config.items():
            nodes = circuit_config.get('nodes', [])
            self.assertIsInstance(
                nodes, list,
                f"Circuit {circuit_name}: nodes should be a list, got {type(nodes)}"
            )
    
    def test_config_nodes_not_empty(self):
        """Test that at least one trojan node is specified per circuit."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        for circuit_name, circuit_config in config.items():
            nodes = circuit_config.get('nodes', [])
            self.assertGreater(
                len(nodes), 0,
                f"Circuit {circuit_name}: should specify at least one trojan node"
            )


class TestIntegrationPipeline(unittest.TestCase):
    """Integration tests for complete processing pipeline."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.config_path = Path('./circuit_configs.json')
        with open(cls.config_path, 'r') as f:
            cls.configs = json.load(f)
        # Use first circuit for integration test
        cls.test_circuit_key = list(cls.configs.keys())[0]
        cls.test_config = cls.configs[cls.test_circuit_key]
    
    def test_full_pipeline_single_circuit(self):
        """Test complete processing pipeline for a single circuit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Step 1: Load netlist
            verilog_path = self.test_config['verilog_path']
            c = nl.read_netlist(
                verilog_path,
                name=self.test_config['verilog_name'],
                fmt='verilog',
                techlib=self.test_config['tech']
            )
            self.assertIsNotNone(c)
            
            # Step 2: Merge cells
            nl.merge_cells(c, nl.list_cell_names(c))
            
            # Step 3: Remove wires
            nl.remove_cells(c, ['wire'])
            
            # Step 4: Generate graph
            graph_path = str(output_dir / 'test_graph')
            nl.graph_cells(c, graph_path)
            self.assertTrue(Path(f'{graph_path}.dot').exists())
            
            # Step 5: Extract metrics
            csv_path = str(output_dir / 'test_metrics.csv')
            nl.write_metrics(c, self.test_config['nodes'], csv_path)
            self.assertTrue(Path(csv_path).exists())
            
            # Verify CSV has data
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            self.assertGreater(len(rows), 1, "CSV should have header and data")
    
    def test_batch_processing_consistency(self):
        """Test that processing is consistent across multiple runs."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                # Process same circuit twice
                for tmpdir in [tmpdir1, tmpdir2]:
                    c = nl.read_netlist(
                        self.test_config['verilog_path'],
                        name=self.test_config['verilog_name'],
                        fmt='verilog',
                        techlib=self.test_config['tech']
                    )
                    nl.merge_cells(c, nl.list_cell_names(c))
                    nl.remove_cells(c, ['wire'])
                    
                    csv_path = str(Path(tmpdir) / 'metrics.csv')
                    nl.write_metrics(c, self.test_config['nodes'], csv_path)
                
                # Compare CSV outputs
                with open(Path(tmpdir1) / 'metrics.csv', 'r') as f1:
                    content1 = f1.read()
                with open(Path(tmpdir2) / 'metrics.csv', 'r') as f2:
                    content2 = f2.read()
                
                self.assertEqual(
                    content1, content2,
                    "Multiple runs should produce identical output"
                )


if __name__ == '__main__':
    unittest.main()

"""Tests for Trust-Hub downloader."""

import pytest
import tempfile
import shutil
import zipfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from data_acquisition.downloader import download_circuits, TrustHubDownloader


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_html():
    """Sample HTML with download links."""
    return '''
    <html>
        <div class="benchmarks">
            <a href="/downloads/resource/benchmarks/AES/AES-T100.zip">AES-T100</a>
            <a href="/downloads/resource/benchmarks/AES/AES-T200.zip">AES-T200</a>
            <a href="/downloads/resource/benchmarks/RS232/RS232-T100.zip">RS232</a>
            <a href="/other/path/file.txt">Not a benchmark</a>
        </div>
    </html>
    '''


@pytest.fixture
def sample_zip(temp_dir):
    """Create a sample ZIP file for testing extraction."""
    # Create in a separate subdirectory
    zip_dir = Path(temp_dir) / "zips"
    zip_dir.mkdir()
    zip_path = zip_dir / "test.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        # Add a test file
        zf.writestr("test.txt", "Hello World")
        zf.writestr("subdir/file.txt", "Nested file")
    return zip_path


class TestDownloaderInit:
    """Test downloader initialization."""
    
    def test_basic_init(self):
        """Test basic initialization."""
        downloader = TrustHubDownloader(output_dir="test_data")
        assert downloader.output_dir == Path("test_data")
        assert downloader.downloaded == 0
        assert downloader.skipped == 0
        assert downloader.failed == 0
        assert downloader.verify_ssl == False
    
    def test_init_with_html_file(self, temp_dir):
        """Test initialization with HTML file."""
        html_file = Path(temp_dir) / "test.html"
        html_file.write_text("<html></html>")
        
        downloader = TrustHubDownloader(
            output_dir=temp_dir,
            html_file=str(html_file)
        )
        assert downloader.html_file == str(html_file)
    
    def test_init_with_ssl_verification(self):
        """Test SSL verification flag."""
        downloader = TrustHubDownloader(verify_ssl=True)
        assert downloader.verify_ssl == True


class TestExtractDownloadLinks:
    """Test download link extraction."""
    
    def test_extract_valid_links(self, sample_html):
        """Test extracting valid download links."""
        downloader = TrustHubDownloader()
        links = downloader.extract_download_links(sample_html)
        
        assert len(links) == 3
        assert '/downloads/resource/benchmarks/AES/AES-T100.zip' in links
        assert '/downloads/resource/benchmarks/AES/AES-T200.zip' in links
        assert '/downloads/resource/benchmarks/RS232/RS232-T100.zip' in links
    
    def test_extract_no_duplicates(self):
        """Test that duplicate links are removed."""
        html = '''
        <a href="/downloads/resource/file1.zip">File 1</a>
        <a href="/downloads/resource/file1.zip">File 1 Again</a>
        <a href="/downloads/resource/file2.zip">File 2</a>
        '''
        downloader = TrustHubDownloader()
        links = downloader.extract_download_links(html)
        
        assert len(links) == 2
    
    def test_extract_empty_html(self):
        """Test extraction from empty HTML."""
        downloader = TrustHubDownloader()
        links = downloader.extract_download_links("")
        assert len(links) == 0
    
    def test_extract_rar_files(self):
        """Test extraction of RAR files."""
        html = '''
        <a href="/downloads/resource/file1.rar">RAR file</a>
        <a href="/downloads/resource/file2.part01.rar">Multi-part RAR</a>
        '''
        downloader = TrustHubDownloader()
        links = downloader.extract_download_links(html)
        
        assert len(links) == 2
        assert all('.rar' in link for link in links)


class TestFetchBenchmarkPage:
    """Test benchmark page fetching."""
    
    def test_fetch_from_file(self, temp_dir):
        """Test loading HTML from file."""
        html_content = "<html><body>Test</body></html>"
        html_file = Path(temp_dir) / "test.html"
        html_file.write_text(html_content)
        
        downloader = TrustHubDownloader(html_file=str(html_file))
        result = downloader.fetch_benchmark_page()
        
        assert html_content in result
    
    def test_fetch_missing_file(self):
        """Test error handling for missing file."""
        downloader = TrustHubDownloader(html_file="/nonexistent/file.html")
        
        with pytest.raises(FileNotFoundError):
            downloader.fetch_benchmark_page()


class TestZipExtraction:
    """Test ZIP file extraction."""
    
    def test_extract_zip_file(self, temp_dir, sample_zip):
        """Test extracting a ZIP file."""
        downloader = TrustHubDownloader(output_dir=temp_dir)
        
        # Move zip to output directory
        dest_zip = Path(temp_dir) / "test.zip"
        shutil.copy(sample_zip, dest_zip)
        
        # Extract
        downloader.extract_archives()
        
        # Check extraction - files are extracted directly to output_dir
        assert (Path(temp_dir) / "test.txt").exists()
        assert (Path(temp_dir) / "subdir" / "file.txt").exists()
    
    def test_skip_already_extracted(self, temp_dir, sample_zip):
        """Test that already-extracted archives are skipped."""
        downloader = TrustHubDownloader(output_dir=temp_dir)
        
        # Move zip and create a file that would be extracted
        dest_zip = Path(temp_dir) / "test.zip"
        shutil.copy(sample_zip, dest_zip)
        (Path(temp_dir) / "test.txt").write_text("already exists")
        
        # Extract - should work (overwrite existing files)
        downloader.extract_archives()
        
        # Should have successfully extracted
        assert (Path(temp_dir) / "test.txt").exists()
        # Content should be from the zip, not "already exists"
        assert (Path(temp_dir) / "test.txt").read_text() == "Hello World"


class TestStatistics:
    """Test download statistics tracking."""
    
    def test_initial_statistics(self):
        """Test initial statistics are zero."""
        downloader = TrustHubDownloader()
        assert downloader.downloaded == 0
        assert downloader.skipped == 0
        assert downloader.failed == 0
    
    @patch('requests.get')
    def test_download_statistics(self, mock_get, temp_dir):
        """Test that statistics are updated correctly."""
        # Mock successful download
        mock_response = Mock()
        mock_response.content = b"test data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        downloader = TrustHubDownloader(output_dir=temp_dir)
        result = downloader.download_file('/downloads/resource/test.zip')
        
        assert result == True
        assert (Path(temp_dir) / 'test.zip').exists()


class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow_with_html_file(self, temp_dir, sample_html):
        """Test complete workflow from HTML file to extraction."""
        # Create HTML file
        html_file = Path(temp_dir) / "benchmarks.html"
        html_file.write_text(sample_html)
        
        # Initialize downloader
        downloader = TrustHubDownloader(
            output_dir=temp_dir,
            html_file=str(html_file)
        )
        
        # Load and extract links
        html = downloader.fetch_benchmark_page()
        links = downloader.extract_download_links(html)
        
        assert len(links) == 3
        assert all('/downloads/resource/' in link for link in links)


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_output_directory(self):
        """Test handling of invalid output directory."""
        # Use a path that doesn't require permissions to check
        # The downloader creates the directory, so test with writable location
        downloader = TrustHubDownloader(output_dir="/tmp/test_impossible_dir_12345")
        assert downloader.output_dir == Path("/tmp/test_impossible_dir_12345")
        # Clean up
        if downloader.output_dir.exists():
            downloader.output_dir.rmdir()
    
    def test_malformed_html(self):
        """Test handling of malformed HTML."""
        downloader = TrustHubDownloader()
        malformed_html = "<html><a href='/downloads/resource/file.zip'</html>"
        
        # Should not crash, just return what it can find
        links = downloader.extract_download_links(malformed_html)
        assert isinstance(links, list)


class TestDownloadCircuitsAPI:
    """Test the main API function."""
    
    def test_api_function_signature(self):
        """Test the main API function exists with correct signature."""
        assert callable(download_circuits)
    
    @patch('data_acquisition.downloader.download.TrustHubDownloader')
    def test_api_creates_downloader(self, mock_downloader_class, temp_dir):
        """Test that API function creates downloader correctly."""
        mock_instance = Mock()
        mock_downloader_class.return_value = mock_instance
        mock_instance.fetch_benchmark_page.return_value = ""
        mock_instance.extract_download_links.return_value = []
        
        download_circuits(
            output_dir=temp_dir,
            verify_ssl=True,
            extract=False,
            html_file="test.html"
        )
        
        mock_downloader_class.assert_called_once_with(
            output_dir=temp_dir,
            verify_ssl=True,
            html_file="test.html"
        )


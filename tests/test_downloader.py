"""
Test Suite for Gamdl Downloader Module

This module contains comprehensive tests for the download functionality,
covering various scenarios and edge cases.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

# Import the downloader module to be tested
from gamdl.downloader import Downloader
from gamdl.exceptions import (
    DownloadError,
    NetworkError,
    AuthenticationError
)

# Test data and mock objects
from tests import generate_mock_data, get_test_data_path

class TestDownloader:
    """
    Comprehensive test class for Downloader functionality
    """

    @pytest.fixture
    def temp_download_dir(self):
        """
        Create a temporary download directory for each test
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_downloader(self, temp_download_dir):
        """
        Create a mock Downloader instance with temporary directory
        """
        return Downloader(
            download_dir=temp_download_dir,
            quality='high',
            metadata=True
        )

    @pytest.mark.unit
    def test_downloader_initialization(self, mock_downloader):
        """
        Test Downloader class initialization
        """
        assert mock_downloader is not None
        assert os.path.exists(mock_downloader.download_dir)
        assert mock_downloader.quality == 'high'
        assert mock_downloader.metadata is True

    @pytest.mark.unit
    def test_validate_download_url(self, mock_downloader):
        """
        Test URL validation for different types of music links
        """
        valid_urls = [
            'https://open.spotify.com/track/123',
            'https://music.youtube.com/watch?v=abc',
            'https://soundcloud.com/artist/track'
        ]

        invalid_urls = [
            'https://example.com/invalid',
            'not a url',
            ''
        ]

        for url in valid_urls:
            assert mock_downloader.validate_url(url) is True

        for url in invalid_urls:
            assert mock_downloader.validate_url(url) is False

    @pytest.mark.integration
    @patch('gamdl.downloader.requests.get')
    def test_download_track_success(self, mock_get, mock_downloader, temp_download_dir):
        """
        Test successful track download
        """
        # Prepare mock track data
        mock_track = generate_mock_data('track')[0]
        mock_url = f"https://example.com/track/{mock_track['id']}"

        # Mock successful download response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'Mock audio content'
        mock_get.return_value = mock_response

        # Perform download
        download_path = mock_downloader.download_track(
            track_url=mock_url,
            track_info=mock_track
        )

        # Assertions
        assert os.path.exists(download_path)
        assert os.path.getsize(download_path) > 0

    @pytest.mark.unit
    def test_download_track_network_error(self, mock_downloader):
        """
        Test network error during download
        """
        mock_track = generate_mock_data('track')[0]
        
        with pytest.raises(NetworkError):
            with patch('gamdl.downloader.requests.get') as mock_get:
                mock_get.side_effect = ConnectionError("Network error")
                mock_downloader.download_track(
                    track_url='https://example.com/track/123',
                    track_info=mock_track
                )

    @pytest.mark.unit
    def test_download_track_invalid_url(self, mock_downloader):
        """
        Test download with invalid URL
        """
        mock_track = generate_mock_data('track')[0]
        
        with pytest.raises(DownloadError):
            mock_downloader.download_track(
                track_url='invalid_url',
                track_info=mock_track
            )

    @pytest.mark.integration
    def test_batch_download(self, mock_downloader, temp_download_dir):
        """
        Test batch download of multiple tracks
        """
        # Generate mock tracks
        mock_tracks = generate_mock_data('track', count=5)
        
        # Prepare mock URLs
        mock_urls = [
            f"https://example.com/track/{track['id']}" 
            for track in mock_tracks
        ]

        # Mock download method
        with patch.object(mock_downloader, 'download_track') as mock_download:
            mock_download.return_value = os.path.join(temp_download_dir, 'mock_track.mp3')
            
            # Perform batch download
            downloaded_tracks = mock_downloader.batch_download(
                track_urls=mock_urls,
                track_infos=mock_tracks
            )

            # Assertions
            assert len(downloaded_tracks) == 5
            assert mock_download.call_count == 5

    @pytest.mark.unit
    def test_metadata_extraction(self, mock_downloader):
        """
        Test metadata extraction for downloaded tracks
        """
        mock_track = generate_mock_data('track')[0]
        
        # Mock metadata extraction
        metadata = mock_downloader.extract_metadata(mock_track)
        
        assert 'title' in metadata
        assert 'artist' in metadata
        assert metadata['title'] == mock_track['title']

    @pytest.mark.parametrize('quality', ['low', 'medium', 'high'])
    def test_download_quality_options(self, quality):
        """
        Test different download quality options
        """
        downloader = Downloader(
            download_dir=tempfile.mkdtemp(),
            quality=quality
        )
        
        assert downloader.quality == quality

def test_authentication_error():
    """
    Test authentication failure scenario
    """
    with pytest.raises(AuthenticationError):
        # Simulate authentication failure
        Downloader(
            download_dir=tempfile.mkdtemp(),
            auth_token=None
        )

# Performance test
@pytest.mark.performance
def test_download_performance(benchmark, mock_downloader):
    """
    Benchmark download performance
    """
    mock_track = generate_mock_data('track')[0]
    mock_url = f"https://example.com/track/{mock_track['id']}"

    result = benchmark(
        mock_downloader.download_track,
        track_url=mock_url,
        track_info=mock_track
    )
    
    assert result is not None

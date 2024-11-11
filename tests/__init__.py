"""
Gamdl Test Suite Initialization Module

This module sets up the testing environment, configures test discovery,
and provides utility functions for testing.
"""

import os
import sys
import logging
from typing import List, Dict, Any
import pytest

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('tests/test.log')
    ]
)

# Test Configuration
TEST_CONFIG: Dict[str, Any] = {
    'test_mode': True,
    'mock_services': True,
    'log_level': logging.DEBUG,
    'timeout': 30,
    'retry_attempts': 3
}

def pytest_configure(config):
    """
    Configure pytest settings and register custom markers
    
    Args:
        config (pytest.Config): Pytest configuration object
    """
    config.addinivalue_line(
        "markers", 
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", 
        "performance: mark test for performance evaluation"
    )
    config.addinivalue_line(
        "markers", 
        "external: mark test requiring external services"
    )

def get_test_data_path(filename: str) -> str:
    """
    Retrieve full path to test data file
    
    Args:
        filename (str): Name of test data file
    
    Returns:
        str: Full path to test data file
    """
    return os.path.join(PROJECT_ROOT, 'tests', 'data', filename)

def load_test_config() -> Dict[str, Any]:
    """
    Load test configuration
    
    Returns:
        Dict[str, Any]: Test configuration dictionary
    """
    return TEST_CONFIG.copy()

class TestEnvironment:
    """
    Centralized test environment management
    """
    
    @staticmethod
    def setup_test_environment() -> None:
        """
        Prepare test environment
        """
        # Create necessary test directories
        os.makedirs(os.path.join(PROJECT_ROOT, 'tests', 'data'), exist_ok=True)
        os.makedirs(os.path.join(PROJECT_ROOT, 'tests', 'logs'), exist_ok=True)
        
        # Set environment variables for testing
        os.environ['GAMDL_TEST_MODE'] = 'true'
    
    @staticmethod
    def teardown_test_environment() -> None:
        """
        Clean up test environment
        """
        # Remove test-specific environment variables
        os.environ.pop('GAMDL_TEST_MODE', None)

def pytest_runtest_setup(item):
    """
    Pre-test setup hook
    
    Args:
        item (pytest.Item): Test item being run
    """
    TestEnvironment.setup_test_environment()
    
    # Log test information
    logging.info(f"Running test: {item.name}")

def pytest_runtest_teardown(item, nextitem):
    """
    Post-test teardown hook
    
    Args:
        item (pytest.Item): Test item that was run
        nextitem (pytest.Item): Next test item to be run
    """
    TestEnvironment.teardown_test_environment()
    
    # Log test completion
    logging.info(f"Completed test: {item.name}")

def generate_mock_data(data_type: str, count: int = 1) -> List[Dict[str, Any]]:
    """
    Generate mock test data
    
    Args:
        data_type (str): Type of mock data to generate
        count (int, optional): Number of mock data entries. Defaults to 1.
    
    Returns:
        List[Dict[str, Any]]: Generated mock data
    """
    mock_generators = {
        'track': lambda: {
            'id': f'track_{i}',
            'title': f'Mock Track {i}',
            'artist': f'Mock Artist {i}',
            'duration': 180
        } for i in range(count),
        'album': lambda: {
            'id': f'album_{i}',
            'name': f'Mock Album {i}',
            'artist': f'Mock Artist {i}',
            'tracks_count': 10
        } for i in range(count),
        'playlist': lambda: {
            'id': f'playlist_{i}',
            'name': f'Mock Playlist {i}',
            'owner': 'Test User',
            'tracks': [generate_mock_data('track', 5)]
        } for i in range(count)
    }
    
    return list(mock_generators.get(data_type, lambda: [])())

# Expose key functions and classes
__all__ = [
    'get_test_data_path',
    'load_test_config',
    'generate_mock_data',
    'TestEnvironment',
    'TEST_CONFIG'
]

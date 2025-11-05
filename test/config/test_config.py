"""Test configuration loader."""
import json
from pathlib import Path
from typing import Any, Dict

class TestConfig:
    """Test configuration manager."""

    def __init__(self):
        """Initialize test configuration."""
        self._config = None
        self._config_path = Path(__file__).parent / "test_data.json"

    @property
    def config(self) -> Dict[str, Any]:
        """Load and cache test configuration."""
        if self._config is None:
            with open(self._config_path, 'r') as f:
                self._config = json.load(f)
        return self._config

    def get_valid_patent_numbers(self):
        """Get list of valid patent numbers for testing."""
        return self.config["patents"]["valid"]

    def get_invalid_patent_numbers(self):
        """Get list of invalid patent numbers for testing."""
        return self.config["patents"]["invalid"]

    def get_valid_app_numbers(self):
        """Get list of valid application numbers for testing."""
        return self.config["applications"]["valid"]

    def get_invalid_app_numbers(self):
        """Get list of invalid application numbers for testing."""
        return self.config["applications"]["invalid"]

    def get_search_queries(self):
        """Get test search queries."""
        return self.config["search_queries"]

    def get_timeouts(self):
        """Get timeout values for tests."""
        return self.config["timeouts"]

    def get_mock_data(self):
        """Get mock data for testing."""
        return self.config["mock_data"]

# Global test config instance
test_config = TestConfig()

"""
Unit tests for ConfigManager

Test Strategy: UNIT_INTEGRATION
Phase: 5 (Test Implementation)
Issue: #380
"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import yaml
import tempfile
import shutil

from core.config_manager import ConfigManager
from common.error_handler import ConfigValidationError


class TestConfigManagerInit:
    """Test ConfigManager initialization"""

    def test_config_manager_init_正常系(self):
        """
        Test: ConfigManager initialization (normal case)
        Given: Valid config_path
        When: ConfigManager is initialized
        Then: Instance is created with correct attributes
        """
        # Given
        config_path = Path('config.yaml')

        # When
        config_manager = ConfigManager(config_path)

        # Then
        assert config_manager.config_path == config_path
        assert config_manager._config == {}
        assert config_manager.logger is not None

    def test_config_manager_init_default_path(self):
        """
        Test: ConfigManager initialization with default path
        Given: No config_path provided
        When: ConfigManager is initialized
        Then: Default path is used
        """
        # When
        config_manager = ConfigManager()

        # Then
        assert config_manager.config_path == Path('config.yaml')


class TestConfigManagerLoadConfig:
    """Test ConfigManager.load_config() method"""

    def test_load_config_from_yaml_正常系(self, tmp_path):
        """
        Test: Load configuration from YAML file (normal case)
        Given: Valid config.yaml exists
        When: load_config() is called
        Then: Configuration is loaded successfully
        """
        # Given
        config_file = tmp_path / "config.yaml"
        config_data = {
            'github_token': 'test-token-123',
            'github_repository': 'test-owner/test-repo',
            'claude_api_key': 'sk-test-key-456',
            'openai_api_key': 'sk-openai-test-key',
            'claude_code_oauth_token': 'oauth-test-token',
            'working_dir': '/tmp/test',
            'log_level': 'INFO'
        }
        config_file.write_text(yaml.dump(config_data))

        config_manager = ConfigManager(config_file)

        # When
        result = config_manager.load_config()

        # Then
        assert result['github_token'] == 'test-token-123'
        assert result['github_repository'] == 'test-owner/test-repo'
        assert result['claude_api_key'] == 'sk-test-key-456'
        assert result['log_level'] == 'INFO'

    def test_load_config_from_environment_正常系(self, tmp_path):
        """
        Test: Environment variables override YAML config
        Given: config.yaml has github_token and GITHUB_TOKEN env var is set
        When: load_config() is called
        Then: Environment variable takes precedence
        """
        # Given
        config_file = tmp_path / "config.yaml"
        config_data = {
            'github_token': 'yaml-token',
            'github_repository': 'test-owner/test-repo',
            'claude_api_key': 'sk-test-key-456',
            'openai_api_key': 'sk-openai-test-key',
            'claude_code_oauth_token': 'oauth-test-token'
        }
        config_file.write_text(yaml.dump(config_data))

        config_manager = ConfigManager(config_file)

        # When - Mock environment variable
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'env-token'}):
            result = config_manager.load_config()

        # Then - Environment variable overrides YAML
        assert result['github_token'] == 'env-token'
        assert result['github_repository'] == 'test-owner/test-repo'

    def test_load_config_missing_required_key_異常系(self, tmp_path):
        """
        Test: ConfigValidationError raised when required key is missing
        Given: config.yaml missing github_token and no env var set
        When: load_config() is called
        Then: ConfigValidationError is raised
        """
        # Given
        config_file = tmp_path / "config.yaml"
        config_data = {
            'github_repository': 'test-owner/test-repo',
            'claude_api_key': 'sk-test-key-456'
            # github_token is missing
        }
        config_file.write_text(yaml.dump(config_data))

        config_manager = ConfigManager(config_file)

        # When/Then
        with pytest.raises(ConfigValidationError) as exc_info:
            config_manager.load_config()

        assert 'github_token' in str(exc_info.value).lower()

    def test_load_config_invalid_log_level_異常系(self, tmp_path):
        """
        Test: ConfigValidationError raised for invalid LOG_LEVEL
        Given: config.yaml with invalid log_level
        When: load_config() is called
        Then: ConfigValidationError is raised
        """
        # Given
        config_file = tmp_path / "config.yaml"
        config_data = {
            'github_token': 'test-token',
            'github_repository': 'test-owner/test-repo',
            'claude_api_key': 'sk-test-key',
            'openai_api_key': 'sk-openai-test-key',
            'claude_code_oauth_token': 'oauth-test-token',
            'log_level': 'INVALID_LEVEL'
        }
        config_file.write_text(yaml.dump(config_data))

        config_manager = ConfigManager(config_file)

        # When/Then
        with pytest.raises(ConfigValidationError) as exc_info:
            config_manager.load_config()

        assert 'Invalid log_level' in str(exc_info.value)

    def test_load_config_yaml_not_found_正常系(self, tmp_path):
        """
        Test: Graceful handling when config.yaml doesn't exist
        Given: config.yaml does not exist but env vars are set
        When: load_config() is called
        Then: Default values + env vars are used, no error raised
        """
        # Given
        config_file = tmp_path / "nonexistent_config.yaml"
        config_manager = ConfigManager(config_file)

        # When - Set all required env vars
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'env-token',
            'GITHUB_REPOSITORY': 'test-owner/test-repo',
            'CLAUDE_API_KEY': 'sk-env-key',
            'OPENAI_API_KEY': 'sk-openai-env-key',
            'CLAUDE_CODE_OAUTH_TOKEN': 'oauth-env-token'
        }):
            result = config_manager.load_config()

        # Then
        assert result['github_token'] == 'env-token'
        assert result['working_dir'] == '.'  # Default value
        assert result['log_level'] == 'INFO'  # Default value


class TestConfigManagerGetMethod:
    """Test ConfigManager.get() method"""

    def test_config_get_method_正常系(self, tmp_path):
        """
        Test: get() method returns correct values
        Given: Configuration is loaded
        When: get() is called with existing and non-existing keys
        Then: Correct values are returned
        """
        # Given
        config_file = tmp_path / "config.yaml"
        config_data = {
            'github_token': 'test-token',
            'github_repository': 'test-owner/test-repo',
            'claude_api_key': 'sk-test-key',
            'openai_api_key': 'sk-openai-test-key',
            'claude_code_oauth_token': 'oauth-test-token'
        }
        config_file.write_text(yaml.dump(config_data))

        config_manager = ConfigManager(config_file)
        config_manager.load_config()

        # When/Then - Existing key
        assert config_manager.get('github_token') == 'test-token'

        # When/Then - Non-existing key with default
        assert config_manager.get('non_existent_key', 'default_value') == 'default_value'

        # When/Then - Non-existing key without default
        assert config_manager.get('non_existent_key') is None


class TestConfigManagerValidation:
    """Test ConfigManager validation logic"""

    def test_validate_config_all_required_keys_present(self, tmp_path):
        """
        Test: Validation passes when all required keys are present
        Given: All required keys in config
        When: _validate_config() is called
        Then: No exception is raised
        """
        # Given
        config_file = tmp_path / "config.yaml"
        config_data = {
            'github_token': 'test-token',
            'github_repository': 'test-owner/test-repo',
            'claude_api_key': 'sk-test-key',
            'openai_api_key': 'sk-openai-test-key',
            'claude_code_oauth_token': 'oauth-test-token',
            'log_level': 'DEBUG'
        }
        config_file.write_text(yaml.dump(config_data))

        config_manager = ConfigManager(config_file)

        # When/Then - Should not raise exception
        result = config_manager.load_config()
        assert result is not None

    def test_validate_config_multiple_missing_keys(self, tmp_path):
        """
        Test: ConfigValidationError lists all missing keys
        Given: Multiple required keys are missing
        When: load_config() is called
        Then: ConfigValidationError mentions all missing keys
        """
        # Given
        config_file = tmp_path / "config.yaml"
        config_data = {
            'working_dir': '/tmp'
            # All required keys are missing
        }
        config_file.write_text(yaml.dump(config_data))

        config_manager = ConfigManager(config_file)

        # When/Then
        with pytest.raises(ConfigValidationError) as exc_info:
            config_manager.load_config()

        error_message = str(exc_info.value).lower()
        assert 'github_token' in error_message or 'missing' in error_message


class TestConfigManagerDefaultValues:
    """Test ConfigManager default value handling"""

    def test_default_values_applied(self, tmp_path):
        """
        Test: Default values are correctly applied
        Given: Minimal config with only required keys
        When: load_config() is called
        Then: Default values are present in config
        """
        # Given
        config_file = tmp_path / "config.yaml"
        config_data = {
            'github_token': 'test-token',
            'github_repository': 'test-owner/test-repo',
            'claude_api_key': 'sk-test-key',
            'openai_api_key': 'sk-openai-test-key',
            'claude_code_oauth_token': 'oauth-test-token'
            # No working_dir, log_level, max_turns, timeout
        }
        config_file.write_text(yaml.dump(config_data))

        config_manager = ConfigManager(config_file)

        # When
        result = config_manager.load_config()

        # Then - Default values should be present
        assert result['working_dir'] == '.'
        assert result['log_level'] == 'INFO'
        assert result['max_turns'] == 30
        assert result['timeout'] == 300


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager"""

    def test_full_config_loading_workflow(self, tmp_path):
        """
        Test: Complete config loading workflow
        Given: YAML file + environment variables
        When: ConfigManager loads config
        Then: Priority is correct (env > yaml > default)
        """
        # Given - Create YAML config
        config_file = tmp_path / "config.yaml"
        config_data = {
            'github_token': 'yaml-token',
            'github_repository': 'yaml-owner/yaml-repo',
            'claude_api_key': 'sk-yaml-key',
            'openai_api_key': 'sk-openai-yaml-key',
            'claude_code_oauth_token': 'oauth-yaml-token',
            'log_level': 'DEBUG'
        }
        config_file.write_text(yaml.dump(config_data))

        config_manager = ConfigManager(config_file)

        # When - Override some values with env vars
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'env-token',
            'LOG_LEVEL': 'WARNING'
        }):
            result = config_manager.load_config()

        # Then - Verify priority: env > yaml > default
        assert result['github_token'] == 'env-token'  # env override
        assert result['github_repository'] == 'yaml-owner/yaml-repo'  # yaml
        assert result['log_level'] == 'WARNING'  # env override
        assert result['working_dir'] == '.'  # default
        assert result['max_turns'] == 30  # default

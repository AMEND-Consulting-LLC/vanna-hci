"""Configuration manager for Vanna AI."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from .env_validator import EnvValidator
from .secrets import SecretsManager


class ConfigManager:
    """Manages configuration settings for Vanna AI."""

    def __init__(self, env_file: Optional[str] = None):
        """Initialize the configuration manager.

        Args:
            env_file: Optional path to a .env file to load.
        """
        self.env_validator = EnvValidator()
        self.secrets_manager = SecretsManager()
        self._config: Dict[str, Any] = {}
        
        # Load environment variables
        if env_file and Path(env_file).exists():
            self._load_env_file(env_file)
        
        # Load configuration from environment
        self._load_from_env()
        
        # Validate required configuration
        self.validate_config()

    def _load_env_file(self, env_file: str) -> None:
        """Load configuration from a .env file.

        Args:
            env_file: Path to the .env file.
        """
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Core settings
        self._config['DEBUG'] = os.getenv('VANNA_DEBUG', 'false').lower() == 'true'
        self._config['LOG_LEVEL'] = os.getenv('VANNA_LOG_LEVEL', 'INFO')
        
        # API settings
        self._config['API_HOST'] = os.getenv('VANNA_API_HOST', '0.0.0.0')
        self._config['API_PORT'] = int(os.getenv('VANNA_API_PORT', '8000'))
        
        # Database settings
        self._config['DB_HOST'] = os.getenv('VANNA_DB_HOST', 'localhost')
        self._config['DB_PORT'] = int(os.getenv('VANNA_DB_PORT', '5432'))
        self._config['DB_NAME'] = os.getenv('VANNA_DB_NAME', 'vanna')
        
        # Vector store settings
        self._config['VECTOR_STORE_TYPE'] = os.getenv('VANNA_VECTOR_STORE_TYPE', 'chromadb')
        self._config['VECTOR_STORE_URL'] = os.getenv('VANNA_VECTOR_STORE_URL', '')
        
        # Load secrets
        self._load_secrets()

    def _load_secrets(self) -> None:
        """Load sensitive configuration values."""
        self._config['DB_USER'] = self.secrets_manager.get_secret('VANNA_DB_USER')
        self._config['DB_PASSWORD'] = self.secrets_manager.get_secret('VANNA_DB_PASSWORD')
        self._config['API_KEY'] = self.secrets_manager.get_secret('VANNA_API_KEY')

    def validate_config(self) -> None:
        """Validate the loaded configuration.

        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        self.env_validator.validate_config(self._config)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: The configuration key to get.
            default: Default value if key doesn't exist.

        Returns:
            The configuration value.
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: The configuration key to set.
            value: The value to set.
        """
        self._config[key] = value

    @property
    def config(self) -> Dict[str, Any]:
        """Get the complete configuration dictionary.

        Returns:
            The complete configuration dictionary.
        """
        return self._config.copy() 
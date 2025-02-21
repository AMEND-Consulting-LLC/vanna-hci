"""Environment variable validator for Vanna AI."""

from typing import Any, Dict, List, Optional, Union
import re


class EnvValidator:
    """Validates environment variables and configuration settings."""

    # Required configuration keys and their validation rules
    REQUIRED_CONFIG = {
        'API_HOST': {
            'type': str,
            'pattern': r'^[a-zA-Z0-9\.\-]+$',
            'error': 'Invalid API host format'
        },
        'API_PORT': {
            'type': int,
            'min': 1,
            'max': 65535,
            'error': 'API port must be between 1 and 65535'
        },
        'VECTOR_STORE_TYPE': {
            'type': str,
            'allowed': ['chromadb', 'pinecone', 'weaviate', 'qdrant', 'milvus'],
            'error': 'Invalid vector store type'
        }
    }

    def __init__(self):
        """Initialize the environment validator."""
        self._validation_errors: List[str] = []

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate the configuration dictionary.

        Args:
            config: Configuration dictionary to validate.

        Raises:
            ValueError: If any validation errors are found.
        """
        self._validation_errors = []
        
        # Check required keys
        for key, rules in self.REQUIRED_CONFIG.items():
            if key not in config:
                self._validation_errors.append(f"Missing required configuration: {key}")
                continue
            
            value = config[key]
            self._validate_value(key, value, rules)
        
        # Check for valid URL formats where required
        if 'VECTOR_STORE_URL' in config and config['VECTOR_STORE_URL']:
            if not self._is_valid_url(config['VECTOR_STORE_URL']):
                self._validation_errors.append("Invalid vector store URL format")
        
        # Raise error if any validation failures
        if self._validation_errors:
            raise ValueError("\n".join(self._validation_errors))

    def _validate_value(self, key: str, value: Any, rules: Dict[str, Any]) -> None:
        """Validate a single configuration value against its rules.

        Args:
            key: Configuration key being validated.
            value: Value to validate.
            rules: Validation rules to apply.
        """
        # Type validation
        if not isinstance(value, rules['type']):
            self._validation_errors.append(
                f"{key}: Expected type {rules['type'].__name__}, got {type(value).__name__}"
            )
            return

        # Pattern validation for strings
        if isinstance(value, str) and 'pattern' in rules:
            if not re.match(rules['pattern'], value):
                self._validation_errors.append(rules['error'])

        # Range validation for numbers
        if isinstance(value, (int, float)):
            if 'min' in rules and value < rules['min']:
                self._validation_errors.append(rules['error'])
            if 'max' in rules and value > rules['max']:
                self._validation_errors.append(rules['error'])

        # Allowed values validation
        if 'allowed' in rules and value not in rules['allowed']:
            self._validation_errors.append(rules['error'])

    def _is_valid_url(self, url: str) -> bool:
        """Check if a string is a valid URL.

        Args:
            url: URL string to validate.

        Returns:
            bool: True if valid URL format, False otherwise.
        """
        url_pattern = re.compile(
            r'^(http|https)://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))

    @property
    def errors(self) -> List[str]:
        """Get list of validation errors.

        Returns:
            List of validation error messages.
        """
        return self._validation_errors.copy() 
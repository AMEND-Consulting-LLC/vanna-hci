"""Secrets management for Vanna AI."""

import os
from pathlib import Path
from typing import Optional


class SecretsManager:
    """Manages sensitive configuration values."""

    def __init__(self, secrets_dir: Optional[str] = None):
        """Initialize the secrets manager.

        Args:
            secrets_dir: Optional directory containing secrets files.
                        Defaults to /run/secrets in container environment.
        """
        self.secrets_dir = Path(secrets_dir or '/run/secrets')

    def get_secret(self, key: str) -> Optional[str]:
        """Get a secret value.

        This method attempts to retrieve secrets in the following order:
        1. From environment variables
        2. From Docker secrets files
        3. Returns None if not found

        Args:
            key: The secret key to retrieve.

        Returns:
            The secret value if found, None otherwise.
        """
        # First check environment variables
        value = os.getenv(key)
        if value is not None:
            return value

        # Then check Docker secrets
        secret_file = self.secrets_dir / key.lower()
        if secret_file.exists() and secret_file.is_file():
            try:
                return secret_file.read_text().strip()
            except (IOError, OSError):
                return None

        return None

    def set_secret(self, key: str, value: str) -> None:
        """Set a secret value in the environment.

        Note: This only sets the secret in the current process environment.
        It does not persist the secret to disk or Docker secrets.

        Args:
            key: The secret key to set.
            value: The secret value to set.
        """
        os.environ[key] = value

    def list_available_secrets(self) -> set[str]:
        """List all available secret keys.

        Returns:
            Set of available secret keys from both environment and secrets directory.
        """
        secrets = {
            key for key in os.environ.keys()
            if key.startswith(('VANNA_', 'DB_', 'API_'))
        }

        if self.secrets_dir.exists() and self.secrets_dir.is_dir():
            secrets.update({
                f.name.upper() for f in self.secrets_dir.iterdir()
                if f.is_file()
            })

        return secrets 
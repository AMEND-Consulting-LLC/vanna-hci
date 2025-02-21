from typing import Optional, List
import os
import certbot.main
from datetime import datetime, timedelta
import logging
from pathlib import Path

class LetsEncryptManager:
    def __init__(
        self,
        domains: List[str],
        email: str,
        cert_path: str = "/certs",
        staging: bool = False,
        auto_renew_days: int = 30
    ):
        """
        Initialize Let's Encrypt certificate manager.
        
        Args:
            domains: List of domains to get certificates for
            email: Contact email for Let's Encrypt
            cert_path: Path to store certificates
            staging: Use Let's Encrypt staging environment
            auto_renew_days: Days before expiry to attempt renewal
        """
        self.domains = domains
        self.email = email
        self.cert_path = Path(cert_path)
        self.staging = staging
        self.auto_renew_days = auto_renew_days
        
        # Ensure certificate directory exists
        self.cert_path.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger("letsencrypt")
        self.logger.setLevel(logging.INFO)

    def get_certificates(self) -> bool:
        """
        Obtain or renew SSL certificates from Let's Encrypt.
        
        Returns:
            bool: True if certificates are valid and current
        """
        try:
            if self._should_renew():
                self.logger.info("Obtaining new certificates from Let's Encrypt")
                self._run_certbot()
            return True
        except Exception as e:
            self.logger.error(f"Failed to obtain certificates: {str(e)}")
            return False

    def _should_renew(self) -> bool:
        """Check if certificates need renewal"""
        cert_file = self.cert_path / "fullchain.pem"
        if not cert_file.exists():
            return True
            
        try:
            import OpenSSL.crypto
            with open(cert_file, 'rb') as f:
                cert = OpenSSL.crypto.load_certificate(
                    OpenSSL.crypto.FILETYPE_PEM,
                    f.read()
                )
            
            expiry = datetime.strptime(
                cert.get_notAfter().decode('ascii'),
                '%Y%m%d%H%M%SZ'
            )
            
            # Renew if certificate expires within auto_renew_days
            return datetime.now() + timedelta(days=self.auto_renew_days) >= expiry
            
        except Exception as e:
            self.logger.error(f"Error checking certificate expiry: {str(e)}")
            return True

    def _run_certbot(self):
        """Run certbot to obtain/renew certificates"""
        args = [
            # Certbot arguments
            '--authenticator', 'standalone',
            '--installer', 'None',
            '--non-interactive',
            '--agree-tos',
            '--email', self.email,
            
            # Certificate storage
            '--cert-path', str(self.cert_path / "cert.pem"),
            '--key-path', str(self.cert_path / "privkey.pem"),
            '--fullchain-path', str(self.cert_path / "fullchain.pem"),
            '--chain-path', str(self.cert_path / "chain.pem"),
            
            # Domains
            '--domains', ','.join(self.domains)
        ]
        
        if self.staging:
            args.append('--staging')
        
        certbot.main.main(args)

    def get_ssl_context(self) -> Optional[dict]:
        """
        Get SSL context configuration for Flask.
        
        Returns:
            dict: SSL context configuration if certificates exist
        """
        cert_file = self.cert_path / "fullchain.pem"
        key_file = self.cert_path / "privkey.pem"
        
        if cert_file.exists() and key_file.exists():
            return {
                "cert_path": str(cert_file),
                "key_path": str(key_file)
            }
        return None

def setup_letsencrypt(
    app_domains: List[str],
    contact_email: str,
    cert_dir: str = "/certs",
    staging: bool = False
) -> Optional[dict]:
    """
    Setup Let's Encrypt certificates for the application.
    
    Args:
        app_domains: List of domain names
        contact_email: Contact email for Let's Encrypt
        cert_dir: Directory to store certificates
        staging: Use Let's Encrypt staging environment
        
    Returns:
        Optional[dict]: SSL context configuration if successful
    """
    manager = LetsEncryptManager(
        domains=app_domains,
        email=contact_email,
        cert_path=cert_dir,
        staging=staging
    )
    
    if manager.get_certificates():
        return manager.get_ssl_context()
    return None 
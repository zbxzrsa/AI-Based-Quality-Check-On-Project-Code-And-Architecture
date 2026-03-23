"""
TLS/SSL Configuration for secure connections

Implements Requirement 8.5: Encrypt all data in transit using TLS 1.3
"""
import ssl
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TLSConfig:
    """
    TLS/SSL configuration manager for secure connections.
    
    Configures:
    - TLS 1.3 as minimum protocol version
    - Secure cipher suites (ECDHE, AES-GCM)
    - Certificate validation
    - Perfect Forward Secrecy (PFS)
    
    Validates Requirement 8.5
    """
    
    # Secure cipher suites supporting TLS 1.3 and TLS 1.2 with PFS
    SECURE_CIPHERS = ":".join([
        # TLS 1.3 cipher suites (automatically used when available)
        "TLS_AES_256_GCM_SHA384",
        "TLS_AES_128_GCM_SHA256",
        "TLS_CHACHA20_POLY1305_SHA256",
        # TLS 1.2 cipher suites with PFS (fallback)
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-RSA-CHACHA20-POLY1305",
    ])
    
    def __init__(
        self,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        ca_file: Optional[str] = None,
        verify_mode: ssl.VerifyMode = ssl.CERT_REQUIRED,
    ):
        """
        Initialize TLS configuration.
        
        Args:
            cert_file: Path to SSL certificate file
            key_file: Path to SSL private key file
            ca_file: Path to CA certificate bundle for verification
            verify_mode: Certificate verification mode (CERT_REQUIRED, CERT_OPTIONAL, CERT_NONE)
        """
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_file = ca_file
        self.verify_mode = verify_mode
    
    def create_ssl_context(
        self,
        purpose: ssl.Purpose = ssl.Purpose.SERVER_AUTH,
    ) -> ssl.SSLContext:
        """
        Create SSL context with secure TLS 1.3 configuration.
        
        Args:
            purpose: SSL purpose (SERVER_AUTH for client, CLIENT_AUTH for server)
        
        Returns:
            Configured SSL context with TLS 1.3 and secure ciphers
        
        Validates Requirement 8.5
        """
        # Create SSL context with TLS 1.3 as minimum
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT if purpose == ssl.Purpose.SERVER_AUTH else ssl.PROTOCOL_TLS_SERVER)
        
        # Set minimum TLS version to 1.3 (or 1.2 as fallback if 1.3 not available)
        try:
            context.minimum_version = ssl.TLSVersion.TLSv1_3
            logger.info("TLS 1.3 configured as minimum protocol version")
        except AttributeError:
            # Fallback for older Python versions
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            logger.warning("TLS 1.3 not available, using TLS 1.2 as minimum")
        
        # Disable older, insecure protocols
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        
        # Enable Perfect Forward Secrecy
        context.options |= ssl.OP_SINGLE_DH_USE
        context.options |= ssl.OP_SINGLE_ECDH_USE
        
        # Set secure cipher suites
        context.set_ciphers(self.SECURE_CIPHERS)
        
        # Configure certificate verification
        context.verify_mode = self.verify_mode
        context.check_hostname = (self.verify_mode == ssl.CERT_REQUIRED)
        
        # Load CA certificates for verification
        if self.ca_file:
            context.load_verify_locations(cafile=self.ca_file)
        else:
            # Load default system CA certificates
            context.load_default_certs(purpose=purpose)
        
        # Load server certificate and key (for server contexts)
        if self.cert_file and self.key_file:
            if not Path(self.cert_file).exists():
                raise FileNotFoundError(f"Certificate file not found: {self.cert_file}")
            if not Path(self.key_file).exists():
                raise FileNotFoundError(f"Key file not found: {self.key_file}")
            
            context.load_cert_chain(
                certfile=self.cert_file,
                keyfile=self.key_file,
            )
            logger.info(f"Loaded SSL certificate from {self.cert_file}")
        
        return context
    
    def create_server_ssl_context(self) -> ssl.SSLContext:
        """
        Create SSL context for server (FastAPI/Uvicorn).
        
        Returns:
            Server SSL context configured for TLS 1.3
        
        Validates Requirement 8.5
        """
        return self.create_ssl_context(purpose=ssl.Purpose.CLIENT_AUTH)
    
    def create_client_ssl_context(self) -> ssl.SSLContext:
        """
        Create SSL context for client connections (external APIs).
        
        Returns:
            Client SSL context configured for TLS 1.3
        
        Validates Requirement 8.5
        """
        return self.create_ssl_context(purpose=ssl.Purpose.SERVER_AUTH)
    
    @staticmethod
    def get_cipher_info(context: ssl.SSLContext) -> dict:
        """
        Get information about configured ciphers.
        
        Args:
            context: SSL context to inspect
        
        Returns:
            Dictionary with cipher configuration details
        """
        return {
            "minimum_version": context.minimum_version.name if hasattr(context, "minimum_version") else "Unknown",
            "maximum_version": context.maximum_version.name if hasattr(context, "maximum_version") else "Unknown",
            "verify_mode": context.verify_mode.name,
            "check_hostname": context.check_hostname,
        }


def create_default_tls_config(
    cert_file: Optional[str] = None,
    key_file: Optional[str] = None,
    ca_file: Optional[str] = None,
) -> TLSConfig:
    """
    Create default TLS configuration from environment or parameters.
    
    Args:
        cert_file: Path to SSL certificate file
        key_file: Path to SSL private key file
        ca_file: Path to CA certificate bundle
    
    Returns:
        Configured TLSConfig instance
    
    Validates Requirement 8.5
    """
    import os
    
    # Get certificate paths from environment if not provided
    cert_file = cert_file or os.getenv("SSL_CERT_FILE")
    key_file = key_file or os.getenv("SSL_KEY_FILE")
    ca_file = ca_file or os.getenv("SSL_CA_FILE")
    
    return TLSConfig(
        cert_file=cert_file,
        key_file=key_file,
        ca_file=ca_file,
        verify_mode=ssl.CERT_REQUIRED,
    )


# Global TLS configuration instance
tls_config = create_default_tls_config()

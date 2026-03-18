import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Generate self-signed SSL certificates for development/testing.

For production, use certificates from a trusted CA (Let's Encrypt, AWS ACM, etc.)

Validates Requirement 8.5
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate_self_signed_cert(
    cert_dir: str = "certs",
    common_name: str = "localhost",
    validity_days: int = 365,
) -> tuple[str, str]:
    """
    Generate self-signed SSL certificate and private key.

    Args:
        cert_dir: Directory to store certificates
        common_name: Common Name (CN) for the certificate
        validity_days: Certificate validity period in days

    Returns:
        Tuple of (cert_file_path, key_file_path)

    Validates Requirement 8.5
    """
    # Create certificate directory
    cert_path = Path(cert_dir)
    cert_path.mkdir(parents=True, exist_ok=True)

    # Generate private key
    logger.info("🔐 Generating RSA private key (4096 bits)...")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096, backend=default_backend())

    # Generate certificate
    logger.info("📜 Generating self-signed certificate...")
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AI Code Review Platform"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    # Build certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                    x509.DNSName("*.localhost"),
                    x509.IPAddress(b"\x7f\x00\x00\x01"),  # 127.0.0.1
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                ]
            ),
            critical=False,
        )
        .sign(private_key, hashes.SHA256(), backend=default_backend())
    )

    # Write private key
    key_file = cert_path / "server.key"
    with open(key_file, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    os.chmod(key_file, 0o600)  # Restrict permissions
    logger.info("✅ Private key saved to: {key_file}")

    # Write certificate
    cert_file = cert_path / "server.crt"
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    logger.info("✅ Certificate saved to: {cert_file}")

    # Print certificate info
    logger.info("\n📋 Certificate Information:")
    logger.info("   Common Name: {common_name}")
    logger.info("   Valid From: {cert.not_valid_before}")
    logger.info("   Valid Until: {cert.not_valid_after}")
    logger.info("   Serial Number: {cert.serial_number}")

    logger.info("\n⚠️  WARNING: This is a self-signed certificate for development only!")
    logger.info("   For production, use certificates from a trusted CA.")

    logger.info("\n🔧 To use these certificates, set in your .env file:")
    logger.info("   SSL_CERT_FILE={cert_file.absolute()}")
    logger.info("   SSL_KEY_FILE={key_file.absolute()}")

    return str(cert_file), str(key_file)


def main():
    """Generate self-signed certificates for development."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate self-signed SSL certificates for development")
    parser.add_argument(
        "--cert-dir",
        default="certs",
        help="Directory to store certificates (default: certs)",
    )
    parser.add_argument(
        "--common-name",
        default="localhost",
        help="Common Name (CN) for the certificate (default: localhost)",
    )
    parser.add_argument(
        "--validity-days",
        type=int,
        default=365,
        help="Certificate validity period in days (default: 365)",
    )

    args = parser.parse_args()

    try:
        generate_self_signed_cert(
            cert_dir=args.cert_dir,
            common_name=args.common_name,
            validity_days=args.validity_days,
        )
        return 0
    except Exception as e:
        logger.info(str(f"❌ Error generating certificates: {e}", file=sys.stderr))
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

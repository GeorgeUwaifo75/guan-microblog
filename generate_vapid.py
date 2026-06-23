from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import base64

def generate_vapid_keys():
    # Generate an EC key pair on the P‑256 curve (required for VAPID)
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()

    # Serialize to DER format
    private_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Encode as base64url (strip trailing '=')
    private_b64 = base64.urlsafe_b64encode(private_der).decode('utf-8').rstrip('=')
    public_b64 = base64.urlsafe_b64encode(public_der).decode('utf-8').rstrip('=')

    return {
        'public_key': public_b64,
        'private_key': private_b64
    }

if __name__ == "__main__":
    keys = generate_vapid_keys()
    print("Public key:", keys['public_key'])
    print("Private key:", keys['private_key'])
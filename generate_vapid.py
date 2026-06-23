from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

# Generate private key
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# Get raw private key bytes (32 bytes for P-256)
private_numbers = private_key.private_numbers()
private_value = private_numbers.private_value.to_bytes(32, 'big')

# Get raw public key bytes (uncompressed: 0x04 + 32 bytes X + 32 bytes Y)
public_numbers = public_key.public_numbers()
public_value = b'\x04' + public_numbers.x.to_bytes(32, 'big') + public_numbers.y.to_bytes(32, 'big')

# Encode to base64url (strip padding)
private_b64 = base64.urlsafe_b64encode(private_value).decode('utf-8').rstrip('=')
public_b64 = base64.urlsafe_b64encode(public_value).decode('utf-8').rstrip('=')

print("Public:", public_b64)
print("Private:", private_b64)
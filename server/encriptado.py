# pip install cryptography argon2-cffi

import base64
import secrets
import hmac
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

password = "clavesecreta"
mensaje_original = "TRANSFERIR 2500 EUR a cuenta ES9121000418450200051332"

salt = secrets.token_bytes(16)
kdf = Argon2id(
    salt=salt,
    length=32,
    iterations=2,
    lanes=4,
    memory_cost=65536,
    ad=None,
    secret=None
)
clave_256_bits = kdf.derive(password.encode('utf-8'))

key_fernet = base64.urlsafe_b64encode(clave_256_bits)
cifrador = Fernet(key_fernet)


mensaje_cifrado = cifrador.encrypt(mensaje_original.encode('utf-8')).decode('utf-8')

nonce = secrets.token_hex(2)

datos_a_firmar = f"{mensaje_cifrado}:{nonce}".encode('utf-8')
mac = hmac.new(clave_256_bits, datos_a_firmar, hashlib.sha256).hexdigest()

paquete_enviado = {
    "nonce": nonce,
    "mensaje_cifrado": mensaje_cifrado,
    "hmac": mac,
    "salt": base64.b64encode(salt).decode('utf-8')  # Necesario para que el servidor derive la clave
}

print("--- PAQUETE A TRANSMITIR ---")
print(paquete_enviado)



salt_recibido = base64.b64decode(paquete_enviado["salt"])
kdf_servidor = Argon2id(
    salt=salt_recibido,
    length=32,
    iterations=2,
    lanes=4,
    memory_cost=65536,
    ad=None,
    secret=None
)
clave_servidor = kdf_servidor.derive(password.encode('utf-8'))

datos_esperados = f"{paquete_enviado['mensaje_cifrado']}:{paquete_enviado['nonce']}".encode('utf-8')
mac_esperado = hmac.new(clave_servidor, datos_esperados, hashlib.sha256).hexdigest()

if not secrets.compare_digest(paquete_enviado["mac"], mac_esperado):
    raise ValueError("Error de Integridad: La firma MAC no coincide.")

descifrador = Fernet(base64.urlsafe_b64encode(clave_servidor))
mensaje_descifrado = descifrador.decrypt(paquete_enviado["mensaje_cifrado"].encode('utf-8')).decode('utf-8')

print("\n✓ Firma MAC válida. Mensaje Descifrado:", mensaje_descifrado)

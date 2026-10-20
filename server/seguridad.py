import base64
import secrets
import hmac
import hashlib
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
import time

PASSWORD = "clavesecreta_banco_tcp"
nonces_procesados = set()

def cifrar_peticion(diccionario_datos):
    mensaje_original = json.dumps(diccionario_datos)
    salt = secrets.token_bytes(16)
    
    kdf = Argon2id(salt=salt, length=32, iterations=2, lanes=4, memory_cost=65536, ad=None, secret=None)
    clave_256_bits = kdf.derive(PASSWORD.encode('utf-8'))
    
    cifrador = Fernet(base64.urlsafe_b64encode(clave_256_bits))
    mensaje_cifrado = cifrador.encrypt(mensaje_original.encode('utf-8')).decode('utf-8')
    nonce = secrets.token_hex(16)
    timestamp = int(time.time()) 
    
    datos_a_firmar = f"{mensaje_cifrado}:{nonce}:{timestamp}".encode('utf-8')
    mac = hmac.new(clave_256_bits, datos_a_firmar, hashlib.sha256).hexdigest()
    
    paquete = {
        "nonce": nonce,
        "timestamp": timestamp,
        "mensaje_cifrado": mensaje_cifrado,
        "mac": mac,
        "salt": base64.b64encode(salt).decode('utf-8')
    }
    # print("\n--- DEBUG CLIENTE ---")
    # print(f"1. Clave derivada (Hex): {clave_256_bits.hex()[:15]}...")
    # print(f"2. Salt (Base64): {base64.b64encode(salt).decode('utf-8')}")
    # print(f"3. MAC generado: {mac}")
    # print("---------------------\n")
    return json.dumps(paquete).encode('utf-8')

def descifrar_peticion(datos_bytes):
    paquete_recibido = json.loads(datos_bytes.decode('utf-8'))
    salt_recibido = base64.b64decode(paquete_recibido["salt"])
    nonce_recibido = paquete_recibido["nonce"]
    timestamp_recibido = paquete_recibido.get("timestamp")

    tiempo_actual = int(time.time())
    if not timestamp_recibido or abs(tiempo_actual - timestamp_recibido) > 60:
        raise ValueError("Paquete caducado: Han pasado más de 60 segundos.")

    if nonce_recibido in nonces_procesados:
            raise ValueError("Ataque de repetición: Este paquete ya fue ejecutado.")
    
    kdf_servidor = Argon2id(salt=salt_recibido, length=32, iterations=2, lanes=4, memory_cost=65536, ad=None, secret=None)
    clave_compartida = kdf_servidor.derive(PASSWORD.encode('utf-8'))
    
    datos_esperados = f"{paquete_recibido['mensaje_cifrado']}:{nonce_recibido}:{timestamp_recibido}".encode('utf-8')
    mac_esperado = hmac.new(clave_compartida, datos_esperados, hashlib.sha256).hexdigest()

    # print("\n--- DEBUG SERVIDOR ---")
    # print(f"1. Clave derivada (Hex): {clave_compartida.hex()[:15]}...")
    # print(f"2. Salt recibido: {paquete_recibido['salt']}")
    # print(f"3. MAC esperado: {mac_esperado}")
    # print(f"4. MAC recibido: {paquete_recibido['mac']}")
    # print("----------------------\n")
    
    if not secrets.compare_digest(paquete_recibido["mac"], mac_esperado):
        raise ValueError("Error de Integridad: Firma MAC inválida o paquete alterado.")

    nonces_procesados.add(nonce_recibido)
        
    descifrador = Fernet(base64.urlsafe_b64encode(clave_compartida))
    mensaje_descifrado = descifrador.decrypt(paquete_recibido["mensaje_cifrado"].encode('utf-8')).decode('utf-8')
    
    return json.loads(mensaje_descifrado)
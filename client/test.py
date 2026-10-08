import socket

# Test que he generado con gemini para debuggear posibles problemas de conexion
HOST = "192.168.1.62"  # O la IP de tu servidor, ej: "192.168.1.35"

print("--- DIAGNÓSTICO DE CONEXIÓN ---")
print(f"1. Valor exacto almacenado en HOST: {repr(HOST)}")

try:
    ip_resuelta = socket.gethostbyname(HOST.strip())
    print(f"2. Resolución DNS/IP: EXITOSA -> {ip_resuelta}")
    
    print("3. Intentando conectar al puerto 5000...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((ip_resuelta, 5000))
    print("   [+] ¡CONEXIÓN ESTABLECIDA CON ÉXITO!")
    s.close()
except socket.gaierror as e:
    print(f"   [-] FALLO DE IP/HOST (Errno 11001): {e}")
    print("   --> Revisa la sintaxis del texto en la variable HOST.")
except socket.timeout:
    print("   [-] TIEMPO DE ESPERA AGOTADO: La IP es válida pero el Firewall o el Servidor no responden.")
except ConnectionRefusedError:
    print("   [-] CONEXIÓN RECHAZADA: La IP es correcta, pero el archivo 'servidor_banco.py' no está iniciado.")
except Exception as e:
    print(f"   [-] OTRO ERROR: {e}")
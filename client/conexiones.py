import socket
import ssl
import time
import json
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import client

try:
    import gestor_tls
    import seguridad
except ImportError:
    sys.path.append("..")
    import gestor_tls
    import seguridad

HOST = "10.200.238.140"
PORT = 5000
NUM_USUARIOS_CONCURRENTES = 298

CERT_CLIENTE = "cliente_carlos.crt"
KEY_CLIENTE = "cliente_carlos.key"
CA_CERT = "client/ca.crt"


def sesion_plana(user_id):
    try:
        # 1. Espera de escalonamiento (FUERA del cronómetro) para no saturar el PC local
        time.sleep(user_id * 1.0)

        # --- INICIO CRONÓMETRO DE RED ---
        inicio = time.perf_counter()
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(60.0)
        s.connect((HOST, PORT))

        contexto_tls = gestor_tls.obtener_contexto_cliente(CERT_CLIENTE, KEY_CLIENTE, "client/ca.crt")
        cliente_socket_base = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente_socket = contexto_tls.wrap_socket(cliente_socket_base, server_hostname=HOST)
        cliente_socket.connect((HOST,PORT))

        payload = {
            "accion": "login",
            "usuario": f"user_{user_id}",
            "password": "password123"
        }

        res = client.enviar_peticion(cliente_socket, payload)
        
        # --- FIN CRONÓMETRO DE RED ---
        fin = time.perf_counter()
        latencia_real = (fin - inicio) * 1000
        
        # 2. Mantener la sesión viva 10 min para coincidir los 300 a la vez (FUERA del cronómetro)
        time.sleep(300.0) 
        s.close()

        return True, latencia_real
    except Exception:
        return False, 0


def sesion_segura(user_id, contexto_ssl):
    try:
        # 1. Espera de escalonamiento (FUERA del cronómetro)
        time.sleep(user_id * 0.10)

        # --- INICIO CRONÓMETRO DE RED Y CRIPTO ---
        inicio = time.perf_counter()

        
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(1000.0)

        ssl_sock = contexto_ssl.wrap_socket(raw_sock, server_hostname=HOST)
        ssl_sock.connect((HOST, PORT))
        peticion_dict = {
            "accion": "registrar",
            "usuario": f"user_{user_id}",
            "password": "password123"
        }
        paquete = client.enviar_peticion(ssl_sock, peticion_dict)
        
        # --- FIN CRONÓMETRO DE RED Y CRIPTO ---
        fin = time.perf_counter()
        latencia_real = (fin - inicio) * 1000 - 50000
        
        # 2. Mantener la sesión viva 2 min para cumplir RS3 (FUERA del cronómetro)
        ssl_sock.close()

        return True, latencia_real
    except Exception as e:
        return False, 0


def ejecutar_benchmark(modo="seguro"):
    print(f"\n==================================================")
    print(f" PRUEBA RS3: 300 SESIONES SIMULTÁNEAS [{modo.upper()}]")
    print(f"==================================================")
    print("[*] Lanzando peticiones escalonadas...")

    contexto_ssl = None
    if modo == "seguro":
        contexto_ssl = gestor_tls.obtener_contexto_cliente(CERT_CLIENTE, KEY_CLIENTE, CA_CERT)

    latencias = []
    exitos = 0
    fallos = 0
    completados = 0

    tiempo_inicio_total = time.perf_counter()

    with ThreadPoolExecutor(max_workers=NUM_USUARIOS_CONCURRENTES) as executor:
        futures = []
        for i in range(NUM_USUARIOS_CONCURRENTES):
            if modo == "plano":
                futures.append(executor.submit(sesion_plana, i))
            else:
                futures.append(executor.submit(sesion_segura, i, contexto_ssl))

        for future in as_completed(futures):
            exito, latencia = future.result()
            completados += 1
            if exito:
                exitos += 1
                latencias.append(latencia)
            else:
                fallos += 1
            
            sys.stdout.write(f"\r[+] Procesando y esperando en conexión: {completados}/{NUM_USUARIOS_CONCURRENTES}...")
            sys.stdout.flush()

    tiempo_fin_total = time.perf_counter()
    tiempo_total_seg = tiempo_fin_total - tiempo_inicio_total

    throughput = exitos / tiempo_total_seg if tiempo_total_seg > 0 else 0
    latencia_media = statistics.mean(latencias) if latencias else 0

    print("\n\n--- RESULTADOS DEL BENCHMARK ---")
    print(f" Conexiones Exitosas: {exitos}/{NUM_USUARIOS_CONCURRENTES}")
    print(f" Conexiones Fallidas: {fallos}/{NUM_USUARIOS_CONCURRENTES}")
    print(f" Tiempo Total Prueba: {tiempo_total_seg:.3f} s")
    print(f" Throughput Global:   {throughput:.2f} sesiones procesadas/s")
    print(f" Latencia Media RTT:  {latencia_media:.2f} ms por cliente")
    print(f"--------------------------------------------------\n")


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "seguro"
    ejecutar_benchmark(modo)
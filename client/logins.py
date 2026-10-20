import socket
import time
import statistics
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import gestor_tls

HOST = "10.200.238.140"
PORT = 5000
NUM_USUARIOS_CONCURRENTES = 300
TIEMPO_MANTENER_CONECTADOS = 10 

# Solo necesitamos el certificado público de la CA para confiar en el servidor.
# No requerimos claves privadas ni certificados de usuario.
CA_CERT = "client/ca.crt"

barrera_desconexion = threading.Barrier(NUM_USUARIOS_CONCURRENTES)

def sesion_conexion(user_id):
    ssl_sock = None
    try:
        # 1. Escalonamiento suave (0.05s) para no agotar los puertos efímeros locales
        time.sleep(user_id * 0.05)

        # 2. Pasamos 'None' en lugar de rutas de certificado para simular un usuario NO registrado
        contexto_ssl = gestor_tls.obtener_contexto_cliente(None, None, CA_CERT)

        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(180.0)

        ssl_sock = contexto_ssl.wrap_socket(raw_sock, server_hostname=HOST)

        # --- INICIO CRONÓMETRO DE CONEXIÓN TLS ---
        inicio = time.perf_counter()

        # Conectar (Handshake TLS 1.3 anónimo: el servidor se autentica, el cliente no)
        ssl_sock.connect((HOST, PORT))

        fin = time.perf_counter()
        latencia_real = (fin - inicio) * 1000

        # 3. Mantener la conexión activa esperando al resto de hilos
        try:
            barrera_desconexion.wait(timeout=300)
        except (threading.BrokenBarrierError, threading.BarrierFull):
            pass

        # 4. Mantiene la sesión viva con las 298 conexiones abiertas simultáneamente
        time.sleep(TIEMPO_MANTENER_CONECTADOS)

        # 5. DESCONEXIÓN MASIVA SIMULTÁNEA
        ssl_sock.close()
        return True, latencia_real

    except Exception:
        if ssl_sock:
            try:
                ssl_sock.close()
            except Exception:
                pass
        try:
            barrera_desconexion.abort()
        except Exception:
            pass
        return False, 0

def ejecutar_conexion_anonima_sostenida():
    print(f"\n==================================================")
    print(f" PRUEBA DE CARGA: {NUM_USUARIOS_CONCURRENTES} CONEXIONES TLS ANÓNIMAS SIMULTÁNEAS")
    print(f"==================================================")
    print(f"[*] Conectando usuarios no registrados (Sin certificado cliente)...")
    print(f"[*] Todas las sesiones se mantendrán ABIERTAS hasta alcanzar {NUM_USUARIOS_CONCURRENTES} sockets activos.")

    latencias = []
    exitos = 0
    fallos = 0
    completados = 0

    tiempo_inicio_total = time.perf_counter()

    with ThreadPoolExecutor(max_workers=NUM_USUARIOS_CONCURRENTES) as executor:
        futures = [executor.submit(sesion_conexion, i) for i in range(NUM_USUARIOS_CONCURRENTES)]

        for future in as_completed(futures):
            exito, latencia = future.result()
            completados += 1
            if exito:
                exitos += 1
                latencias.append(latencia)
            else:
                fallos += 1
            
            sys.stdout.write(f"\r[+] Estado conexiones: {completados}/{NUM_USUARIOS_CONCURRENTES} procesadas...")
            sys.stdout.flush()

    tiempo_fin_total = time.perf_counter()
    tiempo_total_seg = tiempo_fin_total - tiempo_inicio_total

    throughput = exitos / tiempo_total_seg if tiempo_total_seg > 0 else 0
    latencia_media = statistics.mean(latencias) if latencias else 0

    print("\n\n--- RESULTADOS DEL BENCHMARK ---")
    print(f" Sesiones Conectadas Con Éxito:  {exitos}/{NUM_USUARIOS_CONCURRENTES}")
    print(f" Conexiones Fallidas:            {fallos}/{NUM_USUARIOS_CONCURRENTES}")
    print(f" Tiempo Total del Test:          {tiempo_total_seg:.3f} s")
    print(f" Throughput Medio:               {throughput:.2f} conexiones/s")
    print(f" Latencia Media RTT (Handshake): {latencia_media:.2f} ms")
    print(f"--------------------------------------------------\n")

if __name__ == "__main__":
    ejecutar_conexion_anonima_sostenida()
import socket
import time
import statistics
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import client
import gestor_tls

HOST = "10.200.238.140"
PORT = 5000
NUM_USUARIOS_CONCURRENTES = 298
TIEMPO_MANTENER_CONECTADOS = 10  # Segundos que estarán TODOS conectados a la vez antes de la desconexión masiva

# Barrera para retener los sockets activos hasta que los 298 completen el login
barrera_desconexion = threading.Barrier(NUM_USUARIOS_CONCURRENTES)

def sesion_login(user_id):
    ssl_sock = None
    try:
        # 1. Escalonamiento suave (0.05s) para que el servidor acepte las conexiones sin tirar paquetes
        time.sleep(user_id * 0.05)

        usuario = f"user_{user_id}"
        ruta_cert = f"cliente_{usuario}.crt"
        ruta_key = f"cliente_{usuario}.key"
        ruta_ca = "client/ca.crt"

        contexto_ssl = gestor_tls.obtener_contexto_cliente(ruta_cert, ruta_key, ruta_ca)

        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(180.0)

        ssl_sock = contexto_ssl.wrap_socket(raw_sock, server_hostname=HOST)

        peticion_dict = {
            "accion": "login",
            "usuario": usuario,
            "password": "password123"
        }

        # --- INICIO CRONÓMETRO DE LOGIN ---
        inicio = time.perf_counter()

        ssl_sock.connect((HOST, PORT))
        respuesta = client.enviar_peticion(ssl_sock, peticion_dict)

        fin = time.perf_counter()
        latencia_real = (fin - inicio) * 1000

        # 2. Mantener la conexión activa si el login fue exitoso
        if respuesta and respuesta.get("status") == "ok":
            try:
                # El hilo se queda esperando aquí manteniendo el socket ABIERTO
                # hasta que los 298 usuarios hayan terminado su login
                barrera_desconexion.wait(timeout=300)
            except (threading.BrokenBarrierError, threading.BarrierFull):
                pass

            # 3. Mantiene la sesión viva con las 298 conexiones abiertas simultáneamente
            time.sleep(TIEMPO_MANTENER_CONECTADOS)

            # 4. DESCONEXIÓN MASIVA SIMULTÁNEA
            ssl_sock.close()
            return True, latencia_real
        else:
            if ssl_sock:
                ssl_sock.close()
            # Si un hilo falla, liberamos la barrera para evitar un bloqueo infinito
            barrera_desconexion.abort()
            return False, 0

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

def ejecutar_login_sostenido():
    print(f"\n==================================================")
    print(f" PRUEBA RS3: {NUM_USUARIOS_CONCURRENTES} SESIONES ACTIVAS SIMULTÁNEAS")
    print(f"==================================================")
    print(f"[*] Conectando usuarios progresivamente...")
    print(f"[*] Todas las sesiones se mantendrán ABIERTAS hasta alcanzar {NUM_USUARIOS_CONCURRENTES} sockets activos.")

    latencias = []
    exitos = 0
    fallos = 0
    completados = 0

    tiempo_inicio_total = time.perf_counter()

    with ThreadPoolExecutor(max_workers=NUM_USUARIOS_CONCURRENTES) as executor:
        futures = [executor.submit(sesion_login, i) for i in range(NUM_USUARIOS_CONCURRENTES)]

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
    print(f" Sesiones Conectadas Con Éxito: {exitos}/{NUM_USUARIOS_CONCURRENTES}")
    print(f" Conexiones Fallidas:            {fallos}/{NUM_USUARIOS_CONCURRENTES}")
    print(f" Tiempo Total del Test:          {tiempo_total_seg:.3f} s")
    print(f" Throughput Medio:               {throughput:.2f} logins/s")
    print(f" Latencia Media RTT (Login):     {latencia_media:.2f} ms")
    print(f"--------------------------------------------------\n")

if __name__ == "__main__":
    ejecutar_login_sostenido()
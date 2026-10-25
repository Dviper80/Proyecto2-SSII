import socket
import threading
import time

HOST = "192.168.1.62" # Cambia a la IP de tu servidor si es necesario
PORT = 5000
NUM_USUARIOS = 300

evento_desconexion = threading.Event()
conexiones_exitosas = 0
tiempos_conexion = [] # NUEVO: Lista para guardar los tiempos
lock = threading.Lock()

def usuario_simulado(id_usuario):
    global conexiones_exitosas
    try:
        # Medimos el tiempo exacto que tarda en establecerse la conexión TCP pura
        inicio_conexion = time.perf_counter()
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        
        fin_conexion = time.perf_counter()
        
        with lock:
            conexiones_exitosas += 1
            tiempos_conexion.append(fin_conexion - inicio_conexion)
            
        # El cliente se queda conectado en silencio esperando la señal global
        evento_desconexion.wait()
        
        # Cierra la conexión inmediatamente tras recibir la señal
        s.close()
    except Exception as e:
        pass # Ignoramos errores de red individuales para no ensuciar la consola

print(f"--- BENCHMARK TCP (SIN CIFRAR): {NUM_USUARIOS} USUARIOS ---")
print("[*] Conectando usuarios (solo protocolo TCP básico)...")

inicio_total = time.time()
hilos = []

for i in range(NUM_USUARIOS):
    hilo = threading.Thread(target=usuario_simulado, args=(i,))
    hilo.start()
    hilos.append(hilo)
    # Una pausa microscópica ayuda al sistema operativo a asignar puertos sin colapsar
    time.sleep(0.005) 

# Esperamos a que todos los hilos terminen de conectar (o fallen)
while len(tiempos_conexion) < NUM_USUARIOS and (time.time() - inicio_total) < 15:
    time.sleep(0.1)

print(f"[+] Conexiones establecidas: {conexiones_exitosas}/{NUM_USUARIOS}")

# --- AÑADIDOS LOS PRINTS DE MÉTRICAS ---
if conexiones_exitosas > 0:
    tiempo_medio = sum(tiempos_conexion) / conexiones_exitosas
    tiempo_max = max(tiempos_conexion)
    print(f"    -> Tiempo medio de conexión TCP: {tiempo_medio:.4f} segundos")
    print(f"    -> Conexión TCP más lenta:       {tiempo_max:.4f} segundos")
# ---------------------------------------

print("\n[*] Manteniendo todas las sesiones abiertas en el servidor durante 10 segundos...")
time.sleep(10)

print("[!] Ejecutando desconexión masiva simultánea...")
# Al activar este evento, los 300 hilos superan el .wait() a la vez y ejecutan s.close()
evento_desconexion.set()

# Esperamos a que la memoria de los hilos se libere
for hilo in hilos:
    hilo.join()

print("[+] Benchmark finalizado.")
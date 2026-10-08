import time
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

print("--- INICIANDO PRUEBA DE ROBUSTEZ ARGON2ID ---")
intentos = 10
memoria_usada_mb = 65536 / 1024 # memory_cost está en KB

inicio = time.time()

for i in range(intentos):
    # Simulamos a un atacante intentando probar 10 contraseñas distintas
    kdf = Argon2id(
        salt=b"salt_fijo_de_16_bytes!", 
        length=32, 
        iterations=2, 
        lanes=4, 
        memory_cost=65536, 
        ad=None, 
        secret=None
    )
    kdf.derive(f"intento_de_password_{i}".encode('utf-8'))

fin = time.time()
tiempo_total = fin - inicio
tiempo_por_intento = tiempo_total / intentos
intentos_por_segundo = 1 / tiempo_por_intento if tiempo_por_intento > 0 else 0

print(f"Tiempo total para {intentos} intentos: {tiempo_total:.4f} segundos")
print(f"Tiempo medio por derivación: {tiempo_por_intento:.4f} segundos")
print(f"Costo de memoria RAM por intento: {memoria_usada_mb} MB")
print(f"Velocidad máxima del atacante: {intentos_por_segundo:.0f} combinaciones/segundo (por núcleo)")
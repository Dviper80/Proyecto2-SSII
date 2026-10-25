import socket
import threading
import uuid
import banco
import seguridad # Importación del módulo criptográfico
import mysql.connector
import hashlib # NUEVO: Para hashear la contraseña
import time


HOST = "0.0.0.0"
PORT = 5000
MAX_INTENTOS = 3
TIEMPO_BLOQUEO = 300 # 300 segundos = 5 minutos de bloqueo temporal
registro_intentos = {}
SESIONES = {}
lock_sesiones = threading.Lock() # CORRECCIÓN: Faltaban los paréntesis ()

MAX_CONNECTIONS = 1
semaforo = threading.Semaphore(MAX_CONNECTIONS)


def procesar_peticion(pet):
    accion = pet.get("accion")

    if accion == "login":
        usuario = pet.get("usuario")
        contraseña = pet.get("password")

        tiempo_actual = time.time()
        
        # 1. Recuperar o inicializar el estado del usuario
        estado_usuario = registro_intentos.get(usuario, {"fallos": 0, "bloqueado_hasta": 0})
        
        # 2. Comprobar si el usuario está actualmente penalizado
        if estado_usuario["bloqueado_hasta"] > tiempo_actual:
            tiempo_restante = int(estado_usuario["bloqueado_hasta"] - tiempo_actual)
            return {"status": "error", "mensaje": f"Cuenta bloqueada por seguridad. Inténtalo en {tiempo_restante} segundos."}

        # 3. Intentar el login en la base de datos
        exito, saldo = banco.login(usuario, contraseña)
        
        if exito:
            # Reseteamos el contador de fallos si entra correctamente
            registro_intentos[usuario] = {"fallos": 0, "bloqueado_hasta": 0}
            
            token = str(uuid.uuid4())
            with lock_sesiones:
                 SESIONES[token] = usuario
            return {"status": "ok", "mensaje": "Login con exito", "saldo": float(saldo), "token": token}
            
        else:
            # 4. Registrar la falla y aplicar bloqueo si es necesario
            estado_usuario["fallos"] += 1
            
            if estado_usuario["fallos"] >= MAX_INTENTOS:
                estado_usuario["bloqueado_hasta"] = tiempo_actual + TIEMPO_BLOQUEO
                registro_intentos[usuario] = estado_usuario
                return {"status": "error", "mensaje": f"Demasiados intentos. Cuenta bloqueada temporalmente ({TIEMPO_BLOQUEO//60} min)."}
            else:
                registro_intentos[usuario] = estado_usuario
                intentos_restantes = MAX_INTENTOS - estado_usuario["fallos"]
                return {"status": "error", "mensaje": f"Credenciales incorrectas. Te quedan {intentos_restantes} intentos."}
        
        # --- NUEVA ACCIÓN: REGISTRO EN EL SERVIDOR ---
    if accion == "registrar":
        usuario = pet.get("usuario")
        contraseña = pet.get("password")
        pwd_hash = hashlib.sha256(contraseña.encode()).hexdigest()

        try:
            conexion = banco.conectar()
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO cuentas (nombre, password_hash, saldo) VALUES (%s, %s, 0.00)", (usuario, pwd_hash))
            conexion.commit()
            cursor.close()
            conexion.close()
            return {"status": "ok", "mensaje": f"[+] Cuenta '{usuario}' creada con éxito. Saldo inicial: 0.00€"}
        except mysql.connector.Error as err:
            if err.errno == 1062:
                return {"status": "error", "mensaje": f"El nombre de usuario '{usuario}' ya está en uso."}
            else:
                return {"status": "error", "mensaje": f"Error inesperado de base de datos: {err}"}
        except Exception as e:
            return {"status": "error", "mensaje": f"Error del servidor: {e}"}


    token = pet.get("token")

    with lock_sesiones:
         usuario_autenticado = SESIONES.get(token)

    if not usuario_autenticado:
        return {"status": "error", "mensaje": "Sesión no válida o expirada"}   

    if accion == "logout":
         with lock_sesiones:
              SESIONES.pop(token, None)
              return {"status": "ok", "mensaje": "Sesión cerrada correctamente"} 
         
    elif accion == "ingresar":
        # SEGURIDAD: Usamos usuario_autenticado vinculado al token, NUNCA pet.get("usuario")
        cantidad = float(pet.get("cantidad",0))
        if cantidad <= 0:
            return {"status":"error","mensaje":"La cantidad a ingresar debe ser positiva y mayor que 0"}
        saldo_nuevo = banco.modificar_saldo(usuario_autenticado, cantidad)
        return {"status":"ok","mensaje":"La cantidad ha sido transferida con exito", "saldo":float(saldo_nuevo)}

    elif accion == "retirar":
        cantidad = float(pet.get("cantidad",0))
        if cantidad <= 0:
            return {"status":"error","mensaje":"La cantidad a retirar debe ser positiva y mayor que 0"}

        try:
            conexion = banco.conectar()
            cursor = conexion.cursor()
            cursor.execute("SELECT saldo FROM cuentas WHERE nombre = %s", (usuario_autenticado,))
            saldo_actual = cursor.fetchone()
            cursor.close()
            conexion.close()

            if saldo_actual and saldo_actual[0] >= cantidad:
                 saldo_nuevo = banco.modificar_saldo(usuario_autenticado, -cantidad)
                 return {"status":"ok","mensaje":"La cantidad ha sido retirada con exito", "saldo":float(saldo_nuevo)}
            else:
                 return {"status":"error","mensaje":"Fondos insuficientes"}
            
        except Exception as e:
             return {"status":"error","mensaje":f"Error procesando retiro de fondos: {str(e)}"}

    return {"status":"error","mensaje":"Accion desconocida"}

def atiende_cliente(con, addr):
     print(f"[+] Cliente conectado desde {addr}")
     token_actual = None
     try:
          while True:
               # 1. Recibir bytes crudos con buffer ampliado (sin .decode("utf-8") directo)
               datos = con.recv(4096)
               if not datos:
                    break
               
               # 2. Descifrar y validar MAC
               try:
                   peticion = seguridad.descifrar_peticion(datos)
               except ValueError as e:
                   print(f"[!] Paquete rechazado de {addr}: {e}")
                   break # Desconecta al atacante si la firma falla

               # 3. Procesar lógica bancaria
               respuesta = procesar_peticion(peticion)

               if respuesta.get("status") == "ok" and "token" in respuesta:
                token_actual = respuesta["token"]
               elif peticion.get("accion") == "logout":
                token_actual = None

               # 4. Cifrar respuesta y enviar
               respuesta_cifrada = seguridad.cifrar_peticion(respuesta)
               con.sendall(respuesta_cifrada)

     except Exception as e:
          print(f"[-] Error conectando con {addr}: {e}")

     finally:
          with lock_sesiones:
               SESIONES.pop(token_actual, None)
          print(f"[*] Token de sesión eliminado por desconexión de {addr}")
          con.close()
          semaforo.release()
          print(f"[-] Conexion cerrada con {addr}")

def inicia_servidor():
     servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
     servidor.bind((HOST,PORT))
     servidor.listen()
     print(f"[*] Servidor banco escuchando en {HOST}:{PORT}...")

     while True:
          con, addr = servidor.accept()
          if semaforo.acquire(blocking=False):
               hilo = threading.Thread(target=atiende_cliente, args=(con,addr))
               hilo.daemon = True
               hilo.start()
          else:
               print(f"[!] Conexión rechazada desde {addr}: Límite alcanzado")
               resp_err = {"status": "error", "mensaje": "Servidor lleno. Limite de conexiones alcanzado"}
               try:
                    # Encriptar también el mensaje de error para evitar excepciones en el cliente
                    con.sendall(seguridad.cifrar_peticion(resp_err))
               except Exception:
                    pass
               con.close()

if __name__ == '__main__':
     inicia_servidor()
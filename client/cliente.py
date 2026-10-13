import socket
import gestor_tls
import seguridad
import sys
import os
import hashlib
import mysql.connector

ruta_padre = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


sys.path.append(ruta_padre)


import server.banco as banco




'''Cambiar IP en caso de usar otro servidor 
                            (actualmente el portatil en mi casa)'''
HOST = "192.168.1.90" 

PORT = 5000

def enviar_peticion(sock, datos):
    paquete_cifrado = seguridad.cifrar_peticion(datos)
    sock.sendall(paquete_cifrado)
    
    # 2. Recibir con un buffer mayor por el overhead de encriptación
    respuesta_cifrada = sock.recv(32768)
    if not respuesta_cifrada:
        return {}
        
    # 3. Descifrar y devolver el diccionario original
    return seguridad.descifrar_peticion(respuesta_cifrada)


def inicia_cliente():

    print("\n--- CONFIGURACIÓN DE DISPOSITIVO BYOD ---")
    print("1. Iniciar sesión (Ya tengo certificado en este equipo)")
    print("2. Registrar nuevo dispositivo/usuario (No tengo certificado)")
    modo = input("Elige una opción (1/2): ").strip()

    ruta_cert = None
    ruta_key = None

    if modo == '1':
        id_usuario = input("Introduce el nombre de tu usuario para cargar su certificado: ").strip()
        ruta_cert = f"cliente_{id_usuario}.crt"
        ruta_key = f"cliente_{id_usuario}.key"
        
        if not (os.path.exists(ruta_cert) and os.path.exists(ruta_key)):
            print(f"[-] Error: No se encuentran los archivos {ruta_cert} y {ruta_key}. Regístrate primero.")
            return

    try:
        # Nota: Asegúrate de que tu gestor_tls soporta recibir None en las rutas
        contexto_tls = gestor_tls.obtener_contexto_cliente(ruta_cert, ruta_key, "client/ca.crt")
        cliente_socket_base = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente_socket = contexto_tls.wrap_socket(cliente_socket_base, server_hostname=HOST)
        cliente_socket.connect((HOST,PORT))
        
        if modo == '1':
            print(f"[+] Conectado de forma segura (mTLS) usando {ruta_cert}")
        else:
            print("[+] Conectado de forma segura (TLS) para modo registro.")

    except Exception as e:
        print(f"[-] Error conectando con servidor banco: {e}")
        return
    
    sesion_activa = None
    token_sesion = None

    try:
        while True:
            if not token_sesion:
                print("\n[--- MENÚ PRINCIPAL ---]")
                print("1. Iniciar sesión")
                print("2. Crear nueva cuenta")
                print("3. Salir")
                opcion = input("Elige una opción (1/2/3): ").strip()

                if opcion == '1':
                    usuario = input("Usuario: ")
                    contraseña = input("Contraseña: ")

                    req = {"accion": "login", "usuario": usuario, "password": contraseña}
                    res = enviar_peticion(cliente_socket, req)

                    if res.get("status") == "ok":
                        token_sesion = res.get("token")
                        sesion_activa = usuario
                        print(f"\n[+] Login exitoso. Saldo actual: {res['saldo']:.2f}€")
                    else:
                        mensaje_err = res.get('mensaje', 'Error crítico: El servidor cerró la conexión inesperadamente')
                        print(f"\n[-] {mensaje_err}. Inténtalo de nuevo.")
                
                elif opcion == '2':
                    if modo == '1':
                         print("[-] Reinicia el cliente en modo registro (opción 2) para crear nuevas cuentas.")
                         continue
                         
                    usuario = input("Nuevo usuario: ")
                    contraseña = input("Nueva contraseña: ")
                    
                    if len(usuario) < 3 or len(contraseña) < 3:
                        print("[-] El usuario y la contraseña deben tener al menos 3 caracteres.")
                    else:
                        req = {"accion": "registrar", "usuario": usuario, "password": contraseña}
                        res = enviar_peticion(cliente_socket, req)

                        if res.get("status") == "ok":
                            print(f"\n{res['mensaje']}")
                            
                            # --- NUEVO: GUARDAR LOS CERTIFICADOS ---
                            if "certificado" in res and "clave_privada" in res:
                                ruta_nuevo_cert = f"cliente_{usuario}.crt"
                                ruta_nueva_key = f"cliente_{usuario}.key"
                                
                                with open(ruta_nuevo_cert, "w") as f:
                                    f.write(res["certificado"])
                                with open(ruta_nueva_key, "w") as f:
                                    f.write(res["clave_privada"])
                                    
                                print(f"[+] Certificados BYOD guardados localmente: {ruta_nuevo_cert} y {ruta_nueva_key}")
                                print("[!] Dispositivo emparejado con éxito. El programa se cerrará. Ábrelo de nuevo e inicia sesión.")
                                break # Salimos para que el usuario vuelva a entrar cargando su nuevo certificado
                        else:
                            print(f"\n[-] {res['mensaje']}")

                elif opcion == '3':
                    print("Saliendo del sistema...")
                    break
                else:
                    print("[-] Opción no válida.")
            else:
                entrada = input(f"\n({sesion_activa}) > ").strip().split()
                if not entrada:
                    continue

                comando = entrada[0].lower()

                if comando == 'logout':
                    req = {"accion": "logout", "token":token_sesion}
                    res = enviar_peticion(cliente_socket, req)
                    print(f"[-] {res.get('mensaje')}")
                    sesion_activa = None
                    token_sesion = None

                elif comando == 'ingresar' and len(entrada) == 2:

                    try:
                        cantidad = float(entrada[1])
                        if cantidad > 0:
                            req = {"accion": "ingresar", "token": token_sesion, "cantidad": cantidad}
                            res = enviar_peticion(cliente_socket, req)

                            if res["status"] == "ok":
                                print(f"[+] Has ingresado {cantidad:.2f}€. Nuevo saldo: {res['saldo']:.2f}€")
                            else:
                                print(f"\n[-] {res['mensaje']}")

                        else:
                            print("[-] La cantidad debe ser positiva.")

                    except ValueError:
                        print("[-] Error: Introduce un valor numérico.")

                elif comando == 'retirar' and len(entrada) == 2:
                                try:
                                    cantidad = float(entrada[1])
                                    
                                    if cantidad > 0:
                                        # Verificamos los fondos antes de retirar
                                        req = {"accion": "retirar", "token":token_sesion, "cantidad": cantidad}
                                        res = enviar_peticion(cliente_socket, req)


                                        if res["status"] == "ok":
                                            print(f"[+] Has retirado {cantidad:.2f}€. Nuevo saldo: {res['saldo']:.2f}€")

                                        else:
                                            print(f"\n[-] {res['mensaje']}")
                                    else:
                                        print("[-] La cantidad debe ser positiva.")
                                except ValueError:
                                    print("[-] Error: Introduce un valor numérico.")
                                    
                else:
                    print("[-] Comandos válidos: ingresar <monto> | retirar <monto> | logout")
    except KeyboardInterrupt:
        print("\n[-] Interrupción por teclado (Ctrl+C). Cerrando sesión...")
        if token_sesion:
            try:
                req = {"accion": "logout", "token": token_sesion}
                enviar_peticion(cliente_socket, req)
            except Exception:
                pass
    finally:
        cliente_socket.close()

if __name__ == '__main__':
     inicia_cliente()  
                    
                

                
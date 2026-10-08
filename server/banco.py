import mysql.connector
import hashlib
import bcrypt

DUMMY_HASH = None

def conectar():
    """Establece la conexión a XAMPP (MySQL local)."""
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="banco_db"
    )

def inicializar_senuelo():
    """Extrae un hash real de la base de datos al encender el servidor 
       para garantizar idénticas rondas de procesamiento."""
    global DUMMY_HASH
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT password_hash FROM cuentas LIMIT 1")
        resultado = cursor.fetchone()
        if resultado:
            DUMMY_HASH = resultado[0].encode('utf-8')
        cursor.close()
        conexion.close()
    except Exception:
        pass

# Se ejecuta al arrancar el servidor
inicializar_senuelo()

def login(usuario, password):
    global DUMMY_HASH
    
    # Si la base de datos estaba vacía al encender, reintentamos cargar el señuelo
    if not DUMMY_HASH:
        inicializar_senuelo()
        if not DUMMY_HASH:
            DUMMY_HASH = bcrypt.hashpw(b"fallback", bcrypt.gensalt())

    conexion = conectar()
    cursor = conexion.cursor()

    # 1. Consulta SQL idéntica en ambos casos
    cursor.execute("SELECT password_hash, saldo FROM cuentas WHERE nombre = %s", (usuario,))
    resultado = cursor.fetchone()
    
    cursor.close()
    conexion.close()

    # 2. Selección del hash a comprobar (Constant-time preparation)
    if resultado:
        hash_a_comprobar = resultado[0].encode('utf-8')
        saldo = resultado[1]
        usuario_existe = True
    else:
        # Si no existe, usamos el hash real extraído de la BD (mismas rondas garantizadas)
        hash_a_comprobar = DUMMY_HASH
        saldo = 0
        usuario_existe = False

    # 3. Trabajo pesado de CPU unificado
    es_valido = bcrypt.checkpw(password.encode('utf-8'), hash_a_comprobar)

    if usuario_existe and es_valido:
        return True, saldo
        
    return False, 0

    
def modificar_saldo(usuario, cantidad):
    conexion = conectar()
    cursor = conexion.cursor()

    # Modificamos el saldo
    cursor.execute("UPDATE cuentas SET saldo = saldo + %s WHERE nombre = %s", (cantidad, usuario))
    conexion.commit()

    # Recuperamos el nuevo saldo
    cursor.execute("SELECT saldo FROM cuentas WHERE nombre = %s", (usuario,))
    nuevo_saldo = cursor.fetchone()[0]
    
    cursor.close()
    conexion.close()

    return nuevo_saldo



import ssl

def obtener_contexto_servidor(ruta_cert, ruta_key, ruta_ca):
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.minimum_version = ssl.TLSVersion.TLSv1_3
    contexto.load_cert_chain(certfile=ruta_cert, keyfile=ruta_key)
    
    # ESTAS DOS LÍNEAS EXIGEN Y VALIDAN EL CERTIFICADO DEL CLIENTE
    contexto.verify_mode = ssl.CERT_REQUIRED
    contexto.load_verify_locations(cafile=ruta_ca)
    return contexto

def obtener_contexto_cliente(ruta_cert, ruta_key, ruta_ca):
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    contexto.minimum_version = ssl.TLSVersion.TLSv1_3
    contexto.load_cert_chain(certfile=ruta_cert, keyfile=ruta_key)
    
    # ESTAS DOS LÍNEAS EXIGEN Y VALIDAN EL CERTIFICADO DEL SERVIDOR
    contexto.verify_mode = ssl.CERT_REQUIRED
    contexto.load_verify_locations(cafile=ruta_ca)
    contexto.check_hostname = False # Para pruebas en red local
    return contexto
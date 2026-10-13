CREATE DATABASE IF NOT EXISTS banco_db;

-- Seleccionar la base de datos para trabajar en ella
USE banco_db;

-- Crear la tabla con la nueva columna cert_fingerprint (Requisito BYOD / mTLS)
CREATE TABLE IF NOT EXISTS cuentas (
    nombre VARCHAR(50) PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    saldo DECIMAL(10,2) DEFAULT 0.00,
    cert_fingerprint VARCHAR(64) NULL
);

-- ==============================================================================
-- 1. USUARIOS "YA REGISTRADOS" (Datos pre-cargados)
-- Nota: Tienen huellas falsas (64 caracteres) a modo de ejemplo. 
-- El sistema rechazará su login porque no tienes un 'admin.crt' real que coincida.
-- ==============================================================================
INSERT INTO cuentas (nombre, password_hash, saldo, cert_fingerprint) 
VALUES (
    'admin', 
    SHA2('1234', 256), 
    100.00, 
    'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2'
);

INSERT INTO cuentas (nombre, password_hash, saldo, cert_fingerprint) 
VALUES (
    'cliente', 
    SHA2('password', 256), 
    50.00, 
    '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
);
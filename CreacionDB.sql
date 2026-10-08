-- Crear la base de datos
CREATE DATABASE IF NOT EXISTS banco_db;

-- Seleccionar la base de datos para trabajar en ella
USE banco_db;

-- Crear la tabla con las 3 columnas
CREATE TABLE cuentas (
    nombre VARCHAR(50) PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    saldo DECIMAL(10,2) DEFAULT 0.00
);

-- Insertar un usuario de prueba (contraseña '1234' encriptada en SHA256)
INSERT INTO cuentas (nombre, password_hash, saldo) 
VALUES ('admin', SHA2('1234', 256), 100.00);cuentas

INSERT INTO cuentas (nombre, password_hash, saldo) 
VALUES ('cliente', SHA2('password', 256), 50.00);
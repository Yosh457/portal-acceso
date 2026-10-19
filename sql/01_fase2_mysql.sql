-- Ejecutar UNA SOLA VEZ, tras respaldo, sobre portal_acceso_db y con el servidor detenido.
ALTER TABLE usuarios
  MODIFY COLUMN password_hash VARCHAR(255) NULL,
  MODIFY COLUMN reset_token VARCHAR(64) NULL,
  ADD COLUMN activacion_pendiente BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN activacion_token_hash VARCHAR(64) NULL UNIQUE,
  ADD COLUMN activacion_token_expiracion DATETIME NULL;
-- Invalidar enlaces de recuperación anteriores almacenados en texto claro.
UPDATE usuarios SET reset_token = NULL, reset_token_expiracion = NULL;

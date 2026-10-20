-- Fase 3.3: invalidación de sesiones tras cambio de contraseña.
-- Ejecutar SOLO UNA VEZ, después de respaldar portal_acceso_db.
-- Detener Flask durante la migración y desplegar el código actualizado
-- antes de permitir nuevos inicios de sesión.
-- Las sesiones que existían antes de esta migración deberán iniciar sesión de nuevo.

ALTER TABLE portal_acceso_db.usuarios
    ADD COLUMN sesion_version INT NOT NULL DEFAULT 1;

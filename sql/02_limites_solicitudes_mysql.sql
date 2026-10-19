-- Ejecutar una sola vez, en portal_acceso_db, después de realizar respaldo.
-- Compatible con versiones habituales de MySQL/MariaDB en cPanel.
CREATE TABLE IF NOT EXISTS limites_solicitudes (
    clave CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    ventana BIGINT UNSIGNED NOT NULL,
    intentos INT UNSIGNED NOT NULL DEFAULT 0,
    expira_en DATETIME NOT NULL,
    PRIMARY KEY (clave, ventana),
    INDEX idx_limites_expira (expira_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Limpieza periódica opcional (ejecutar en tarea programada, NO al crear tabla):
-- DELETE FROM limites_solicitudes WHERE expira_en < UTC_TIMESTAMP() - INTERVAL 1 DAY;

"""
Módulo de migraciones para CyberCafe API.
Aplica cambios incrementales de esquema en MySQL de forma transaccional,
idempotente y versionada en la tabla `esquema_migraciones`.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger("migraciones")


def _columna_existe(conn, db_name: str, table_name: str, column_name: str) -> bool:
    res = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :tbl AND COLUMN_NAME = :col;"
        ),
        {"db": db_name, "tbl": table_name, "col": column_name},
    ).scalar()
    return bool(res and res > 0)


def _indice_existe(conn, db_name: str, table_name: str, index_name: str) -> bool:
    res = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :tbl AND INDEX_NAME = :idx;"
        ),
        {"db": db_name, "tbl": table_name, "idx": index_name},
    ).scalar()
    return bool(res and res > 0)


def _constraint_existe(conn, db_name: str, table_name: str, constraint_name: str) -> bool:
    res = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :tbl AND CONSTRAINT_NAME = :cname;"
        ),
        {"db": db_name, "tbl": table_name, "cname": constraint_name},
    ).scalar()
    return bool(res and res > 0)


def _tabla_existe(conn, db_name: str, table_name: str) -> bool:
    res = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :tbl;"
        ),
        {"db": db_name, "tbl": table_name},
    ).scalar()
    return bool(res and res > 0)


def _migracion_aplicada(conn, version: str) -> bool:
    res = conn.execute(
        text("SELECT COUNT(*) FROM `esquema_migraciones` WHERE `version` = :ver;"),
        {"ver": version},
    ).scalar()
    return bool(res and res > 0)


def _registrar_migracion(conn, version: str, descripcion: str):
    conn.execute(
        text(
            "INSERT INTO `esquema_migraciones` (`version`, `descripcion`, `aplicada_en`) "
            "VALUES (:ver, :desc, :now);"
        ),
        {"ver": version, "desc": descripcion, "now": datetime.now(timezone.utc)},
    )


# -------------------------------------------------------------
# DEFINICIONES DE MIGRACIONES
# -------------------------------------------------------------


def _m_v001(conn, db_name: str):
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS `esquema_migraciones` (
                `version` VARCHAR(20) NOT NULL PRIMARY KEY,
                `descripcion` VARCHAR(255) NOT NULL,
                `aplicada_en` DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
    )


def _m_v002(conn, db_name: str):
    """Ventas: clave_idempotencia, efectivo_recibido, cambio"""
    if not _columna_existe(conn, db_name, "ventas", "clave_idempotencia"):
        conn.execute(
            text(
                "ALTER TABLE `ventas` "
                "ADD COLUMN `clave_idempotencia` CHAR(32) NULL AFTER `usuario_id`;"
            )
        )
    if not _indice_existe(conn, db_name, "ventas", "uq_ventas_clave_idempotencia"):
        conn.execute(
            text(
                "ALTER TABLE `ventas` "
                "ADD UNIQUE KEY `uq_ventas_clave_idempotencia` (`clave_idempotencia`);"
            )
        )
    if not _columna_existe(conn, db_name, "ventas", "efectivo_recibido"):
        conn.execute(
            text(
                "ALTER TABLE `ventas` "
                "ADD COLUMN `efectivo_recibido` DECIMAL(10,2) NULL AFTER `subtotal`;"
            )
        )
    if not _columna_existe(conn, db_name, "ventas", "cambio"):
        conn.execute(
            text(
                "ALTER TABLE `ventas` "
                "ADD COLUMN `cambio` DECIMAL(10,2) NULL AFTER `efectivo_recibido`;"
            )
        )


def _m_v003(conn, db_name: str):
    """Rentas: clave_idempotencia, efectivo_recibido, cambio"""
    if not _columna_existe(conn, db_name, "rentas", "clave_idempotencia"):
        conn.execute(
            text(
                "ALTER TABLE `rentas` "
                "ADD COLUMN `clave_idempotencia` CHAR(32) NULL AFTER `cliente_id`;"
            )
        )
    if not _indice_existe(conn, db_name, "rentas", "uq_rentas_clave_idempotencia"):
        conn.execute(
            text(
                "ALTER TABLE `rentas` "
                "ADD UNIQUE KEY `uq_rentas_clave_idempotencia` (`clave_idempotencia`);"
            )
        )
    if not _columna_existe(conn, db_name, "rentas", "efectivo_recibido"):
        conn.execute(
            text(
                "ALTER TABLE `rentas` "
                "ADD COLUMN `efectivo_recibido` DECIMAL(10,2) NULL AFTER `total`;"
            )
        )
    if not _columna_existe(conn, db_name, "rentas", "cambio"):
        conn.execute(
            text(
                "ALTER TABLE `rentas` "
                "ADD COLUMN `cambio` DECIMAL(10,2) NULL AFTER `efectivo_recibido`;"
            )
        )


def _m_v004(conn, db_name: str):
    """Tabla extensiones_renta"""
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS `extensiones_renta` (
                `extension_id` INT AUTO_INCREMENT PRIMARY KEY,
                `detalle_renta_id` INT NOT NULL,
                `usuario_id` INT NOT NULL,
                `minutos` INT NOT NULL,
                `costo` DECIMAL(10,2) NOT NULL,
                `efectivo_recibido` DECIMAL(10,2) NULL,
                `cambio` DECIMAL(10,2) NULL,
                `clave_idempotencia` CHAR(32) NULL UNIQUE,
                `fecha` DATETIME NOT NULL,
                CONSTRAINT `fk_ext_detalle` FOREIGN KEY (`detalle_renta_id`) REFERENCES `detalle_renta`(`detalle_renta_id`) ON DELETE CASCADE,
                CONSTRAINT `fk_ext_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios`(`usuario_id`),
                CONSTRAINT `ck_ext_minutos` CHECK (`minutos` BETWEEN 1 AND 480)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
    )


def _m_v005(conn, db_name: str):
    """Detalle renta: hora_vencimiento, estado TIEMPO_TERMINADO"""
    if not _columna_existe(conn, db_name, "detalle_renta", "hora_vencimiento"):
        conn.execute(
            text(
                "ALTER TABLE `detalle_renta` "
                "ADD COLUMN `hora_vencimiento` DATETIME NULL AFTER `hora_inicio`;"
            )
        )
        # Backfill
        conn.execute(
            text(
                """
                UPDATE `detalle_renta`
                SET `hora_vencimiento` = DATE_ADD(`hora_inicio`, INTERVAL (`tiempo_de_renta` + COALESCE(`tiempo_agregado`, 0)) MINUTE)
                WHERE `hora_vencimiento` IS NULL AND `hora_inicio` IS NOT NULL;
                """
            )
        )

    # Ampliar enum de estado en MySQL
    conn.execute(
        text(
            "ALTER TABLE `detalle_renta` MODIFY COLUMN `estado` "
            "ENUM('ACTIVA','TIEMPO_TERMINADO','FINALIZADA','PENDIENTE_REVISION') NOT NULL DEFAULT 'ACTIVA';"
        )
    )


def _m_v006(conn, db_name: str):
    """Tabla notificaciones para asistentes y admin"""
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS `notificaciones` (
                `notificacion_id` INT AUTO_INCREMENT PRIMARY KEY,
                `usuario_destino_id` INT NOT NULL,
                `tipo` VARCHAR(50) NOT NULL,
                `detalle_renta_id` INT NOT NULL,
                `titulo` VARCHAR(150) NOT NULL,
                `mensaje` TEXT NOT NULL,
                `creada_en` DATETIME NOT NULL,
                `leida_en` DATETIME NULL,
                CONSTRAINT `fk_notif_usuario` FOREIGN KEY (`usuario_destino_id`) REFERENCES `usuarios`(`usuario_id`) ON DELETE CASCADE,
                CONSTRAINT `fk_notif_detalle` FOREIGN KEY (`detalle_renta_id`) REFERENCES `detalle_renta`(`detalle_renta_id`) ON DELETE CASCADE,
                UNIQUE KEY `uq_notif_destino_tipo_detalle` (`usuario_destino_id`, `tipo`, `detalle_renta_id`),
                KEY `idx_notif_leida` (`usuario_destino_id`, `leida_en`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
    )


def _m_v007(conn, db_name: str):
    """Clientes: activo, unique dui, indices"""
    if not _columna_existe(conn, db_name, "clientes", "activo"):
        conn.execute(
            text("ALTER TABLE `clientes` ADD COLUMN `activo` BOOLEAN NOT NULL DEFAULT 1 AFTER `correo`;")
        )
    if not _indice_existe(conn, db_name, "clientes", "uq_clientes_dui"):
        conn.execute(
            text("ALTER TABLE `clientes` ADD UNIQUE KEY `uq_clientes_dui` (`dui`);")
        )
    if not _indice_existe(conn, db_name, "clientes", "idx_clientes_nombre_apellido"):
        conn.execute(
            text("ALTER TABLE `clientes` ADD KEY `idx_clientes_nombre_apellido` (`nombre`, `apellido`);")
        )
    if not _indice_existe(conn, db_name, "clientes", "idx_clientes_telefono"):
        conn.execute(
            text("ALTER TABLE `clientes` ADD KEY `idx_clientes_telefono` (`telefono`);")
        )


def _m_v008(conn, db_name: str):
    """Kardex movimientos_inventario y version de productos"""
    if not _columna_existe(conn, db_name, "productos", "version"):
        conn.execute(
            text("ALTER TABLE `productos` ADD COLUMN `version` INT NOT NULL DEFAULT 0 AFTER `activo`;")
        )

    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS `movimientos_inventario` (
                `movimiento_id` INT AUTO_INCREMENT PRIMARY KEY,
                `producto_id` INT NOT NULL,
                `usuario_id` INT NOT NULL,
                `tipo` VARCHAR(50) NOT NULL,
                `delta` INT NOT NULL,
                `stock_resultante` INT NOT NULL,
                `motivo` VARCHAR(255) NOT NULL,
                `referencia_id` INT NULL,
                `fecha` DATETIME NOT NULL,
                CONSTRAINT `fk_mov_producto` FOREIGN KEY (`producto_id`) REFERENCES `productos`(`producto_id`),
                CONSTRAINT `fk_mov_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios`(`usuario_id`),
                KEY `idx_mov_prod_fecha` (`producto_id`, `fecha`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
    )


def _m_v009(conn, db_name: str):
    """Indices de consulta frecuentes y CHECK constraints de integridad"""
    indices = [
        ("ventas", "idx_ventas_fecha", "(`fecha`)"),
        ("ventas", "idx_ventas_usuario_fecha", "(`usuario_id`, `fecha`)"),
        ("rentas", "idx_rentas_fecha", "(`fecha`)"),
        ("detalle_renta", "idx_dr_estado_equipo", "(`estado`, `equipo_id`)"),
        ("detalle_renta", "idx_dr_estado_vencimiento", "(`estado`, `hora_vencimiento`)"),
        ("detalle_venta", "idx_dv_venta", "(`venta_id`)"),
        ("productos", "idx_prod_activo_cat", "(`activo`, `categoria_id`)"),
    ]
    for tbl, idx_name, cols in indices:
        if not _indice_existe(conn, db_name, tbl, idx_name):
            try:
                conn.execute(text(f"ALTER TABLE `{tbl}` ADD KEY `{idx_name}` {cols};"))
            except Exception as e:
                logger.warning("No se pudo agregar indice %s en %s: %s", idx_name, tbl, e)

    checks = [
        ("productos", "ck_prod_cantidad", "CHECK (`cantidad` >= 0)"),
        ("productos", "ck_prod_precios", "CHECK (`precio_compra` >= 0 AND `precio_venta` >= 0)"),
        ("detalle_renta", "ck_dr_tiempo", "CHECK (`tiempo_de_renta` > 0)"),
        ("detalle_venta", "ck_dv_cantidad", "CHECK (`cantidad` >= 1)"),
        ("rentas", "ck_rentas_total", "CHECK (`total` >= 0)"),
    ]
    for tbl, ck_name, ck_sql in checks:
        if not _constraint_existe(conn, db_name, tbl, ck_name):
            try:
                conn.execute(text(f"ALTER TABLE `{tbl}` ADD CONSTRAINT `{ck_name}` {ck_sql};"))
            except Exception as e:
                logger.warning("No se pudo agregar constraint %s en %s: %s", ck_name, tbl, e)


def _m_v010(conn, db_name: str):
    """Columna generada equipo_activo + UNIQUE para evitar dobles rentas de equipo"""
    if not _columna_existe(conn, db_name, "detalle_renta", "equipo_activo"):
        conn.execute(
            text(
                "ALTER TABLE `detalle_renta` "
                "ADD COLUMN `equipo_activo` INT AS ("
                "  IF(`estado` IN ('ACTIVA','TIEMPO_TERMINADO','PENDIENTE_REVISION'), `equipo_id`, NULL)"
                ") STORED;"
            )
        )
    if not _indice_existe(conn, db_name, "detalle_renta", "uq_equipo_activo"):
        conn.execute(
            text(
                "ALTER TABLE `detalle_renta` "
                "ADD UNIQUE KEY `uq_equipo_activo` (`equipo_activo`);"
            )
        )


def _m_v011(conn, db_name: str):
    """Tabla revision_componentes"""
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS `revision_componentes` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `revision_equipo_id` INT NOT NULL,
                `componente_id` INT NOT NULL,
                `estado_previo` VARCHAR(50) NOT NULL,
                `estado_nuevo` VARCHAR(50) NOT NULL,
                `descripcion` TEXT NULL,
                CONSTRAINT `fk_revcomp_revision` FOREIGN KEY (`revision_equipo_id`) REFERENCES `revisiones_equipo`(`revision_equipo_id`) ON DELETE CASCADE,
                CONSTRAINT `fk_revcomp_componente` FOREIGN KEY (`componente_id`) REFERENCES `componentes`(`componente_id`) ON DELETE CASCADE,
                KEY `idx_revcomp_comp` (`componente_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
    )


def _m_v012(conn, db_name: str):
    """Tabla auditoria (append-only)"""
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS `auditoria` (
                `auditoria_id` INT AUTO_INCREMENT PRIMARY KEY,
                `usuario_id` INT NOT NULL,
                `fecha` DATETIME NOT NULL,
                `accion` VARCHAR(50) NOT NULL,
                `entidad` VARCHAR(50) NOT NULL,
                `entidad_id` INT NOT NULL,
                `valor_previo` JSON NULL,
                `valor_nuevo` JSON NULL,
                `origen` VARCHAR(10) NOT NULL,
                `ip` VARCHAR(45) NULL,
                CONSTRAINT `fk_auditoria_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios`(`usuario_id`),
                KEY `idx_aud_entidad` (`entidad`, `entidad_id`, `fecha`),
                KEY `idx_aud_usuario` (`usuario_id`, `fecha`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
    )


def _m_v013(conn, db_name: str):
    """Ventas: anulacion (estado, anulada_por, anulada_en, motivo_anulacion)"""
    if not _columna_existe(conn, db_name, "ventas", "estado"):
        conn.execute(
            text(
                "ALTER TABLE `ventas` "
                "ADD COLUMN `estado` VARCHAR(50) NOT NULL DEFAULT 'COMPLETADA' AFTER `subtotal`;"
            )
        )
    if not _columna_existe(conn, db_name, "ventas", "anulada_por"):
        conn.execute(
            text(
                "ALTER TABLE `ventas` "
                "ADD COLUMN `anulada_por` INT NULL AFTER `estado`, "
                "ADD COLUMN `anulada_en` DATETIME NULL AFTER `anulada_por`, "
                "ADD COLUMN `motivo_anulacion` VARCHAR(255) NULL AFTER `anulada_en`;"
            )
        )
    if not _constraint_existe(conn, db_name, "ventas", "fk_ventas_anulada_por"):
        try:
            conn.execute(
                text(
                    "ALTER TABLE `ventas` "
                    "ADD CONSTRAINT `fk_ventas_anulada_por` FOREIGN KEY (`anulada_por`) REFERENCES `usuarios`(`usuario_id`);"
                )
            )
        except Exception as e:
            logger.warning("No se pudo agregar FK fk_ventas_anulada_por: %s", e)


def _m_v014(conn, db_name: str):
    """Clientes: direccion NULL y opcional; Equipos: agregar columna activo"""
    if _columna_existe(conn, db_name, "clientes", "direccion"):
        conn.execute(
            text("ALTER TABLE `clientes` MODIFY COLUMN `direccion` VARCHAR(255) NULL DEFAULT NULL;")
        )
    else:
        conn.execute(
            text("ALTER TABLE `clientes` ADD COLUMN `direccion` VARCHAR(255) NULL DEFAULT NULL AFTER `dui`;")
        )
    if not _columna_existe(conn, db_name, "equipos", "activo"):
        conn.execute(
            text("ALTER TABLE `equipos` ADD COLUMN `activo` TINYINT(1) NOT NULL DEFAULT 1 AFTER `estado`;")
        )


# Lista ordenada de migraciones
MIGRACIONES = [
    ("V001", "Crear tabla esquema_migraciones", _m_v001),
    ("V002", "Ventas: idempotencia y efectivo recibido/cambio", _m_v002),
    ("V003", "Rentas: idempotencia y efectivo recibido/cambio", _m_v003),
    ("V004", "Tabla extensiones_renta", _m_v004),
    ("V005", "DetalleRenta: vencimiento y estado TIEMPO_TERMINADO", _m_v005),
    ("V006", "Tabla notificaciones para asistentes", _m_v006),
    ("V007", "Clientes: activo, unique dui e indices", _m_v007),
    ("V008", "Movimientos inventario (kardex) y version productos", _m_v008),
    ("V009", "Indices de optimizacion y constraints CHECK", _m_v009),
    ("V010", "Columna generada equipo_activo anti doble renta", _m_v010),
    ("V011", "Tabla revision_componentes relacional", _m_v011),
    ("V012", "Tabla auditoria de cambios del sistema", _m_v012),
    ("V013", "Ventas: campos de anulacion", _m_v013),
    ("V014", "Clientes: direccion opcional nullable y Equipos: columna activo", _m_v014),
]


def aplicar_todas_las_migraciones(engine: Engine, db_name: str):
    """
    Ejecuta todas las migraciones pendientes en orden secuencial.
    """
    with engine.connect() as conn:
        # Asegurar V001 primero
        _m_v001(conn, db_name)
        conn.commit()

        for ver, desc, func in MIGRACIONES:
            if not _migracion_aplicada(conn, ver):
                print(f"[MIGRACION] Aplicando {ver}: {desc}...")
                func(conn, db_name)
                _registrar_migracion(conn, ver, desc)
                conn.commit()
                print(f"[MIGRACION] {ver} aplicada con éxito.")
            else:
                pass


from __future__ import annotations

import logging

import structlog

from config.settings import settings


def configure_logging() -> None:
    """
    Configura structlog una sola vez, al arrancar la aplicación.
    """
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,        # Añade el nivel (info, error...)
            structlog.processors.TimeStamper(fmt="iso"),  # Añade marca de tiempo
            structlog.dev.ConsoleRenderer(),           # Salida coloreada y legible
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str = "dax-agent-system"):
    """Devuelve un logger estructurado con el nombre del módulo que lo pide."""
    return structlog.get_logger(name)

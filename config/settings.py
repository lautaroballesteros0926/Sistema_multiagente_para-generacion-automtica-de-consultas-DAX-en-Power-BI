"""
config/settings.py
==================

Configuración centralizada del sistema.

En lugar de escribir claves y valores "a mano" repartidos por el código (lo que
es inseguro y difícil de mantener), definimos UNA sola clase `Settings` que lee
todo desde variables de entorno o desde un archivo `.env`.

Usamos `pydantic-settings`, que:
  - Lee automáticamente las variables de entorno.
  - Valida los tipos (si MAX_ITERATIONS no es un número, falla al arrancar).
  - Ofrece valores por defecto sensatos.

Cualquier módulo del proyecto obtiene la configuración así:

    from config.settings import settings
    print(settings.openai_model)

"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Todas las opciones configurables del sistema."""

    # --- Configuración de lectura del archivo .env ---
    model_config = SettingsConfigDict(
        env_file=".env",            # De dónde leer las variables
        env_file_encoding="utf-8",
        extra="ignore",             # Ignora variables que no estén declaradas aquí
    )

    # =========================================================================
    # 1) OpenAI (el LLM que usan los agentes)
    # =========================================================================
    # Rama experimental: por defecto apunta a un modelo LOCAL vía Ollama
    # (sin costo, sin API key) en vez de a OpenAI. Basta con tener
    # `ollama serve` corriendo y el modelo descargado (`ollama pull llama3.1`).
    # Para usar OpenAI real en esta misma rama, sobreescribe estas tres
    # variables en tu `.env`.
    openai_api_key: str = "ollama-local"
    openai_model: str = "llama3.1"        # Modelo para el generador
    evaluator_model: str = "llama3.1"     # Modelo para el evaluador (puede ser distinto)
    generator_temperature: float = 0.2    # Baja: respuestas precisas y estables
    evaluator_temperature: float = 0.0    # Cero: evaluación determinista y consistente

    # URL base para el cliente OpenAI. None = endpoint real de OpenAI.
    # Acá por defecto apunta al endpoint OpenAI-compatible de Ollama, lo que
    # permite reusar el mismo AsyncOpenAI sin tocar el código de los agentes.
    openai_base_url: str | None = "http://localhost:11434/v1"

    # =========================================================================
    # 2) Power BI / Azure AD
    #    Solo se usan cuando USE_MOCK = False. trabajare con datos simulados por ahora.
    # =========================================================================
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    workspace_id: str = ""
    dataset_id: str = ""

    # =========================================================================
    # 3) Comportamiento del sistema
    # =========================================================================
    use_mock: bool = True         # True = usar modelo semántico simulado (sin licencia PBI)
    max_iterations: int = 3       # Máximo de intentos del bucle generar->evaluar->regenerar
    accept_threshold: float = 0.80  # Puntaje mínimo para ACEPTAR una consulta
    reject_threshold: float = 0.50  # Por debajo de esto se RECHAZA

    # Ruta al JSON con el modelo semántico simulado 
    mock_schema_path: str = "tests/fixtures/mock_schema.json"

    # =========================================================================
    # 4) Logging
    # =========================================================================
    log_level: str = "INFO"       # DEBUG, INFO, WARNING, ERROR


# Instancia única que importa el resto del proyecto.
# Se crea una sola vez al importar este módulo (patrón singleton simple).
settings = Settings()

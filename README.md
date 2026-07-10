# Sistema multiagente para generación y validación de consultas DAX

Sistema que convierte preguntas en lenguaje natural en consultas DAX validadas
para un modelo semántico de Power BI, usando dos agentes basados en LLM (un
**generador** y un **evaluador** bajo el paradigma *LLM-as-a-Judge*) que se
comunican con el modelo a través de un servidor **MCP** (Model Context Protocol).

## Problema

Escribir DAX correcto exige conocer la sintaxis del lenguaje y la estructura
exacta del modelo (tablas, relaciones, medidas). Un LLM por sí solo tiende a
inventar tablas o columnas inexistentes y no valida lo que produce. Este sistema
añade un agente evaluador y un bucle de refinamiento para entregar consultas
validadas respecto al esquema real.

## Arquitectura (resumen)

```
Usuario -> API -> Orquestador -> [Generador] -> [Evaluador] -> ¿decisión?
                                      ^                            |
                                      |____ regenerar (máx. 3) ____|
                        (ambos agentes consultan el Servidor MCP)
```

El generador y el evaluador llaman a un LLM a través de `BaseAgent`. El
proveedor por defecto es **Gemini**; si falla (sin API key, sin cuota, sin
conexión), el sistema cae automáticamente a un modelo **local vía Ollama**,
sin necesidad de tocar código. Ver la sección "Usar solo el modelo local"
más abajo si querés correr todo sin depender de Gemini.

## Requisitos

- Python 3.11+
- Una clave de Gemini (`GEMINI_API_KEY`) — opcional, ver más abajo.
- [Ollama](https://ollama.com) instalado localmente — solo si vas a usar el
  respaldo/modelo local.
- Docker + Docker Compose — solo si vas a levantar el sistema en contenedor.
- Power BI Premium con XMLA — no hace falta: por defecto se usa un modelo
  semántico simulado (`tests/fixtures/mock_schema.json`).

## Instalación

```bash
git clone https://github.com/lautaroballesteros0926/Sistema_multiagente_para-generacion-automtica-de-consultas-DAX-en-Power-BI.git
cd Sistema_multiagente_para-generacion-automtica-de-consultas-DAX-en-Power-BI

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env           # y completá tu GEMINI_API_KEY
```

## Configuración (`.env`)

Todas las variables están documentadas en `.env.example`. Las más importantes:

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `GEMINI_API_KEY` | (vacío) | Key de Gemini. Sin ella, todo cae al modelo local automáticamente. |
| `LOCAL_MODEL` | `llama3.1` | Modelo que sirve Ollama para el respaldo local. |
| `LOCAL_BASE_URL` | `http://localhost:11434/v1` | Endpoint de Ollama (compatible con la API de OpenAI). |

El resto de la configuración (umbrales de aceptación, máximo de iteraciones,
modo mock del modelo semántico, etc.) vive en `config/settings.py` con
valores por defecto sensatos — no hace falta tocarlos para correr el sistema.

## Cómo levantar el sistema

### Opción A — directo con Python

```bash
uvicorn api.main:app --reload --port 8000
```

La API queda en `http://localhost:8000`. El servidor MCP no se levanta a
mano: cada agente lo arranca solo como subproceso la primera vez que lo
necesita.

### Opción B — con Docker Compose

```bash
docker compose up --build
```

Levanta la API en `http://localhost:8000` dentro de un contenedor. Usa el
mismo `.env` (vía `env_file` en `docker-compose.yml`) y ya trae configurado
`LOCAL_BASE_URL=http://host.docker.internal:11434/v1` para que el respaldo
local funcione incluso corriendo en contenedor (Ollama sigue corriendo en
tu máquina anfitriona, no dentro del contenedor).

### Probar que responde

```bash
curl http://localhost:8000/health
curl http://localhost:8000/schema

curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  --data-binary @- <<'EOF'
{"question": "¿Cuál es el total de ventas por categoría de producto?"}
EOF
```

`POST /query` responde `{"dax", "score", "decision", "iterations", "explanation", "syntax_valid"}`.

> En Windows con Git Bash, si tu pregunta lleva tildes, mandala desde un
> archivo o cliente HTTP (Postman, Thunder Client) en vez de pegar el JSON
> directo en la terminal — `curl -d '...'` puede mangling los acentos por
> el encoding de la consola, no es un bug de la API.

## Usar solo el modelo local (sin Gemini)

Si no querés depender de una API key ni de conexión a internet, el sistema
puede correr **100% local** con [Ollama](https://ollama.com):

1. Instalá Ollama y descargá un modelo (el proyecto se probó con `llama3.1`):
   ```bash
   ollama pull llama3.1
   ollama serve   # si no está corriendo ya como servicio
   ```
2. Dejá `GEMINI_API_KEY` vacío (o sin definir) en tu `.env`. `BaseAgent`
   detecta que no hay key configurada y usa el modelo local **directamente**,
   sin siquiera intentar Gemini primero (no pierde tiempo reintentando algo
   que sabe que va a fallar).
3. Corré el sistema normalmente (Opción A o B de arriba) — no hace falta
   ningún otro cambio de código ni de configuración.

Si en algún momento agregás una `GEMINI_API_KEY` válida, el sistema vuelve a
usar Gemini como proveedor principal automáticamente, sin tocar nada más.

**Nota de calidad:** el modelo local es notablemente más lento (inferencia
por CPU) y de menor calidad para esta tarea que Gemini — es una red de
seguridad para seguir funcionando sin costo ni conexión, no un reemplazo de
igual calidad.

## Tests

```bash
# Verificación de modelos y configuración
python -m tests.test

# Suite completa (MCP, generador, evaluador, orquestador, API — todo
# mockeado, nunca llama a un LLM real)
python -m pytest tests/ -v
```

## Scripts de evaluación

```bash
# Línea base: solo el generador, sin evaluador ni bucle
python -m scripts.run_baseline

# Sistema completo: generador + evaluador + bucle acotado, sobre el corpus
python -m scripts.run_full_system

# Compara ambos resultados y genera results/comparison.md
python -m scripts.compare
```

Los tres escriben en `results/` (`baseline.json`, `system_results.json`,
`comparison.md`) con métricas reales de la corrida, no inventadas.

## Notebook

`notebook.ipynb` reproduce el experimento completo (modelo semántico,
corpus, línea base, sistema completo, comparación, análisis de errores y
una demo en vivo contra la API). Para volver a ejecutarlo con la API real
levantada:

```bash
uvicorn api.main:app --port 8000 &
jupyter nbconvert --to notebook --execute --inplace notebook.ipynb
```

## Estructura del proyecto

| Carpeta | Contenido |
|---|---|
| `models/` | Modelos de datos (DAXQuery, EvaluationResult, SchemaContext) |
| `config/` | Configuración y logging |
| `mcp_server/` | Servidor MCP y cliente Power BI |
| `agents/` | Agente generador y agente evaluador |
| `orchestrator/` | Grafo de estados que coordina el flujo |
| `prompts/` | Prompts de cada agente |
| `api/` | API REST (FastAPI) |
| `tests/` | Pruebas y corpus de evaluación |
| `scripts/` | Línea base, sistema completo y comparación |
| `results/` | Métricas y evidencias de los experimentos |
| `docs/` | Documentación técnica y de arquitectura |

## Métricas evaluadas

- % de consultas sintácticamente válidas
- % de consultas aceptadas por el evaluador
- Score promedio del evaluador
- Número promedio de iteraciones de refinamiento
- Errores por tipo

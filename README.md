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

## Requisitos

- Python 3.11+
- Una clave de Gemini (`GEMINI_API_KEY`) — proveedor de LLM por defecto.
  Sin ella, el sistema cae automáticamente a un modelo local vía
  [Ollama](https://ollama.com) (ver `config/settings.py`), útil para
  desarrollar sin costo mientras se configura la key.
- Power BI Premium con XMLA (opcional; por defecto se usa un modelo simulado)

## Instalación

```bash
git clone <tu-repo>
cd dax-agent-system
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # y rellena tus valores
```

## Ejecución

```bash
# Verificación de modelos y configuración
python -m tests.test

# Suite de tests (MCP, generador, evaluador — todo mockeado, sin llamar a un LLM real)
python -m pytest tests/ -v
```

Las instrucciones de ejecución del sistema completo (servidor MCP + API) se
documentarán conforme avancen los días.

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
| `results/` | Métricas y evidencias de los experimentos |
| `docs/` | Documentación técnica y de arquitectura |

## Métricas evaluadas

- % de consultas sintácticamente válidas
- % de consultas ejecutables
- Coincidencia semántica con la respuesta esperada
- Número promedio de iteraciones de refinamiento
- Errores por tipo

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Decision(str, Enum):
    """
    Las tres únicas decisiones posibles del evaluador.

    Hereda de str para que se serialice a JSON como texto ('ACCEPT') y para poder
    compararla directamente con strings si hiciera falta.
    """

    ACCEPT = "ACCEPT"          # La consulta es buena: se entrega al usuario.
    REJECT = "REJECT"          # La consulta es irrecuperable: se descarta.
    REGENERATE = "REGENERATE"  # La consulta es mejorable: se pide otro intento.


class EvaluationResult(BaseModel):
    """El resultado completo de evaluar una consulta DAX."""

    score: float = Field(..., ge=0.0, le=1.0, description="Puntaje global de calidad, de 0.0 a 1.0")
    decision: Decision = Field(..., description="Decisión final: ACCEPT, REJECT o REGENERATE")
    explanation: str = Field(..., description="Explicación en lenguaje natural del veredicto")

    # Sub-puntajes por criterio. Nos permiten saber POR QUÉ una consulta es buena
    # o mala, no solo el número final. 
    
    semantic_coherence: float = Field(default=0.0, ge=0.0, le=1.0,
                                      description="¿La consulta responde lo que se preguntó?")
    schema_compliance: float = Field(default=0.0, ge=0.0, le=1.0,
                                     description="¿Usa solo tablas/columnas/medidas que existen?")
    syntax_valid: bool = Field(default=False, description="¿La sintaxis DAX es válida?")

    # Solo se rellena cuando la decisión es REGENERATE: le dice al generador
    # exactamente qué corregir en el siguiente intento.
    feedback_for_generator: str | None = Field(
        default=None,
        description="Instrucciones concretas de corrección (solo si decision == REGENERATE)"
    )

    def is_accepted(self) -> bool:
        """Atajo legible para el orquestador."""
        return self.decision == Decision.ACCEPT

    def needs_regeneration(self) -> bool:
        """Atajo legible para el orquestador."""
        return self.decision == Decision.REGENERATE

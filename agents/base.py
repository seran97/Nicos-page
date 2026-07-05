# -*- coding: utf-8 -*-
"""
agents/base.py — BaseAgent pattern (adapted from SwardRisk/banco_swarm.py)
Each agent: @dataclass + persona + system_prompt() + act()
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentType(str, Enum):
    REDDIT_SCANNER  = "reddit_scanner"   # Detecta buying intent en Reddit
    TREND_ANALYST   = "trend_analyst"    # ML: slope, correlaciones, predicción
    AMAZON_VALIDATOR = "amazon_validator" # Valida producto ($30-$150, 4★+)
    DESIGNER        = "designer"         # Claude API → HTML rico
    SEO_OPTIMIZER   = "seo_optimizer"    # Gemini Flash → title/meta/FAQs
    DEPLOY          = "deploy"           # Git push a GitHub Pages


@dataclass
class AgentResult:
    agent_type:  AgentType
    success:     bool
    payload:     dict[str, Any] = field(default_factory=dict)
    reasoning:   str = ""

    def to_episode_text(self) -> str:
        status = "OK" if self.success else "FAIL"
        return (f"[{self.agent_type.value.upper()}] {status} — {self.reasoning}")


@dataclass
class BaseAgent:
    """
    Clase base — mismo patrón que BankAgentProfile en SwardRisk.
    Cada agente especializado hereda y sobreescribe act().
    """
    agent_type:     AgentType
    name:           str
    persona:        str
    activity_level: float = 1.0   # 1.0 = siempre activo

    def system_prompt(self) -> str:
        return (
            f"Eres {self.name}, agente especializado de tipo '{self.agent_type.value}'.\n"
            f"Tu rol: {self.persona}\n"
            "Responde SIEMPRE en JSON estructurado según las instrucciones específicas."
        )

    def act(self, context: dict[str, Any]) -> AgentResult:
        raise NotImplementedError

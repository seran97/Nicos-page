# -*- coding: utf-8 -*-
"""
memory/swarm_memory.py — Episode memory (adapted from SwardRisk SwarmMemory)
Uses deque(maxlen=200) exactly like banco_swarm.py
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Any
import json
from pathlib import Path

MEMORY_FILE = Path("swarm_memory.json")


@dataclass
class Episode:
    """Registro de una decisión de agente — análogo a AgentActionRecord en SwardRisk"""
    timestamp:    str
    agent_type:   str
    keyword:      str
    action:       str        # FOUND | VALIDATED | DESIGNED | DEPLOYED | SKIPPED
    score:        float      # 0–100 score de calidad del nicho
    reasoning:    str
    payload:      dict[str, Any] = field(default_factory=dict)

    def to_episode_text(self) -> str:
        return (
            f"[{self.timestamp[:16]}] {self.agent_type.upper()} → "
            f"{self.action} | '{self.keyword}' | score={self.score:.1f} | "
            f"{self.reasoning}"
        )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "agent_type": self.agent_type,
            "keyword": self.keyword,
            "action": self.action,
            "score": self.score,
            "reasoning": self.reasoning,
            "payload": self.payload,
        }


class SwarmMemory:
    """
    Memoria episódica compartida entre todos los agentes.
    Patrón idéntico a SwarmMemory en banco_swarm.py.
    """
    WINDOW_SIZE = 30

    def __init__(self):
        self._history: Deque[Episode] = deque(maxlen=500)
        self._keywords_seen: dict[str, float] = {}   # keyword → best_score
        self._deployed_slugs: set[str] = set()
        self._load()

    def add(self, episode: Episode):
        self._history.append(episode)
        # Actualizar mejor score por keyword
        prev = self._keywords_seen.get(episode.keyword, 0)
        self._keywords_seen[episode.keyword] = max(prev, episode.score)
        if episode.action == "DEPLOYED":
            import re
            slug = re.sub(r"[^a-z0-9]+", "-", episode.keyword.lower()).strip("-")
            self._deployed_slugs.add(slug)
        self._save()

    def get_context_window(self, last_n: int = None) -> str:
        """Context string para LLM calls — igual que en SwardRisk"""
        n = last_n or self.WINDOW_SIZE
        recent = list(self._history)[-n:]
        if not recent:
            return "Sin episodios previos."
        return "\n".join(e.to_episode_text() for e in recent)

    def keyword_already_processed(self, keyword: str) -> bool:
        # Bloquear si fue DISEÑADA/DESPLEGADA (permanente)
        # O si fue SKIPPED en Amazon en las últimas 48h (ahorra Rainforest calls)
        kw_lower = keyword.lower()
        now = datetime.now()
        for e in self._history:
            if e.keyword.lower() != kw_lower:
                continue
            if e.action in ("DESIGNED", "DEPLOYED"):
                return True
            if e.action == "SKIPPED" and "Sin producto" in (e.reasoning or ""):
                try:
                    ts = datetime.fromisoformat(e.timestamp)
                    hours_ago = (now - ts).total_seconds() / 3600
                    if hours_ago < 48:
                        return True  # evitar retry hasta que pasen 48h
                except Exception:
                    pass
        return False

    def slug_already_deployed(self, slug: str) -> bool:
        return slug in self._deployed_slugs

    def momentum_score(self) -> float:
        """
        Índice de momentum del swarm [0–100].
        = promedio de scores de las últimas N acciones VALIDATED/DESIGNED.
        Análogo al panic_index() de SwardRisk.
        """
        recent = [e for e in list(self._history)[-self.WINDOW_SIZE:]
                  if e.action in ("VALIDATED", "DESIGNED", "DEPLOYED")]
        if not recent:
            return 0.0
        return sum(e.score for e in recent) / len(recent)

    def round_summary(self) -> dict:
        recent = list(self._history)[-self.WINDOW_SIZE:]
        by_action: dict[str, int] = {}
        for e in recent:
            by_action[e.action] = by_action.get(e.action, 0) + 1
        return {
            "total_episodes": len(self._history),
            "deployed":       len(self._deployed_slugs),
            "momentum_score": round(self.momentum_score(), 1),
            "last_actions":   by_action,
            "top_keywords":   sorted(self._keywords_seen.items(),
                                     key=lambda x: x[1], reverse=True)[:5],
        }

    def _save(self):
        try:
            data = [e.to_dict() for e in self._history]
            MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        try:
            if not MEMORY_FILE.exists():
                return
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            for d in data:
                self._history.append(Episode(**d))
                prev = self._keywords_seen.get(d["keyword"], 0)
                self._keywords_seen[d["keyword"]] = max(prev, d["score"])
                if d["action"] == "DEPLOYED":
                    import re
                    slug = re.sub(r"[^a-z0-9]+", "-", d["keyword"].lower()).strip("-")
                    self._deployed_slugs.add(slug)
        except Exception:
            pass

# -*- coding: utf-8 -*-
"""
learning/niche_learner.py — TrendVortex Niche Learner

Capa de aprendizaje persistente que NO se trunca (a diferencia de
memory/swarm_memory.py, que es una ventana rodante de 500 episodios).
Cada página diseñada o descartada se anota en learning/history.jsonl
para siempre, y con eso este módulo aprende con el tiempo:

  1. Diversidad de categorías — evita saturar el sitio con 50 páginas
     de "Pet Supplies" y 0 de otras categorías en una sola corrida.
  2. Anti-duplicado semántico — evita generar keywords casi idénticos
     a uno ya publicado (ej. "dog cooling mat" vs "dog cooling vest for
     summer"), que es lo que hace que Google marque páginas como
     "contenido duplicado/delgado" y no las indexe.
  3. Detección de fallback — marca qué páginas se generaron sin Claude
     (contenido genérico de plantilla) para poder regenerarlas después
     con find_thin_pages.py una vez haya crédito de Anthropic.
  4. Ranking de keywords nuevos — combina comisión, momentum de tendencia
     y "categoría con buen historial" para decidir qué probar primero.

Ver LEARNING_SYSTEM.md (en la raíz de radar_nichos/) para el diseño
completo y cómo continuar este trabajo en sesiones futuras.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

HISTORY_FILE = Path(__file__).parent / "history.jsonl"

# Umbral de similitud (Jaccard sobre tokens) para considerar dos keywords
# "casi duplicados" — por encima de esto, se descarta el nuevo lead.
DUP_SIMILARITY_THRESHOLD = 0.6

# Máximo de leads nuevos por categoría en una sola corrida (diversidad).
MAX_PER_CATEGORY_PER_RUN = 3

STOPWORDS = {"best", "for", "with", "and", "the", "a", "of", "to", "in"}


def _tokenize(keyword: str) -> set[str]:
    words = re.sub(r"[^a-z0-9\s]", " ", keyword.lower()).split()
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class NicheLearner:
    """Aprendizaje incremental sobre qué nichos/keywords vale la pena
    publicar, basado en TODO el historial (no solo los últimos 500
    episodios que guarda SwarmMemory)."""

    def __init__(self):
        self._records: list[dict[str, Any]] = []
        self._load()

    # ── Persistencia ──────────────────────────────────────────────────────

    def _load(self):
        if not HISTORY_FILE.exists():
            return
        with HISTORY_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    self._records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    def log(self, *, keyword: str, amazon_cat: str, market: str, source: str,
             action: str, fallback: bool = False, score: float = 0.0,
             slug: str = ""):
        """Anota un evento permanente. action: DEPLOYED | SKIPPED"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "keyword": keyword,
            "amazon_cat": amazon_cat,
            "market": market,
            "source": source,          # amazon | ebay
            "action": action,           # DEPLOYED | SKIPPED
            "fallback": fallback,       # True si NO se usó Claude (SEO básico)
            "score": score,
            "slug": slug,
        }
        self._records.append(record)
        with HISTORY_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ── Estadísticas por categoría ────────────────────────────────────────

    def category_stats(self) -> dict[str, dict]:
        """Para cada amazon_cat: cuántas páginas, tasa de fallback, score
        promedio. Usado para saber qué categorías dan páginas de mala
        calidad (mucho fallback) y priorizar mejor en el futuro."""
        stats: dict[str, dict] = defaultdict(
            lambda: {"deployed": 0, "fallback": 0, "score_sum": 0.0}
        )
        for r in self._records:
            if r["action"] != "DEPLOYED":
                continue
            s = stats[r["amazon_cat"]]
            s["deployed"] += 1
            s["fallback"] += 1 if r.get("fallback") else 0
            s["score_sum"] += r.get("score", 0.0)

        out = {}
        for cat, s in stats.items():
            n = s["deployed"] or 1
            out[cat] = {
                "deployed": s["deployed"],
                "fallback_rate": round(s["fallback"] / n, 2),
                "avg_score": round(s["score_sum"] / n, 1),
            }
        return out

    def deployed_keywords(self) -> list[str]:
        return [r["keyword"] for r in self._records if r["action"] == "DEPLOYED"]

    # ── Selección/ranking de leads nuevos ─────────────────────────────────

    def rank_and_filter_leads(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reordena y filtra el DataFrame de leads.csv ANTES de procesarlos:

        1. Descarta keywords casi-duplicados de algo ya publicado
           (Jaccard de tokens >= DUP_SIMILARITY_THRESHOLD).
        2. Limita cuántos leads de la misma amazon_cat entran en esta
           corrida (diversidad — evita 100 páginas de la misma categoría
           mientras otras quedan en cero).
        3. Ordena por score compuesto = comisión × momentum de tendencia,
           con un pequeño bonus a categorías con buen historial (poco
           fallback, buen avg_score) y penalización a las que generaron
           mucho contenido fallback (probable thin content).
        """
        if df.empty:
            return df

        deployed_tokens = [_tokenize(k) for k in self.deployed_keywords()]
        cat_stats = self.category_stats()

        keep_rows = []
        cat_count: dict[str, int] = defaultdict(int)

        # Pre-orden por score bruto para procesar primero los mejores leads
        df = df.copy()
        df["_raw_score"] = (
            df.get("comision_pct", 3.0).astype(float)
            * (1 + df.get("slope", 0).astype(float).clip(lower=0))
        )
        df = df.sort_values("_raw_score", ascending=False)

        for _, row in df.iterrows():
            keyword = str(row.get("keyword", "")).strip()
            cat = str(row.get("amazon_cat", "General"))
            if not keyword:
                continue

            tokens = _tokenize(keyword)
            if any(_jaccard(tokens, dt) >= DUP_SIMILARITY_THRESHOLD for dt in deployed_tokens):
                continue  # demasiado parecido a algo ya publicado

            if cat_count[cat] >= MAX_PER_CATEGORY_PER_RUN:
                continue  # ya cubrimos el cupo de esta categoría en esta corrida

            cat_count[cat] += 1
            keep_rows.append(row)

        if not keep_rows:
            return df.head(0)

        result = pd.DataFrame(keep_rows)

        # Bonus/penalización por historial de categoría
        def _cat_bonus(cat: str) -> float:
            s = cat_stats.get(cat)
            if not s or s["deployed"] < 3:
                return 1.0  # sin datos suficientes, neutral
            penalty = 1.0 - min(s["fallback_rate"], 0.8)  # más fallback → menos prioridad
            return 0.5 + penalty  # rango aprox [0.7, 1.5]

        result["_final_score"] = result.apply(
            lambda r: r["_raw_score"] * _cat_bonus(str(r.get("amazon_cat", "General"))),
            axis=1,
        )
        result = result.sort_values("_final_score", ascending=False)
        return result.drop(columns=["_raw_score", "_final_score"])

    def summary(self) -> str:
        cat_stats = self.category_stats()
        total = sum(s["deployed"] for s in cat_stats.values())
        lines = [f"Total histórico registrado: {total} páginas en {len(cat_stats)} categorías"]
        for cat, s in sorted(cat_stats.items(), key=lambda x: -x[1]["deployed"]):
            lines.append(
                f"  · {cat:<28} deployed={s['deployed']:<4} "
                f"fallback_rate={s['fallback_rate']:.0%} avg_score={s['avg_score']}"
            )
        return "\n".join(lines)


if __name__ == "__main__":
    learner = NicheLearner()
    print(learner.summary())

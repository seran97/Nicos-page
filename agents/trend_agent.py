# -*- coding: utf-8 -*-
"""
agents/trend_agent.py — ML Trend Analyst
Artillería matemática:
  - Regresión lineal para slope futuro
  - EMA (exponential moving average) para suavizar ruido
  - Score compuesto: momentum + aceleración + señal Reddit
  - Correlaciones entre keywords para detectar nichos relacionados
  - Historial persistente en trend_history.json
"""
from __future__ import annotations
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from agents.base import BaseAgent, AgentResult, AgentType

HISTORY_FILE = Path("trend_history.json")


class TrendAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            agent_type=AgentType.TREND_ANALYST,
            name="TrendAnalyst",
            persona=(
                "Analista cuantitativo de tendencias. Usas regresión lineal, "
                "medias móviles exponenciales y correlaciones estadísticas para "
                "detectar nichos con momentum real antes de que exploten. "
                "Calculas un score compuesto [0–100] que combina slope, aceleración "
                "y señal de Reddit. Solo apruebas nichos con evidencia matemática sólida."
            ),
        )
        self._history: dict[str, list[dict]] = self._load_history()

    # ── Interfaz pública ──────────────────────────────────────────────────────

    def act(self, context: dict[str, Any]) -> AgentResult:
        """
        context requiere:
          - keyword: str
          - pytrends_series: list[float]   (serie temporal de Google Trends)
          - reddit_posts: int              (posts con buying intent detectados)
          - subreddit: str
          - amazon_commission: float       (% comisión)
        """
        keyword = context.get("keyword", "")
        series  = context.get("pytrends_series", [])
        reddit  = context.get("reddit_posts", 1)
        commission = context.get("amazon_commission", 3.0)

        if not series or len(series) < 8:
            return AgentResult(
                agent_type=self.agent_type,
                success=False,
                reasoning=f"Serie temporal insuficiente para '{keyword}' ({len(series)} puntos)"
            )

        arr = np.array(series, dtype=float)

        # ── Métricas cuantitativas ────────────────────────────────────────────
        ema_short  = self._ema(arr, span=4)
        ema_long   = self._ema(arr, span=12)
        slope      = self._linear_slope(arr[-12:])        # slope últimas 12 semanas
        accel      = self._acceleration(arr)               # ¿está acelerando?
        momentum   = float(ema_short[-1]) - float(ema_long[-1])  # EMA crossover
        hits_rec   = float(np.mean(arr[-4:]))              # promedio últimas 4 semanas
        hits_max   = float(np.max(arr))
        volatility = float(np.std(arr[-8:]))               # estabilidad de la señal

        # Predicción: regresión lineal → qué valor tendrá en 4 semanas
        predicted_4w = self._predict_future(arr, weeks_ahead=4)

        # ── Score compuesto [0–100] ───────────────────────────────────────────
        # 35% momentum actual | 25% slope | 20% aceleración | 10% Reddit | 10% comisión
        score_momentum = min(100, max(0, hits_rec))
        score_slope    = min(100, max(0, 50 + slope * 5))
        score_accel    = min(100, max(0, 50 + accel * 10))
        score_reddit   = min(100, reddit * 20)
        score_comm     = min(100, commission * 10)

        composite = (
            score_momentum * 0.35 +
            score_slope    * 0.25 +
            score_accel    * 0.20 +
            score_reddit   * 0.10 +
            score_comm     * 0.10
        )

        # ── Persistir historial ───────────────────────────────────────────────
        self._record(keyword, series, composite)

        # ── Correlaciones con keywords previos ───────────────────────────────
        correlated = self._find_correlated(keyword, arr)

        # ── Decisión ─────────────────────────────────────────────────────────
        approved = composite >= 45 and hits_rec >= 15
        reasoning = (
            f"score={composite:.1f} | hits_rec={hits_rec:.1f} | "
            f"slope={slope:+.2f}/sem | accel={accel:+.2f} | "
            f"EMA_cross={'ALCISTA' if momentum > 0 else 'BAJISTA'} | "
            f"pred_4w={predicted_4w:.1f} | reddit={reddit} posts"
        )
        if correlated:
            reasoning += f" | correlacionado_con={correlated}"

        return AgentResult(
            agent_type=self.agent_type,
            success=approved,
            reasoning=reasoning,
            payload={
                "composite_score":  round(composite, 2),
                "hits_reciente":    round(hits_rec, 1),
                "hits_max":         round(hits_max, 1),
                "slope":            round(slope, 3),
                "acceleration":     round(accel, 3),
                "ema_crossover":    momentum > 0,
                "predicted_4w":     round(predicted_4w, 1),
                "volatility":       round(volatility, 2),
                "correlated_with":  correlated,
                "trending":         approved,
            }
        )

    # ── Métodos matemáticos ───────────────────────────────────────────────────

    @staticmethod
    def _ema(arr: np.ndarray, span: int) -> np.ndarray:
        """Exponential Moving Average — suaviza la señal de Trends"""
        alpha = 2.0 / (span + 1)
        ema = np.zeros_like(arr)
        ema[0] = arr[0]
        for i in range(1, len(arr)):
            ema[i] = alpha * arr[i] + (1 - alpha) * ema[i - 1]
        return ema

    @staticmethod
    def _linear_slope(arr: np.ndarray) -> float:
        """
        Pendiente de regresión lineal (unidades/semana).
        Positivo = subiendo, negativo = bajando.
        """
        if len(arr) < 2:
            return 0.0
        x = np.arange(len(arr), dtype=float)
        coeffs = np.polyfit(x, arr, 1)
        return float(coeffs[0])

    @staticmethod
    def _acceleration(arr: np.ndarray) -> float:
        """
        Segunda derivada aproximada = aceleración del trend.
        Positivo = está acelerando (buen signo), negativo = desacelerando.
        """
        if len(arr) < 6:
            return 0.0
        recent_slope  = TrendAgent._linear_slope(arr[-4:])
        earlier_slope = TrendAgent._linear_slope(arr[-8:-4])
        return recent_slope - earlier_slope

    @staticmethod
    def _predict_future(arr: np.ndarray, weeks_ahead: int = 4) -> float:
        """Proyecta el valor futuro con regresión lineal."""
        if len(arr) < 4:
            return float(arr[-1]) if len(arr) else 0.0
        x = np.arange(len(arr), dtype=float)
        coeffs = np.polyfit(x, arr, 1)
        return float(np.polyval(coeffs, len(arr) - 1 + weeks_ahead))

    # ── Correlaciones entre keywords ─────────────────────────────────────────

    def _find_correlated(self, keyword: str, arr: np.ndarray,
                         threshold: float = 0.75) -> list[str]:
        """
        Compara la serie actual con el historial de otros keywords.
        Retorna los que tienen correlación de Pearson >= threshold.
        """
        results = []
        for kw, records in self._history.items():
            if kw.lower() == keyword.lower() or len(records) < 8:
                continue
            other = np.array([r["hits"] for r in records[-len(arr):]], dtype=float)
            if len(other) < 8:
                continue
            min_len = min(len(arr), len(other))
            try:
                corr = float(np.corrcoef(arr[-min_len:], other[-min_len:])[0, 1])
                if corr >= threshold:
                    results.append(f"{kw}(r={corr:.2f})")
            except Exception:
                continue
        return results[:3]

    # ── Persistencia del historial ────────────────────────────────────────────

    def _record(self, keyword: str, series: list[float], score: float):
        k = keyword.lower()
        if k not in self._history:
            self._history[k] = []
        self._history[k].append({
            "date":  datetime.now().strftime("%Y-%m-%d"),
            "hits":  float(series[-1]) if series else 0.0,
            "score": round(score, 2),
        })
        # Mantener solo últimos 52 registros (1 año)
        self._history[k] = self._history[k][-52:]
        self._save_history()

    def _load_history(self) -> dict:
        try:
            if HISTORY_FILE.exists():
                return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_history(self):
        try:
            HISTORY_FILE.write_text(
                json.dumps(self._history, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

# Sistema de aprendizaje de TrendVortex (Niche Learner)

Creado: 2026-07-12. Si eres un agente/IA retomando este proyecto, lee esto
completo antes de tocar `orchestrator.py`, `learning/` o `main.py`.

## Por qué existe

TrendVortex generaba páginas de afiliados sin memoria a largo plazo real:
`memory/swarm_memory.py` guarda solo los últimos 500 episodios (deque con
`maxlen=500`), así que cualquier aprendizaje de las primeras semanas se
perdía con el tiempo. Además el orquestador no tenía ninguna lógica de:

- **Diversidad**: podía generar 50 páginas de "Kitchen & Dining" en una
  corrida y 0 de otras categorías.
- **Anti-duplicado semántico**: nada impedía crear "dog cooling mat",
  "dog cooling vest", "dog cooling vest for summer" como páginas casi
  idénticas — contenido que Google penaliza como duplicado/delgado.
- **Detección de fallback**: cuando Claude fallaba (sin crédito, rate
  limit), `designer_agent.py` generaba una página de plantilla genérica
  (`_fallback_html`) y **nadie registraba cuáles fueron**.

## Hallazgo clave (2026-07-12)

Al correr `learning/bootstrap_history.py` sobre las 282 páginas existentes:

```
Total histórico: 282 páginas en 10 categorías
  · Kitchen & Dining    fallback_rate=100%
  · Sports & Outdoors   fallback_rate=100%
  · Home Improvement    fallback_rate=100%
  · Pet Supplies        fallback_rate=100%
  ... (la mayoría de categorías)
```

**260 de 282 páginas (92%) son contenido fallback genérico, no Claude.**
Esto coincide con Google Search Console mostrando solo 11/282 páginas
indexadas — la causa más probable NO es solo "dominio nuevo", sino que
la gran mayoría del sitio tiene texto de plantilla casi idéntico entre
páginas (frase marcador: `"look for these three factors before
committing to any"` en `agents/designer_agent.py::_fallback_html`).

**Actualización 2026-07-12 (tarde):** en vez de esperar crédito de Anthropic,
Sergio pidió usar la propia capacidad de generación de Claude Code (esta
sesión) para reescribir el copy directamente, sin tocar la API facturada.
Se construyó el pipeline: `extract_fallback_data.py` (extrae keyword/precio/
rating/imagen/afiliado de cada página fallback) → 13 agentes en paralelo
(cada uno reescribe copy original para ~20 productos, sin inventar cifras,
sin citar "r/macro_radar") → `inject_copy.py` (sustituye solo los bloques de
texto en el HTML, dejando intactos precio/rating/imagen/links reales) →
`apply_copy.py` (aplica todos los `learning/copy_batches/copy_*.json` y
marca `action="REGENERATED"` en `history.jsonl`).

**Estado real:** los 13 agentes ya generaron el copy completo para las 260
páginas (guardado en la transcripción de esa sesión). Hasta ahora se
guardaron y aplicaron los lotes `copy_00.json` a `copy_03.json` (80 páginas,
ver commits "Regenerar copy de..."). **Faltan los lotes 04-12 (~180 páginas)**
— el contenido ya fue generado por los agentes pero aún no se guardó a disco
ni se aplicó, por el costo de tokens de transcribir manualmente cada bloque
JSON gigante en una sola sesión.

**Cómo continuar (siguiente sesión):**
1. Si la transcripción de los agentes ya no está en contexto, correr de nuevo:
   `python learning/extract_fallback_data.py > learning/fallback_data.json`,
   dividir en lotes de ~20 con `learning/batches/batch_XX.json` (ver el script
   usado en esa sesión), y lanzar agentes Agent tool con el mismo prompt de
   "Rewrite copy batch NN" usado el 2026-07-12.
2. Guardar cada respuesta de agente como `learning/copy_batches/copy_NN.json`.
3. Correr `python learning/apply_copy.py` (es idempotente — re-aplicar copy_00
   a copy_03 no rompe nada, sólo reescribe el mismo contenido).
4. Confirmar con `python learning/find_thin_pages.py` que el % de páginas
   fallback bajó, hacer commit + push de `docs/` y de los nuevos `copy_*.json`.

## Arquitectura

```
learning/
  niche_learner.py       — el "cerebro": lee/escribe history.jsonl,
                            calcula stats por categoría, rankea y filtra
                            leads.csv antes de procesarlos.
  history.jsonl           — log persistente, NUNCA se trunca (a diferencia
                            de swarm_memory.json). Una línea JSON por
                            página deployada o lead descartado.
  bootstrap_history.py    — se corrió UNA VEZ (2026-07-12) para poblar
                            history.jsonl con las 282 páginas que ya
                            existían antes de este sistema. No lo vuelvas
                            a correr (aborta si history.jsonl ya existe).
  find_thin_pages.py      — detecta páginas fallback vía el marcador de
                            texto; --write-queue escribe
                            regeneration_queue.json.
  regeneration_queue.json — (se genera con find_thin_pages.py --write-queue,
                            no versionado hasta que se cree)
```

### Cómo aprende (`NicheLearner.rank_and_filter_leads`)

Antes de que `orchestrator.py`/`main.py` procesen `leads.csv`, se llama:

```python
learner = NicheLearner()
df = learner.rank_and_filter_leads(df)
```

Esto hace 3 cosas sobre el DataFrame de leads, en orden:

1. **Descarta duplicados semánticos**: tokeniza cada keyword candidato y
   lo compara (Jaccard sobre tokens, sin stopwords) contra TODOS los
   keywords ya deployados históricamente. Si la similitud ≥ 0.6
   (`DUP_SIMILARITY_THRESHOLD`), se descarta — evita generar variantes
   casi idénticas del mismo nicho.
2. **Limita por categoría**: máximo `MAX_PER_CATEGORY_PER_RUN` (3) leads
   nuevos de la misma `amazon_cat` por corrida, para forzar diversidad.
3. **Rankea por score compuesto**: `comisión × momentum_tendencia`, con
   un bonus/penalización por categoría según su `fallback_rate`
   histórico (categorías que generaron mucho contenido fallback bajan de
   prioridad — señal indirecta de "esta categoría necesita mejor
   contenido antes de seguir creciendo, no más volumen").

### Cómo se alimenta (`NicheLearner.log`)

Cada vez que `orchestrator.py::_seo_and_design` despliega una página
(Amazon o eBay), llama:

```python
learner.log(keyword=..., amazon_cat=..., market=..., source="amazon"|"ebay",
            action="DEPLOYED", fallback=True|False, score=..., slug=...)
```

El flag `fallback` viene de `designer_agent.py::act()`, que ahora
retorna `payload["fallback"]` = `True` si `_generate_with_claude()`
devolvió `None` (falló Claude) y se usó `_fallback_html()`.

## Cómo continuar este trabajo

1. **Cuando vuelva el crédito de Anthropic**: correr
   `python learning/find_thin_pages.py --write-queue`, y escribir un
   script `learning/regenerate_thin_pages.py` que itere
   `regeneration_queue.json`, vuelva a llamar `DesignerAgent.act()` con
   los mismos datos de producto/trend (se pueden recuperar de
   `leads.csv` + `swarm_memory.json` si el keyword sigue ahí) y
   sobreescriba el HTML. Ese script todavía NO existe — es el siguiente
   paso lógico.
2. **AliExpress**: no tiene integración de afiliados aún (solo se usa
   como referencia de fechas estacionales en `macro_radar.py`). Si se
   agrega, seguir el mismo patrón que `ebay_checker.py` + registrar
   `source="aliexpress"` en el learner para que también aprenda sobre
   esa fuente.
3. **Ajustar umbrales**: si con el tiempo el learner rechaza demasiados
   leads buenos (Jaccard 0.6 muy agresivo) o muy pocos (permite
   duplicados), ajustar `DUP_SIMILARITY_THRESHOLD` y
   `MAX_PER_CATEGORY_PER_RUN` en `niche_learner.py`.
4. **No perder `history.jsonl`**: es el único lugar con la historia
   completa (a diferencia de `swarm_memory.json`, que rota). Al mover de
   máquina o reiniciar el proyecto, cópialo junto con el repo.

## Estado del negocio al momento de crear esto (contexto para el agente)

- **Amazon Associates**: cuenta confirmada, tag `trendvortex00-20`
  funcionando, info fiscal enviada.
- **eBay Partner Network**: `EBAY_SID` corregido a `5339156969`
  (Campaign ID real). El código de scraping RSS de eBay está **bloqueado
  por eBay (HTTP 403)** — sin `EBAY_APP_ID` (developer.ebay.com,
  pendiente de aprobación de cuenta ~1 día hábil) no va a generar
  páginas reales todavía, aunque el pipeline ya está listo para
  generarlas en paralelo con Amazon (no solo como fallback).
- **AliExpress**: sin cuenta de afiliado, sin integración de código.
- **Anthropic (Claude)**: sin crédito — está generando fallback la
  mayoría de páginas nuevas hasta que se recargue.
- **Gemini**: también topó cuota gratis (429) el 2026-07-12.
- **Rainforest API**: decisión del usuario de NO pagar (~$80/mes) —
  se queda en fallback de scraping directo de Amazon, funciona pero
  menos fiable.
- **Google Search Console**: 11/282 páginas indexadas al 2026-07-12,
  causa principal identificada = 92% contenido fallback (ver arriba).

## Pendientes de afiliación (2026-07-12)

- **eBay**: `EBAY_SID` corregido (`5339156969`), pero falta `EBAY_APP_ID` de
  developer.ebay.com — cuenta en revisión (~1 día hábil, pendiente desde
  hoy). Sin ese App ID, el scraping RSS de eBay está bloqueado (HTTP 403)
  y no genera páginas reales todavía.
- **AliExpress**: cuenta de Affiliate Portal creada, pero la solicitud de
  API (rol "Affiliates individual", Colombia) **volvió a estado "En
  revisión"** — Sergio ya la mandó una vez y AliExpress tarda en aprobar.
  Faltan `ALIEXPRESS_APP_KEY` y `ALIEXPRESS_APP_SECRET` en `.env` (hoy
  vacíos) una vez se apruebe. `ALIEXPRESS_TRACKING_ID=sergiocomercial` ya
  está listo. No existe `aliexpress_checker.py` todavía — hay que
  escribirlo (mismo patrón que `ebay_checker.py`) una vez lleguen las
  credenciales.

**Regla acordada con Sergio:** no avanzar a monetización con suscripciones
u otras integraciones nuevas hasta que eBay y AliExpress también estén
generando páginas de la misma calidad que Amazon (contenido no-fallback).
El criterio de "avance" es poder ver páginas de eBay/AliExpress en
`docs/` con la misma calidad de copy que las de Amazon ya regeneradas.

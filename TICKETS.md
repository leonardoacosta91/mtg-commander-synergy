# TICKETS.md — Backlog MTG Commander Synergy

Backlog del proyecto desglosado por tareas, con responsable asignado según seniority y orden de ejecución sugerido.

> **Uso:** tomá el siguiente ticket `[ ]` pendiente de la fase activa, asignalo en `TICKETS.md`, implementalo siguiendo `AGENTS.md` y marcá `[x]` al completarlo. Actualizá `README.md` y `CHANGELOG.md` en el commit de cierre de cada entrega.

## Leyenda

- **Responsable por seniority:** 🟢 Antony (Trainee) · 🟡 Mathias (Junior) · 🔴 Leonardo (Senior).
- **Dificultad (D):** 1 (simple) → 5 (complejo). Estimación en horas de foco.
- **Depende de:** tickets que deben estar completos antes de arrancar.

## Fase 0 — Fundaciones (setup)

> Orden sugerido: **T-001 → T-002, T-003** (T-002 y T-003 son paralelos).

### T-001 · Setup del entorno — 🟢 Antony · D1 · ~1h

- Crear/verificar el virtualenv, instalar `requirements.txt` y confirmar que la estructura de carpetas de `mtg_commander/` está lista.
- Criterios de aceptación: `pip install -r requirements.txt` funciona; `python -c "import requests"` no falla; estructura de paquetes definida.
- Depende de: — (primer ticket).

### T-002 · Migrar `tarea1.py` → `mtg_commander/ingestion/local.py` — 🟢 Antony · D2 · ~3h

- Llevar `leer_decklist()` al módulo del pipeline con los estándares del proyecto: type hints estrictos, docstrings y manejo de secciones (`Commander`, `Deck`, `Sideboard`, `Maybeboard`).
- Criterios de aceptación: la función recibe un `.txt` y devuelve una `list[str]` de nombres normalizados; `Main.py` sigue funcionando importando desde el módulo nuevo.
- Depende de: T-001.

### T-003 · Migrar `tarea2.py` → `mtg_commander/serialization/naming.py` — 🟡 Mathias · D2 · ~3h

- Llevar `generar_nombre_csv()` al módulo del pipeline con timestamp completo (`evaluation_YYYYmmdd_HHMMSS.csv`) y salida en una carpeta `outputs/`.
- Criterios de aceptación: dos llamadas consecutivas generan nombres distintos (idempotencia); el archivo se crea dentro de `outputs/`.
- Depende de: T-001.

## Fase 1 — Deck Context (generación de `estrategia.md`)

> Flujo propio, aparte del pipeline principal. Orden sugerido: **T-101 → T-102 → T-104 → T-105**, con T-103 en paralelo.

### T-101 · Cliente base de Scryfall — 🟡 Mathias · D3 · ~5h

- Módulo `mtg_commander/extraction/client.py`: wrapper de `requests` con headers `User-Agent`/`Accept` obligatorios, timeouts, manejo explícito del **HTTP 429** (backoff/retry) y rate limiting configurable (500ms para `/cards/search`, `/cards/collection`; 100ms para el resto).
- Criterios de aceptación: una query de prueba a `/sets` devuelve datos; un 429 simulado no crashea la app.
- Depende de: T-001.

### T-102 · Info individual de las cartas del deck vía `/cards/collection` — 🟡 Mathias · D3 · ~5h

- Resolver cada carta del decklist normalizado en batches contra `/cards/collection` y normalizar el payload (`oracle_text`, `mana_cost`, `type_line`, `colors`, `color_identity`, `rarity`).
- Criterios de aceptación: para `data/yshtola_esper.txt` se obtiene el JSON normalizado de todas las cartas con sus campos mínimos.
- Depende de: T-101.

### T-103 · Detección de comandante y color identity — 🟢 Antony · D2 · ~4h

- A partir del decklist normalizado, detectar la sección `Commander` y calcular la **identidad de color** del mazo (reglas Commander: las cartas del deck deben caber en la identidad del comandante).
- Criterios de aceptación: para Y'shtola se devuelve el comandante y `color_identity = ["W","U","B"]`.
- Depende de: T-002.

### T-104 · Research web del deck (win conditions, sinergias) — 🟡 Mathias · D4 · ~8h

- Módulo que busque en Reddit/Google información sobre el comandante y arquetipo: win conditions, sinergias, valoración de la comunidad. Evaluar API de Reddit (PRAW) vs búsqueda web genérica.
- Output intermedio: `research.md`.
- Criterios de aceptación: se genera `research.md` con fuentes y resumen para el comandante del decklist de ejemplo.
- Depende de: T-102.

### T-105 · LLM Pass 1 → `estrategia.md` — 🔴 Leonardo · D4 · ~6h

- Síntesis con LLM: decklist enriquecido (T-102) + research (T-104) → perfil estratégico (arquetipo, win conditions, sinergias, curve). Definir prompt y contrato del archivo de salida.
- Criterios de aceptación: se genera `estrategia.md` legible y reutilizable como system context de la Etapa 4. **No se versiona** (`.gitignore`).
- Depende de: T-102, T-104.

### T-106 · Orquestador CLI del flujo Context — 🔴 Leonardo · D3 · ~4h

- Subcomando/script que orqueste 2a→2b→2c con `argparse`. Si el mazo no cambió, no regenerar `estrategia.md`.
- Criterios de aceptación: `python -m mtg_commander.context --deck data/yshtola_esper.txt` produce `estrategia.md`.
- Depende de: T-105.

## Fase 2 — Data Extraction (pipeline principal)

> Orden sugerido: **T-201 → T-202 → T-203**.

### T-201 · Detección del último set — 🟡 Mathias · D2 · ~3h

- `GET /sets`, filtrar por `set_type` (`expansion`/`core`) y elegir el de `released_at` más reciente. Soporte de override `--set {code}`.
- Criterios de aceptación: la función devuelve el código y nombre del set más nuevo; con override devuelve el set pedido.
- Depende de: T-101.

### T-202 · Extracción de cartas del set — 🟡 Mathias · D4 · ~8h

- Queries `set:{code} id<={color_identity} -type:land` con paginación (`next_page`), cache local ≥24h y rate limits estrictos.
- Criterios de aceptación: se obtienen todas las cartas del set filtradas por identidad, sin perder páginas.
- Depende de: T-201.

### T-203 · Filtro por color identity del comandante — 🔴 Leonardo · D3 · ~4h

- Aplicar identidad de color del comandante (T-103) sobre el payload del set: descartar cartas que no quepan en la identidad (regla Commander).
- Criterios de aceptación: para un comandante Esper solo quedan cartas compatibles con W/U/B.
- Depende de: T-202, T-103.

## Fase 3 — Evaluación + CSV

> Orden sugerido: **T-301 → T-302 → T-303**.

### T-301 · LLM Pass 2 — Synergy Evaluation — 🔴 Leonardo · D4 · ~6h

- **Prompt chaining**: iterar sobre el payload filtrado inyectando `oracle_text` + metadatos junto a `estrategia.md`. Forzar **output estructurado JSON**: `card_name`, `include`, `synergy_score`, `rationale`.
- Criterios de aceptación: el output es JSON parseable y determinista para la Etapa 5.
- Depende de: T-203, T-105.

### T-302 · Serialización CSV — 🟡 Mathias · D2 · ~3h

- Parsear el JSON del LLM y exportar `evaluation_YYYYmmdd_HHMMSS.csv` (reutiliza T-003). Manejo de errores de parseo (registrar filas inválidas).
- Criterios de aceptación: el CSV contiene una fila por carta evaluada con los 4 campos; nunca sobrescribe corridas previas.
- Depende de: T-003, T-301.

### T-303 · Orquestador del pipeline completo — 🔴 Leonardo · D4 · ~5h

- Refactor de `Main.py` a CLI real con `argparse`: `--deck`, `--set` (opcional), modo contexto vs pipeline completo.
- Criterios de aceptación: `python Main.py --deck data/yshtola_esper.txt` corre el pipeline completo y genera el CSV.
- Depende de: T-202, T-301, T-302.

## Fase 4 — Roadmap / V2

### T-401 · Ingestion remota Moxfield/Archidekt — 🔴 Leonardo · D5 · ~10h

- V2 de Etapa 1: consumir `https://api.moxfield.com/v2/decks/all/{deck_id}` y `https://archidekt.com/api/decks/{deck_id}/`, respetando el **mismo contrato** que la V1 local.
- Depende de: T-002.

### T-402 · Caching con bulk data files — 🟡 Mathias · D3 · ~5h

- Cache en disco LRU + evaluación de los **bulk data files** diarios de Scryfall para consultas en volumen.
- Depende de: T-202.

### T-403 · Tests y release — 👥 Equipo · D2 · ~4h

- Pruebas unitarias/integración de los módulos clave + actualización de `README.md`/`CHANGELOG.md` por release.
- Depende de: todas las anteriores.

## Resumen por persona

| Persona | Tickets | Foco |
|---------|---------|------|
| 🟢 Antony (Trainee) | T-001, T-002, T-103 | Setup, migración de prototipos, lógica simple de decklist |
| 🟡 Mathias (Junior) | T-003, T-101, T-102, T-104, T-201, T-202, T-302, T-402 | Cliente HTTP, rate limits, research, extracción y serialización |
| 🔴 Leonardo (Senior) | T-105, T-106, T-203, T-301, T-303, T-401 | Arquitectura, LLM Pass 1 y 2, filtro Commander, orquestación, V2 remoto |

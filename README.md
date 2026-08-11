# MTG Commander Synergy Agent

Herramienta CLI en Python que evalúa qué cartas de los nuevos sets de *Magic: The Gathering* optimizan mazos de Commander. El sistema infiere el perfil estratégico del mazo con un LLM y evalúa cartas nuevas vía la API de Scryfall, emitiendo una recomendación de inclusión con justificación técnica en CSV.

> ⚠️ Proyecto en desarrollo: Etapa 1 (ingesta local `.txt` + detección de comandante/color identity) implementada. El resto de los módulos se implementa por etapas según `TICKETS.md`.

## Pipeline

```
decklist (.txt o URL/ID)
      │  [1] Data Ingestion ─ normalización + comandante(s)
      ▼
      │  [2] Context Generation ─ LLM Pass 1 → estrategia.md
      │      └─ sub-flujo: 2a Scryfall (info individual) → 2b research web → 2c síntesis LLM
      ▼
      │  [3] Data Extraction ─ detectar último set → queries Scryfall (paginación + rate-limit)
      ▼
      │  [4] Synergy Evaluation ─ LLM Pass 2 (prompt chaining) → JSON
      ▼
      │  [5] Data Serialization ─ export CSV con timestamp
```

| Etapa | Módulo (planificado) | Estado |
|-------|----------------------|--------|
| 1. Data Ingestion (V1 local .txt) | `mtg_commander/ingestion/local.py` + `commander.py` | ✅ Implementada (T-002, T-103) |
| 1. Data Ingestion (V2 Moxfield/Archidekt) | `mtg_commander/ingestion/remote.py` | 🚧 Roadmap |
| 2. Context Generation (LLM Pass 1) | `mtg_commander/context/card_info.py` (2a) + `generator.py` (2c) | 🚧 Parcial (T-102: enriquecimiento 2a) |
| 3. Data Extraction (Scryfall) | `client.py` + `latest_set.py` + `set_cards.py` | 🚧 Parcial (T-101, T-201, T-202: falta T-203) |
| 4. Synergy Evaluation (LLM Pass 2) | `mtg_commander/evaluation/engine.py` | 🚧 Ticket abierto |
| 5. Data Serialization (CSV) | `mtg_commander/serialization/naming.py` | 🚧 Parcial (T-003: nombres únicos, falta T-302: export) |

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt` (`requests`)

## Estructura del proyecto

```
.
├── AGENTS.md                       # System prompt / contexto maestro
├── README.md
├── CHANGELOG.md                    # Traza de releases
├── TICKETS.md                      # Backlog desglosado por seniority
├── requirements.txt
├── Main.py                         # Orquestador CLI (a refactorizar)
├── mtg_commander/                  # Paquete principal del pipeline
│   ├── ingestion/                  #   Etapa 1: local.py + commander.py
│   ├── context/                    #   Etapa 2: generación de estrategia.md
│   ├── extraction/                 #   Etapa 3: queries Scryfall
│   ├── evaluation/                 #   Etapa 4: synergy evaluation
│   └── serialization/              #   Etapa 5: naming.py
└── data/                           # Decklists de ejemplo
    └── yshtola_esper.txt
```

## Decklist de ejemplo

Export de Moxfield/Archidekt con secciones `Commander`, `Deck`, `Sideboard` y `Maybeboard`:

```
Commander
1 Y'shtola, Night's Blessed

Deck
1 Arcane Signet
1 Brainstorm
...

Sideboard
1 Pithing Needle
```

## Equipo

- **Leonardo** (Senior)
- **Antony** (Trainee)
- **Mathias** (Junior)

Ver `AGENTS.md` para el pipeline completo, las reglas de código (Type Hints, docstrings) y el modo asistente dinámico. El backlog de trabajo está en `TICKETS.md`.

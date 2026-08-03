# MTG Commander Synergy Agent

Herramienta CLI en Python que evalúa qué cartas de los nuevos sets de *Magic: The Gathering* optimizan mazos de Commander. El sistema infiere el perfil estratégico del mazo con un LLM y evalúa cartas nuevas vía la API de Scryfall, emitiendo una recomendación de inclusión con justificación técnica en CSV.

> ⚠️ Proyecto en estado inicial: solo la definición del pipeline (AGENTS.md) y un decklist de ejemplo. Los módulos se implementan por etapas.

## Pipeline

```
decklist (.txt o URL/ID)
      │  [1] Data Ingestion ─ normalización + comandante(s)
      ▼
      │  [2] Context Generation ─ LLM Pass 1 → estrategia.md
      ▼
      │  [3] Data Extraction ─ queries Scryfall (paginación + rate-limit)
      ▼
      │  [4] Synergy Evaluation ─ LLM Pass 2 (prompt chaining) → JSON
      ▼
      │  [5] Data Serialization ─ export CSV con timestamp
```

| Etapa | Módulo (planificado) | Estado |
|-------|----------------------|--------|
| 1. Data Ingestion (V1 local .txt) | `mtg_commander/ingestion/local.py` | 🚧 Pendiente |
| 1. Data Ingestion (V2 Moxfield/Archidekt) | `mtg_commander/ingestion/remote.py` | 🚧 Roadmap |
| 2. Context Generation (LLM Pass 1) | `mtg_commander/context/generator.py` | 🚧 Ticket abierto |
| 3. Data Extraction (Scryfall) | `mtg_commander/extraction/scryfall.py` | 🚧 Pendiente |
| 4. Synergy Evaluation (LLM Pass 2) | `mtg_commander/evaluation/engine.py` | 🚧 Ticket abierto |
| 5. Data Serialization (CSV) | `mtg_commander/serialization/exporter.py` | 🚧 Pendiente |

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt` (`requests`)

## Estructura del proyecto

```
.
├── AGENTS.md                       # System prompt / contexto maestro
├── README.md
├── requirements.txt
└── data/                           # Decklists de ejemplo
    └── yshtola_esper.txt
```

## Decklist de ejemplo

Export de Moxfield/Archidekt con secciones `Commander`, `Deck`, `Sideboard` y `Maybeboard`:

```
Commander
1 Y'shtola, Night's Herald

Deck
1 Arcane Signet
1 Brainstorm
...

Sideboard
1 Pithing Needle
```

## Equipo

- **Leonardo**
- **Antony**
- **Mathias**

Ver `AGENTS.md` para el pipeline completo, las reglas de código (Type Hints, docstrings) y el modo asistente dinámico.

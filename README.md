# MTG Commander Synergy Agent

Herramienta CLI en Python que evalúa qué cartas de los nuevos sets de *Magic: The Gathering* optimizan mazos de Commander. El sistema infiere el perfil estratégico del mazo con un LLM y evalúa cartas nuevas vía la API de Scryfall, emitiendo una recomendación de inclusión con justificación técnica en CSV.

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

| Etapa | Módulo | Estado |
|-------|--------|--------|
| 1. Data Ingestion (V1 local .txt) | `mtg_commander/ingestion/local.py` | ✅ Implementado |
| 1. Data Ingestion (V2 Moxfield/Archidekt) | `mtg_commander/ingestion/remote.py` | 🚧 Roadmap |
| 2. Context Generation (LLM Pass 1) | `mtg_commander/context/generator.py` | 🚧 Ticket abierto |
| 3. Data Extraction (Scryfall) | `mtg_commander/extraction/scryfall.py` | ✅ Implementado |
| 4. Synergy Evaluation (LLM Pass 2) | `mtg_commander/evaluation/engine.py` | 🚧 Ticket abierto |
| 5. Data Serialization (CSV) | `mtg_commander/serialization/exporter.py` | ✅ Implementado |

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt` (`requests`)

## Uso

```bash
# Pipeline completo
python main.py --deck data/yshtola_esper.txt --set DFT

# Solo ingestión + extracción (sin llamadas LLM)
python main.py --deck data/yshtola_esper.txt --set DFT --dry-run

# Elegir set y directorio de salida
python main.py --deck data/yshtola_esper.txt --set TDM --out reports/
```

También disponible como `python -m mtg_commander`.

### Argumentos

| Argumento | Descripción |
|-----------|-------------|
| `--deck` | Decklist local `.txt` (V1) o URL/ID de mazo (V2). Requerido. |
| `--set` | Código de set a evaluar (default: `DFT`, configurable con `MTG_SET_CODE`). |
| `--out` | Directorio de reportes (default: directorio actual). |
| `--dry-run` | Ejecuta ingestión + extracción y omite las etapas LLM. |

## Formato de decklist (V1)

Export de Moxfield/Archidekt. El parser detecta secciones `Commander`, `Deck`, `Sideboard` y `Maybeboard` (las dos últimas se descartan), y limpia quantifiers (`1x`), espacios y líneas de metadatos.

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

## Estructura del proyecto

```
.
├── main.py                       # Entry point CLI
├── mtg_commander/
│   ├── cli.py                    # argparse y orquestación del pipeline
│   ├── config.py                 # Constantes (Scryfall, rate-limit, set default)
│   ├── models.py                 # Contratos: Card, Decklist, ScryfallCard, EvaluationResult
│   ├── ingestion/                # [1] V1 local / V2 remoto (roadmap)
│   ├── context/                  # [2] LLM Pass 1 → estrategia.md
│   ├── extraction/               # [3] Scryfall REST
│   ├── evaluation/               # [4] LLM Pass 2 (prompt chaining)
│   └── serialization/            # [5] Export CSV
├── data/                         # Decklists de ejemplo
├── requirements.txt
├── agent.md                      # System prompt / contexto maestro
└── README.md
```

## Equipo

- **Leonardo** 
- **Antony**
- **Mathias**

Ver `agent.md` para las reglas de código (Type Hints, docstrings) y el modo asistente dinámico.

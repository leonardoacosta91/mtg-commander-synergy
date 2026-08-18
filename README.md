# MTG Commander Synergy Agent

Herramienta CLI en Python que evalúa qué cartas de los nuevos sets de *Magic: The Gathering* optimizan mazos de Commander. El sistema infiere el perfil estratégico del mazo con un LLM y evalúa cartas nuevas vía la API de Scryfall, emitiendo una recomendación de inclusión con justificación técnica en CSV.

> ⚠️ Proyecto en desarrollo: Etapa 1 (ingesta local `.txt` + detección de comandante/color identity) implementada. El resto de los módulos se implementa por etapas según `TICKETS.md`.

## Pipeline

```
decklist (.txt o URL/ID)
      │  [1] Data Ingestion ─ normalización + comandante(s)
      ▼
      │  [2] Context Generation ─ LLM Pass 1 → estrategia.md
      │      └─ sub-flujo: 2a Scryfall (info individual) → perfil automático → 2b research web → 2c síntesis LLM
      ▼
      │  [3] Data Extraction ─ detectar último set → queries Scryfall (paginación + rate-limit)
      ▼
      │  [4] Synergy Evaluation ─ LLM Pass 2 (prompt chaining) → JSON
      ▼
      │  [5] Data Serialization ─ export CSV con timestamp
```
| Etapa | Módulo | Estado |
|-------|--------|--------|
| 1. Data Ingestion (V1 local .txt) | `mtg_commander/ingestion/local.py` + `commander.py` | ✅ Implementada (T-002, T-103) |
| 1. Data Ingestion (V2 Moxfield/Archidekt) | `mtg_commander/ingestion/remote.py` | 🚧 Roadmap |
| 2. Context Generation (LLM Pass 1) | `card_info.py` (2a) + `deck_profiler.py` + `reddit_research.py` (2b) + `generator.py` (2c) | 🚧 Parcial |
| 3. Data Extraction (Scryfall) | `client.py` + `cache.py` + `latest_set.py` + `set_cards.py` | 🚧 Parcial (T-101, T-201, T-202, T-402: falta T-203) |
| 4. Synergy Evaluation (LLM Pass 2) | `mtg_commander/evaluation/engine.py` | 🚧 Ticket abierto |
| 5. Data Serialization (CSV) | `mtg_commander/serialization/naming.py` + `csv_export.py` | ✅ Implementada (T-003, T-302) |

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt` (`requests`, `praw`, `python-dotenv`, `openai`)
- Un archivo `.env` configurado en la raíz con credenciales de la API de Reddit y del LLM (ver `.env.example`).

## Proveedores de LLM (intercambiables)

El pipeline habla contra una abstracción común (`mtg_commander/llm/`) en vez de contra un SDK puntual. Cambiar de provider es solo configurar `.env`:

```
LLM_PROVIDER=gemini        # gemini | anthropic | openai
GEMINI_API_KEY=...         # key según el provider elegido
# LLM_MODEL=gemini-flash-latest
```

- **Interfaz:** `LLMProvider.chat(system, prompt, ...)` → `LLMResponse(text, provider, model)`.
- **Implementaciones:** `GeminiProvider` (REST oficial), `OpenAIProvider` (SDK oficial) y `AnthropicProvider` (SDK con import perezoso).
- **Selección:** `create_provider()` lee `LLM_PROVIDER` (default `gemini`) y `LLM_MODEL` (default del provider).
- El SDK oficial de OpenAI está incluido; el de Anthropic se agrega solo si se usa.

El Pass 1 se ejecuta con `generar_estrategia(cartas, research_path)`: recibe el
payload normalizado de `obtener_info_cartas()`, combina `research.md` mediante el
provider configurado y genera `estrategia.md`. Ambos Markdown son artefactos locales
ignorados por Git; el orquestador CLI se incorpora en T-106.

Antes del research, `perfilar_deck(cartas)` usa el LLM para inferir arquetipos y
mecánicas desde el payload enriquecido de Scryfall. Ese `DeckProfile` se pasa a
`generar_research(..., profile=perfil)` para sumar queries Reddit específicas del
mazo, además de las tres queries generales del comandante. No requiere cartas ni
tags ingresados manualmente por el usuario.

`calcular_deck_stats(cartas)` produce el resumen determinista de curva, tipos,
colores, keywords y fuentes de mana. El generador final recibe explícitamente
cartas saneadas + `DeckStats` + `DeckProfile` + `research.md`; las `image_uris`
quedan en cache para uso visual pero nunca se envían al LLM.

Las cartas enriquecidas por Scryfall se guardan individualmente en
`outputs/cache/` y no usan TTL: antes de consultar, el sistema revisa la entrada
local por nombre; solo solicita a Scryfall las cartas que aún no estén cacheadas.
Cada JSON conserva texto Oracle, coste, CMC, tipos, colores, keywords, mana que
produce, estadísticas, layout, caras modales y `image_uris` (URLs de Scryfall,
no archivos de imagen).

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
│   ├── llm/                        #   Abstracción de providers LLM (base + factory)
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

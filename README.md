# MTG Commander Synergy Agent

Herramienta CLI en Python que evalúa qué cartas de un set de *Magic: The Gathering* pueden mejorar un mazo de Commander. A partir de un decklist local, el sistema investiga el comandante, sintetiza la estrategia del mazo, obtiene las cartas candidatas desde Scryfall y genera un CSV con decisiones de inclusión y justificaciones técnicas.

> **Estado actual:** el pipeline base funciona de punta a punta con decklists `.txt` locales. La ingesta directa desde URLs de Moxfield/Archidekt continúa en roadmap.

## Inicio rápido

### 1. Preparar Python

Requiere Python 3.10 o superior. Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

En Windows PowerShell, la activación equivalente es:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. Configurar credenciales

Creá el archivo local `.env` a partir del ejemplo:

```bash
cp .env.example .env
```

El flujo completo necesita:

- Credenciales de una aplicación tipo `script` de Reddit para generar `research.md`.
- La API key de un proveedor LLM: Gemini, OpenAI o Anthropic.
- Conexión a Internet para Reddit, el LLM y cualquier dato de Scryfall que todavía no esté cacheado.

Scryfall es público y no requiere API key. Un ejemplo mínimo usando OpenAI es:

```dotenv
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USERNAME=...
REDDIT_PASSWORD=...
REDDIT_USER_AGENT=script:mtg-commander-synergy:v1.0 (by u/tu_usuario)

LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-luna
OPENAI_API_KEY=...
```

No subas `.env`, `research.md`, `estrategia.md`, `outputs/` ni claves al repositorio; ya están contemplados como artefactos locales.

### 3. Agregar el decklist

Guardá el archivo en `data/`. El repositorio incluye
`data/yshtola_esper.txt` como ejemplo versionado. El formato esperado es:

```text
Commander
1 Y'shtola, Night's Blessed

Deck
1 Arcane Signet
1 Counterspell
...

Sideboard
1 Pithing Needle
```

El pipeline procesa `Commander` y `Deck`; ignora `Sideboard` y `Maybeboard`.

### 4. Ejecutar todo el pipeline

Para evaluar automáticamente el último set de tipo expansión o core:

```bash
.venv/bin/python Main.py --deck yshtola_esper.txt
```

Para regenerar también la investigación y la estrategia aunque el deck no haya cambiado:

```bash
.venv/bin/python Main.py --deck yshtola_esper.txt --force-context
```

Al finalizar, el comando informa el comandante, el set evaluado, la cantidad de candidatas y la ruta del CSV generado dentro de `outputs/`.

## Pipeline

```
decklist local (.txt)
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
| 1. Data Ingestion (V1 local .txt) | `mtg_commander/ingestion/local.py` + `commander.py` | ✅ Implementada (T-002, T-103, T-107) |
| 1. Data Ingestion (V2 Moxfield/Archidekt) | `mtg_commander/ingestion/remote.py` | 🚧 Roadmap |
| 2. Context Generation (LLM Pass 1) | `card_info.py` (2a) + `deck_profiler.py` + `reddit_research.py` (2b) + `generator.py` (2c) + `orchestrator.py` | ✅ Implementada (T-102, T-104, T-105, T-106) |
| 3. Data Extraction (Scryfall) | `client.py` + `cache.py` + `latest_set.py` + `set_cards.py` + `color_filter.py` | ✅ Implementada (T-101, T-201, T-202, T-203, T-402) |
| 4. Synergy Evaluation (LLM Pass 2) | `mtg_commander/evaluation/engine.py` | ✅ Implementada (T-301) |
| 5. Data Serialization (CSV) | `mtg_commander/serialization/naming.py` + `csv_export.py` | ✅ Implementada (T-003, T-302) |
| Orquestación CLI completa | `Main.py` + `mtg_commander/pipeline.py` | ✅ Implementada (T-303) |

## Proveedores de LLM (intercambiables)

El pipeline habla contra una abstracción común (`mtg_commander/llm/`) en vez de contra un SDK puntual. Cambiar de provider es solo configurar `.env`:

```dotenv
LLM_PROVIDER=gemini        # gemini | anthropic | openai
GEMINI_API_KEY=...         # key según el provider elegido
# LLM_MODEL=gemini-flash-latest
```

- **Interfaz:** `LLMProvider.chat(system, prompt, ...)` → `LLMResponse(text, provider, model)`.
- **Implementaciones:** `GeminiProvider` (REST oficial), `OpenAIProvider` (SDK oficial) y `AnthropicProvider` (SDK con import perezoso). Con modelos GPT-5 de OpenAI el provider usa `reasoning_effort="low"`; la síntesis de `estrategia.md` reserva hasta 24.000 tokens para razonamiento y salida.
- **Selección:** `create_provider()` lee `LLM_PROVIDER` (default `gemini`) y `LLM_MODEL` (default del provider).
- El SDK oficial de OpenAI está incluido; el de Anthropic se agrega solo si se usa.

Los tres prompts de LLM están redactados en inglés para mantener instrucciones
precisas y consistentes entre providers. Sus contratos conservan la salida de
dominio en español: el perfil preliminar resume en español, `estrategia.md` usa
sus secciones actuales en español y la evaluación devuelve categorías, pros,
contras y justificación en español. Los nombres de campos JSON y los tiers de
recomendación permanecen estables para no afectar la serialización.

El flujo de Context se puede ejecutar por separado desde la raíz del repositorio:

```bash
.venv/bin/python -m mtg_commander.context --deck data/yshtola_esper.txt
```

La primera ejecución normaliza y enriquece el deck, infiere su perfil, genera
`research.md` y finalmente `estrategia.md`. El orquestador guarda el fingerprint
normalizado en `outputs/cache`; si el deck y la estrategia siguen vigentes, una
ejecución posterior reutiliza el resultado. `--force` permite regenerarlo y
`--provider` selecciona `gemini`, `openai` o `anthropic`.

El Pass 1 se ejecuta internamente con `generar_estrategia(cartas, research_path)`: recibe el
payload normalizado de `obtener_info_cartas()`, combina `research.md` mediante el
provider configurado y genera `estrategia.md`. Ambos Markdown son artefactos locales
ignorados por Git.

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

`evaluar_cartas(cartas, strategy_path, provider)` implementa el Pass 2 mediante
una llamada independiente por carta. Cada candidato se compara contra
`estrategia.md`; el motor solicita JSON nativo cuando el provider lo soporta y
valida nombre, decisión, score de 0 a 10, categoría, temas, pros, contras y
justificación antes de entregar los resultados al exportador CSV.

El motor registra el progreso con el módulo estándar `logging`: inicio y fin de
la corrida, posición de cada carta (`n/total`), duración y resumen de decisión
(`include`, tier y score). Para verlo desde una invocación programática:

```python
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
```

## Pipeline completo

Todos los comandos deben ejecutarse desde la raíz del repositorio. Si el decklist
está en `data/`, alcanza con indicar el nombre del archivo:

```bash
.venv/bin/python Main.py --deck yshtola_esper.txt
```

También se acepta una ruta explícita fuera de `data/`:

```bash
.venv/bin/python Main.py --deck /ruta/a/mi_mazo.txt
```

### Opciones habituales

| Objetivo | Comando |
|----------|---------|
| Último set + contexto reutilizable | `.venv/bin/python Main.py --deck yshtola_esper.txt` |
| Último set + contexto regenerado | `.venv/bin/python Main.py --deck yshtola_esper.txt --force-context` |
| Set específico de Scryfall | `.venv/bin/python Main.py --deck yshtola_esper.txt --set fin` |
| Solo investigación y estrategia | `.venv/bin/python Main.py --deck yshtola_esper.txt --context-only --force-context` |
| Elegir proveedor | `.venv/bin/python Main.py --deck yshtola_esper.txt --provider openai` |
| Logs de diagnóstico | `.venv/bin/python Main.py --deck yshtola_esper.txt --verbose` |

Sin `--set`, la detección automática solo considera sets con `set_type`
`expansion` o `core`. Para evaluar un producto suplementario o una bonus sheet,
pasá su código propio de Scryfall mediante `--set CODIGO`.

`--force-context` fuerza nuevas llamadas a Reddit y al LLM para reconstruir
`research.md` y `estrategia.md`; no elimina los datos de Scryfall ya cacheados.

## Resultados generados

Una corrida completa produce o actualiza estos artefactos locales:

| Artefacto | Contenido |
|-----------|-----------|
| `research.md` | Posts y comentarios de Reddit con fuentes trazables. |
| `estrategia.md` | Perfil persistente del mazo: plan, curva, win conditions, paquetes y criterios de inclusión. |
| `outputs/evaluation_<set>_<timestamp>_<id>.csv` | Una fila por candidata con decisión, tier, score, temas, pros, contras y justificación. |
| `outputs/cache/` | Sets, cartas del set, cartas del deck y fingerprint del contexto. |

Cada CSV tiene un nombre único y nunca sobrescribe una evaluación anterior. El
CSV contiene tanto las cartas recomendadas como las rechazadas, para que se
pueda auditar la decisión completa.

## Cómo funciona el caché

- Las cartas enriquecidas del deck se guardan individualmente y se reutilizan
  sin TTL; Scryfall solo recibe los nombres todavía ausentes.
- El listado de sets y las cartas de cada combinación `set + color identity`
  tienen una vigencia de 24 horas.
- `estrategia.md` se reutiliza cuando el fingerprint del deck no cambió.
- `--force-context` regenera research y estrategia, pero conserva el caché de
  Scryfall.

La primera corrida suele ser la más lenta. La evaluación hace una llamada LLM
por carta candidata, por lo que su duración y costo dependen del tamaño del set.

## Problemas frecuentes

### `python: command not found`

Usá el intérprete del entorno virtual directamente:

```bash
.venv/bin/python Main.py --deck yshtola_esper.txt
```

### Faltan variables de Reddit o del LLM

Confirmá que `.env` exista en la raíz y que no conserve valores de ejemplo como
`your_client_id_here`. Para OpenAI, por ejemplo, se requieren
`LLM_PROVIDER=openai` y `OPENAI_API_KEY`.

### El deck no se encuentra

Usá solamente el nombre si está dentro de `data/`, o pasá una ruta completa. La
ingesta directa desde URLs o IDs de Moxfield/Archidekt todavía no está
implementada.

### No aparecen cartas de una bonus sheet

Las bonus sheets suelen tener un código de set distinto. Ejecutá el pipeline con
ese código explícito mediante `--set`; no se incluyen automáticamente al evaluar
el set principal.

### Advertencia de PRAW desactualizado

Una advertencia de versión no implica por sí sola que el research haya fallado.
El proceso solo se considera completo cuando informa la ruta del CSV final y
termina con código de salida `0`.

## Estructura del proyecto

```
.
├── AGENTS.md                       # System prompt / contexto maestro
├── README.md
├── CHANGELOG.md                    # Traza de releases
├── TICKETS.md                      # Backlog desglosado por seniority
├── requirements.txt
├── Main.py                         # CLI del pipeline completo
├── app.py                          # Frontend Streamlit de consulta de cartas
├── mtg_commander/                  # Paquete principal del pipeline
│   ├── ingestion/                  #   Etapa 1: local.py + commander.py
│   ├── context/                    #   Etapa 2: generación de estrategia.md
│   ├── llm/                        #   Abstracción de providers LLM (base + factory)
│   ├── pipeline.py                  #   Orquestación de las cinco etapas
│   ├── extraction/                 #   Etapa 3: queries Scryfall
│   ├── evaluation/                 #   Etapa 4: engine.py (synergy evaluation)
│   └── serialization/              #   Etapa 5: naming.py
├── tests/                          # Suite separada, con estructura espejo
│   ├── context/
│   ├── extraction/
│   ├── ingestion/
│   ├── llm/
│   └── serialization/
└── data/                           # Decklists de ejemplo
    └── yshtola_esper.txt
```

## Pruebas

La suite vive fuera del paquete productivo y replica su estructura por módulo.
Se ejecuta completa con:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

## App web de consulta de cartas

Mini frontend Streamlit (T-108) para mirar la ficha de cualquier carta: imagen,
costo de maná y texto con los símbolos renderizados, tipo, poder/resistencia,
identidad de color en orden WUBRG y alternancia entre caras para cartas de
doble cara (MDFC/transform/split). Las búsquedas son por nombre exacto y se
cachean 24h; una carta inexistente muestra un aviso sin crashear.

```bash
streamlit run app.py
```

Todo el HTTP pasa por el `ScryfallClient` centralizado (headers obligatorios,
rate limiting y retry ante HTTP 429); la app no hace pedidos directos con
`requests`.

## Equipo

- **Leonardo** (Senior)
- **Antony** (Trainee)
- **Mathias** (Junior)

Ver `AGENTS.md` para el pipeline completo, las reglas de código (Type Hints, docstrings) y el modo asistente dinámico. El backlog de trabajo está en `TICKETS.md`.

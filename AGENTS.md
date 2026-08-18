# MTG Commander Synergy Agent

System Prompt / Contexto Maestro para el Agente de Código.

## Objetivo del Proyecto

Herramienta CLI en Python que evalúa qué cartas de los nuevos sets de *Magic: The Gathering* optimizan mazos de Commander. El sistema consume un decklist, infiere el perfil estratégico del mazo mediante un LLM y evalúa cartas nuevas vía la API de Scryfall para emitir una recomendación de inclusión con justificación técnica.

El resultado final es un pipeline automatizado basado en llamadas REST y procesamiento de lenguaje natural (NLP), ejecutable desde terminal.

## Arquitectura Técnica

Pipeline de 5 etapas, cada una aislada en módulos independientes:

```
decklist (txt/URL)
      │
      ▼
┌───────────────────────────┐
│ 1. Data Ingestion         │  → decklist normalizado
│    (normalización)        │
└───────────────────────────┘
      │
      ▼
┌───────────────────────────┐
│ 2. Context Generation     │  → estrategia.md (context persistente)
│    (LLM Pass 1)           │
└───────────────────────────┘
      │
      ▼
┌───────────────────────────┐
│ 3. Data Extraction        │  → payload de cartas nuevas (Scryfall)
│    (REST API)             │
└───────────────────────────┘
      │
      ▼
┌───────────────────────────┐
│ 4. Synergy Evaluation     │  → output estructurado (JSON)
│    (LLM Pass 2)           │
└───────────────────────────┘
      │
      ▼
┌───────────────────────────┐
│ 5. Data Serialization     │  → reporte .csv con timestamp
└───────────────────────────┘
```

### Etapa 1: Data Ingestion (Evolutiva / Modular)

Diseño pensado para evolucionar sin romper el resto del pipeline. Ambas versiones deben devolver el **mismo contrato de datos** (decklist normalizado), de modo que las etapas posteriores no dependan de la fuente de origen.

- **V1 (Fase Inicial):** Lectura de un archivo `.txt` local con el decklist. Incluye normalización:
  - Limpieza de *quantifiers* de cantidad (ej. `1 `, `2 ` al inicio de línea).
  - Eliminación de saltos de línea residuales y espacios sobrantes.
  - Eliminación de metadatos no relacionados (headers, secciones de "Sideboard", "Maybeboard", etc.).
- **V2 (Versión Final / Roadmap):** Extracción programática del decklist consumiendo APIs públicas:
  - Moxfield: `https://api.moxfield.com/v2/decks/all/{deck_id}`
  - Archidekt: `https://archidekt.com/api/decks/{deck_id}/`
  - Se acepta URL o ID del mazo como entrada, extrayendo dinámicamente:
    - La lista de las 99 cartas.
    - La/s carta/s Comandante (campo `commanders` en ambas APIs).

### Etapa 2: Context Generation (LLM Pass 1)

**Tiene su propio flujo aparte del pipeline principal** (se ejecuta una vez por mazo para producir `estrategia.md`). Este flujo consume el decklist normalizado de la Etapa 1 y lo enriquece antes de sintetizar el perfil estratégico:

```
decklist normalizado
      │
      ▼
┌────────────────────────────┐
│ 2a. Enriquecimiento Scryfall│  → /cards/collection
│     (info individual)       │     oracle_text, mana_cost,
└────────────────────────────┘     type_line, color_identity
      │
      ▼
┌────────────────────────────┐
│ 2b. Research web            │  → Reddit (PRAW)
│     (win conditions,       │     research.md (intermedio)
│      sinergias, metagame)   │
└────────────────────────────┘
      │
      ▼
┌────────────────────────────┐
│ 2c. Síntesis con LLM        │  → estrategia.md
│     (Pass 1)                │
└────────────────────────────┘
```

1. **2a — Enriquecimiento con Scryfall:** cada carta del decklist se resuelve contra `/cards/collection` (batch) para obtener `oracle_text`, `mana_cost`, `type_line`, `colors`, `color_identity`, etc. Permite que el LLM y las etapas posteriores trabajen con el texto real de las cartas.
2. **2b — Research web:** `reddit_research.py` consulta Reddit mediante PRAW en `r/EDH` y `r/CompetitiveEDH` para reunir win conditions, sinergias y valoración de la comunidad. La decisión actual es usar la API oficial para obtener posts, comentarios y URLs trazables; una fuente web adicional requerirá un ticket propio. Output intermedio: `research.md`, que debe respetar el contrato de `mtg_commander/context/research_template.md` (fuentes trazables `[F#]`, toda carta entre corchetes `[Carta]`, y foco en el *para qué* se usa cada carta/paquete — no en la carta aislada).
3. **2c — Síntesis con LLM (Pass 1):** se envía el decklist enriquecido (paso 2a) junto con el research (2b) al LLM para inferir el perfil estratégico detallado.

El resultado `estrategia.md` incluye:

- Arquetipo(s) (ej. *Control/Drenaje en Esper para Y'shtola*, *Evasión/Combat Triggers en Bant para Tidus*).
- Win conditions del mazo.
- Sinergias clave y paquetes de cartas.
- En lo posible: colores, identidad de color y presupuesto aproximado de mana (curve).

**`estrategia.md` es el system context persistente**: se genera una vez por mazo y se reutiliza en cada ejecución de la Etapa 4. `python -m mtg_commander.context --deck <decklist>` ejecuta el flujo 2a→2b→2c y guarda un fingerprint del deck normalizado en `outputs/cache`; si no cambió, reutiliza la estrategia. **No se versiona ni se comparte** (ver `.gitignore` y secretos): es personal de cada integrante.

### Etapa 3: Data Extraction (Scryfall API)

Queries a la API REST de Scryfall usando sintaxis avanzada.

**Detección del último set (paso previo a la extracción):**
- Endpoint `GET /sets` → filtrar por `set_type` (`expansion`/`core`) y elegir el de `released_at` más reciente.
- Alternativa directa: `GET /sets/{code}` si el set se conoce de antemano.
- El set detectado se pasa como parámetro a las queries de cartas de esta etapa.

**Requisitos técnicos obligatorios (definidos por Scryfall):**
- La API es pública y gratuita: **no requiere cuenta, registro, API key ni tokens**. La cuenta de la web solo sirve para decks/features del sitio, no para la API.
- Endpoint base: `https://api.scryfall.com`. Solo HTTPS (TLS 1.2+), codificación UTF-8.
- **Toda petición debe incluir headers `User-Agent` y `Accept`**, de lo contrario la API rechaza la petición:
  - `User-Agent`: nombre real de la aplicación (ej. `MTGCommanderSynergy/1.0`). No dejar que la librería HTTP lo elija por defecto.
  - `Accept`: genérico, ej. `*/*` o `application/json;q=0.9,*/*;q=0.8`.

**Rate limits (hard limits de la API):**
- `/cards/search`, `/cards/named`, `/cards/random`, `/cards/collection`: **máximo 2 peticiones/segundo** → delay mínimo de **500ms entre peticiones**.
- Todos los demás métodos: máximo 10 peticiones/segundo (100ms).
- Un **HTTP 429 Too Many Requests** bloquea la aplicación durante 30 segundos. Ignorar o seguir abusando puede resultar en **ban temporal o permanente**. El código debe tratar el 429 explícitamente (backoff/retry o abortar).
- Verificar siempre que los delays implementados respeten el límite del endpoint usado (los 50–100ms NO alcanzan para `/cards/search`).

**Recomendación de Scryfall (caching):**
- Cachear los datos descargados localmente al menos **24 horas**; los precios solo se actualizan una vez por día y los datos de gameplay (oracle_text, mana_cost, etc.) con mucha menos frecuencia.
- Para mirar muchos nombres/precios o resolver imágenes en volumen, usar los **bulk data files** diarios (`/docs/api/bulk-data`) en vez de llamadas puntuales.

**Queries y payload:**
- Ejemplo de query: `set:{code} id<={color_identity} -type:land`
- Manejo obligatorio de paginación JSON: seguir `has_more` y solicitar las páginas consecutivas; si el cliente adopta `next_page`, debe delegar esa URL al `ScryfallClient`.
- Normalización del payload: extraer `oracle_text`, `name`, `type_line`, `mana_cost`, `set`, `rarity`, `colors`, `keywords`, etc.

### Etapa 4: Synergy Evaluation Engine (LLM Pass 2)

Implementación de **Prompt Chaining**:

1. Se itera sobre el payload de Scryfall.
2. Se inyecta el `oracle_text` y metadatos de cada carta junto con el contenido de `estrategia.md`.
3. Se fuerza al modelo a retornar **output estructurado** (JSON o esquema parseable) con:
   - `card_name`: nombre de la carta.
   - `include`: decisión binaria (true/false).
   - `synergy_score`: opcional, score numérico de sinergia.
   - `rationale`: justificación técnica breve.

El prompt debe insistir en el formato estructurado para que la Etapa 5 sea determinista.

### Etapa 5: Data Serialization

Parseo del output estructurado del LLM y exportación tabular a `.csv`. Se implementa **generación dinámica de nombres de archivo mediante timestamps** (ej. `evaluation_20260803_133942.csv`) para garantizar idempotencia entre ejecuciones: cada corrida genera un archivo único y nunca sobrescribe resultados previos.

## Stack Tecnológico

| Capa | Herramienta |
|------|-------------|
| Lenguaje | Python 3 |
| CLI | `argparse` |
| Librerías stdlib | `csv`, `json`, `os`, `re` |
| HTTP | `requests` (Scryfall, Moxfield, Archidekt) |
| LLM | Abstracción `LLMProvider`: Gemini vía REST (default), OpenAI vía SDK y Anthropic vía SDK opcional |

## Roles del Equipo

| Nombre | Rol |
|--------|-----|
| Leonardo | Senior del equipo |
| Antony | Trainee |
| Mathias | Junior |

## Reglas de Código y Vibe Coding

### Estándares de código

- Código limpio, legible y con buenas prácticas.
- **Type Hints estrictos** en todas las firmas de funciones.
- **Docstrings Google-style** obligatorios.
- Modularidad: una responsabilidad por función y por módulo.
- Manejo de errores explícito (`requests.HTTPError`, `json.JSONDecodeError`, etc.).

### Coherencia con el proyecto y reutilización

Todo el código del proyecto sigue una regla simple: **primero buscar, luego construir**.

- **Antes de escribir cualquier lógica, buscar si ya existe un componente que la resuelva** en `mtg_commander/` (client HTTP, normalización, cache, detección de set, etc.). Si existe, reutilizarlo sí o sí: no duplicar. Reusar el trabajo de otros no es "copiar", es la forma estándar de trabajar en equipo: cada quien construye sobre lo que ya existe y el proyecto crece más parejo.
- **Nada de `requests` directo contra Scryfall**: todo el HTTP a la API pasa por `ScryfallClient` (`mtg_commander/extraction/client.py`) para respetar headers, rate limits y retry/429. Si falta un helper, se agrega al client (o al módulo que corresponda), nunca se escribe HTTP suelto en la feature.
- Excepción transitoria conocida: `mtg_commander/ingestion/commander.py` será migrado en T-107; no replicar ese patrón en código nuevo.
- Validar que el código siga la línea arquitectónica del pipeline (etapas y contratos de datos definidos en `AGENTS.md`) y los patrones ya establecidos (`card_info.py`, `set_cards.py`, etc.): inyección del client como parámetro, cache en `outputs/cache`, etc.
- Antes de dar por terminada cualquier tarea, el agente verifica explícitamente esta coherencia y la comenta en la revisión como parte del proceso habitual del equipo.
- Las pruebas viven exclusivamente en `tests/`, con una estructura espejo de `mtg_commander/`; el código productivo no contiene archivos `test_*.py`.

### Modo Asistente Dinámico

Al comienzo de cada sesión o ticket, el agente **debe preguntar primero quién está interactuando** (Antony, Mathias o Leonardo) antes de responder o generar código, y ajustar el nivel de explicación según el integrante:

- **Antony (Trainee):** Explicar la lógica paso a paso y el *por qué* de cada función. Incluir contexto pedagógico, ejemplos y señalar errores comunes.
- **Mathias (Junior):** Enfocarse en las buenas prácticas de la tarea (typing, docstrings, manejo de errores), con explicaciones breves y foco en por qué se hace así.
- **Leonardo (Senior):** Entregar el código directo al grano, enfocado en arquitectura, eficiencia y diseño. Sin explicaciones pedagógicas.

### Flujo de trabajo sugerido

1. Tomar el siguiente ticket pendiente de `TICKETS.md` y asignar responsable (Antony / Mathias / Leonardo).
2. El agente adapta su nivel de detalle según el responsable.
3. Implementación con estándares del proyecto.
4. Verificación (ejecución manual o pruebas unitarias cuando aplique).
5. Revisión del código generado.
6. Marcar el ticket como completado en `TICKETS.md`.

### Control de versiones

- Antes de cada `pull`/`push`, sincronizar siempre con el remoto ejecutando `git pull --rebase` para integrar los cambios remotos.
- Nunca forzar push (`--force`).
- En caso de conflicto, resolverlo antes de continuar y verificar que el pipeline sigue funcionando.
- **Conventional Commits**: usar mensajes de commit con formato `tipo: descripción` (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Mantiene el `git log` legible y facilita la revisión en equipo.

### Dependencias

- **Siempre que se instale una librería nueva, actualizar `requirements.txt`** en el mismo commit (con su versión, ej. `streamlit>=1.30,<2`). El `requirements.txt` es la única fuente de verdad de dependencias: una librería instalada solo localmente no cuenta como instalada.
- Los artefactos propios del ambiente (`.venv/`) no se versionan.

### `.gitignore` y secretos

- Mantener el `.gitignore` al día: los artefactos de ejecución y archivos personales **no se versionan**.
- **`estrategia.md` no se sube al repositorio**: se genera una vez por mazo y es personal de cada integrante. Está excluido vía `.gitignore`.
- Nunca commitear claves de API, tokens ni credenciales. Cualquier secreto se maneja vía variables de entorno.

### README

- El `README.md` es la fuente viva de documentación del proyecto: cada feature nueva se documenta ahí en el mismo commit.

### Changelog

- El `CHANGELOG.md` se actualiza **únicamente en el momento de commitear y pushear**, no durante el desarrollo. Evita llenarlo de basura de "hacer y deshacer" a mitad de tarea.
- Al pushear, agrupar todos los cambios de esa entrega en una sola entrada con formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/): fecha + categorías con sus cambios.
- Categorías: `Added` (features nuevas), `Changed` (cambios/ajustes), `Fixed` (bug fixes), `Deprecated`, `Removed`, `Security`.
- El `CHANGELOG.md` se versiona junto al resto del proyecto, de modo que cada push deja una traza de qué se pusheó.
- Mantener las entradas más recientes al inicio, en orden cronológico inverso.

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

Envío del decklist normalizado al LLM para inferir un perfil estratégico detallado. El resultado se exporta como `estrategia.md`, que incluye:

- Arquetipo(s) (ej. *Control/Drenaje en Esper para Y'shtola*, *Evasión/Combat Triggers en Bant para Tidus*).
- Win conditions del mazo.
- Sinergias clave y paquetes de cartas.
- En lo posible: colores, identidad de color y presupuesto aproximado de mana (curve).

**`estrategia.md` es el system context persistente**: se genera una vez por mazo y se reutiliza en cada ejecución de la Etapa 4. **No se versiona ni se comparte** (ver `.gitignore` y secretos): es personal de cada integrante. Si el mazo no cambia, este archivo no debería regenerarse.

### Etapa 3: Data Extraction (Scryfall API)

Queries a la API REST de Scryfall usando sintaxis avanzada:

- Ejemplo de query: `set:{code} id<={color_identity} -type:land`
- Manejo obligatorio de paginación JSON (campo `next_page`).
- Control estricto de rate-limits: **delay de 50–100ms entre peticiones** para respetar los términos de Scryfall.
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
| LLM | SDK correspondiente a la API elegida (Gemini, por defecto; sujeto a definir) |

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
- **Docstrings** obligatorios (formato Google o NumPy, a definir).
- Modularidad: una responsabilidad por función y por módulo.
- Manejo de errores explícito (`requests.HTTPError`, `json.JSONDecodeError`, etc.).

### Modo Asistente Dinámico

Al generar código, el agente **debe preguntar primero quién resolverá el ticket** (Antony, Mathias o Leonardo) y ajustar el nivel de explicación:

- **Antony (Trainee):** Explicar la lógica paso a paso y el *por qué* de cada función. Incluir contexto pedagógico, ejemplos y señalar errores comunes.
- **Mathias (Junior):** Enfocarse en las buenas prácticas de la tarea (typing, docstrings, manejo de errores), con explicaciones breves y foco en por qué se hace así.
- **Leonardo (Senior):** Entregar el código directo al grano, enfocado en arquitectura, eficiencia y diseño. Sin explicaciones pedagógicas.

### Flujo de trabajo sugerido

1. Definir el ticket y asignar responsable (Antony / Mathias / Leonardo).
2. El agente adapta su nivel de detalle según el responsable.
3. Implementación con estándares del proyecto.
4. Verificación (ejecución manual o pruebas unitarias cuando aplique).
5. Revisión del código generado.

### Control de versiones

- Antes de cada `pull`/`push`, sincronizar siempre con el remoto ejecutando `git pull --rebase` para integrar los cambios remotos.
- Nunca forzar push (`--force`).
- En caso de conflicto, resolverlo antes de continuar y verificar que el pipeline sigue funcionando.
- **Conventional Commits**: usar mensajes de commit con formato `tipo: descripción` (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Mantiene el `git log` legible y facilita la revisión en equipo.

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

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

## [2026-08-17]

### Added

- **T-401 (Ingesta remota Moxfield/Archidekt):** nuevo `mtg_commander/ingestion/remote.py` con `obtener_decklist_remoto()`, que arma un `DecklistRemoto` (comandante(s), mainboard, sideboard, considering — el "maybeboard" de la API — y tokens, cada uno como `{nombre: cantidad}`) a partir de la URL de un mazo público de Moxfield o Archidekt. También expone `leer_decklist_remoto()`, compatible con el contrato de `leer_decklist()` (T-002), para enchufar mazos remotos al resto del pipeline sin cambios. Implementado por Mathias como aporte extra (el ticket estaba asignado a Leonardo).
- **Tests de `remote.py`:** `tests/ingestion/test_remote.py` (mockeando `requests.get`) cubre extracción de ID desde la URL, clasificación por categoría en Archidekt, suma de cantidades cuando la misma carta aparece en más de un printing, categorías ausentes (`None`) y URLs de sitios no soportados.

### Fixed

- **`remote.py` (Archidekt) — cantidades pisadas en vez de sumadas:** una misma carta puede aparecer más de una vez en la lista `cards` de Archidekt (distintos printings/foils). La primera versión sobrescribía la cantidad de la entrada repetida en vez de sumarla; se corrigió antes de mergear, verificado contra un mazo real con 4 cartas repetidas (ej. "Breeding Pool": 2 + 1 = 3).

- **T-105 (LLM Pass 1):** abstracción intercambiable de providers LLM (`Gemini`, `OpenAI`, `Anthropic`), perfilado automático del deck (`DeckProfile`), estadísticas deterministas (`DeckStats`) y generación de `estrategia.md` a partir de las cartas enriquecidas y el research trazable.
- **Research orientado por deck:** las búsquedas de Reddit combinan queries generales del comandante con arquetipos y mecánicas inferidos automáticamente del deck; `research.md` registra la query de cada fuente.
- **Cache persistente por carta:** las respuestas normalizadas de Scryfall se guardan individualmente, sin TTL para datos de gameplay, con soporte para cartas de doble cara y URLs de imagen.
- **T-106 (Context CLI):** `python -m mtg_commander.context --deck <archivo>` orquesta el enriquecimiento Scryfall, perfilado, research y síntesis de `estrategia.md`; reutiliza el resultado cuando el fingerprint normalizado del deck no cambió.
- **Tests del orquestador:** cobertura de generación, reutilización e invalidación del contexto por cambios en el deck.

### Changed

- **Suite de tests:** se mueve desde los módulos productivos a `tests/`, manteniendo la estructura espejo (`context`, `extraction`, `llm`, `serialization`).
- **Documentación:** README y AGENTS reflejan el estado actual del pipeline, providers LLM, research vía PRAW y el CLI de Context.
- **Payload de cartas:** se amplía con CMC, keywords, mana producido, estadísticas de combate, layout, caras modales e `image_uris`; las URLs de imagen se excluyen del contexto enviado al LLM.
- **Research web:** se acota la cantidad y tamaño de posts/comentarios para controlar el contexto y el costo del Pass 1.
- **Tests de cache:** se aíslan en directorios temporales para no borrar artefactos reales dentro de `outputs/`.

## [2026-08-15]

### Added

- **T-302 (Serialización CSV):** nuevo `mtg_commander/serialization/csv_export.py` con `cargar_evaluaciones()` (lee el JSON de T-301) y `exportar_evaluacion_csv()`: exporta con todas las columnas del contrato definido junto al mock (`card_name`, `include`, `recommendation_tier`, `synergy_score`, `synergy_category`, `synergy_themes`, `pros`, `cons`, `rationale`), serializando las columnas de lista como texto separado por `; `. Reutiliza `generar_nombre_csv()` (T-003) para la unicidad de archivos. Las filas a las que les falta algún campo del contrato se loguean como inválidas y se excluyen, sin crashear el resto de la exportación.
- **Tests de `csv_export.py`:** `mtg_commander/serialization/test_csv_export.py` corre contra el mock real (`data/evaluation_mock.json`), y cubre serialización de listas, filas inválidas, JSON roto y que dos corridas no se pisen.

- **T-104 (Research web del deck):** Nuevo módulo `mtg_commander/context/reddit_research.py` que consulta hilos de Reddit vía PRAW con queries estratégicos enfocados en win conditions y sinergias. deduplicación por ID de post, y sanitización de texto con límites definidos de caracteres (`MAX_CHARS_POST` y `MAX_CHARS_COMMENT`) para controlar el gasto de tokens.
- **Script de utilidad y CLI:** Nuevo `scripts/run_research.py` para invocar manualmente el módulo de research y `scripts/verify_reddit_auth.py` para testing de credenciales.
- **Configuración local:** Creación de `.env.example` para documentar secretos de Reddit sin comprometerlos en el versionado.

### Changed

- **`requirements.txt`:** Se agregan dependencias `praw>=7.7,<8` y `python-dotenv>=1.0,<2`.
- **`README.md`:** Se actualiza el estado del pipeline agregando la etapa 2b completa y la explicación de requerimientos del `.env`.
- **`TICKETS.md`:** Marcar el ticket T-104 como completado.
- **`mtg_commander/context/research_template.md`:** Actualizado con sección de curva de maná, nivel de poder separado de arquetipo, y lista de cartas excluidas y debatidas.
- **`.gitignore`:** Exclusión preventiva de `.env` y `research.md`.

## [2026-08-11]

### Added

- **T-402 (Cache LRU + evaluación de bulk data files):** nuevo `mtg_commander/extraction/cache.py` — centraliza la lógica de cache local (antes duplicada en `latest_set.py` y `set_cards.py`, siguiendo la nueva regla de reutilización de `AGENTS.md`) con dos políticas independientes: TTL de 24h por entrada, y **LRU real** (si hay `MAX_ENTRADAS` archivos de cache, descarta el usado hace más tiempo antes de guardar uno nuevo, por fecha de modificación del archivo).
- **Tests de `cache.py`:** `mtg_commander/extraction/test_cache.py` valida guardar/leer, vencimiento por TTL, y la política LRU (incluyendo que `leer()` protege una entrada de ser descartada, al marcarla como usada recientemente).
- **Evaluación de bulk data files (parte del ticket, sin código):** Scryfall publica diariamente volcados completos del catálogo (`/docs/api/bulk-data`), pensados para consumidores que necesitan miles de cartas de una sola vez. Nuestro volumen por corrida es bajo (1 listado de sets con cache + una búsqueda paginada por set, típicamente 1 página) y ya cacheado 24h — el costo de bajar/parsear un volcado de decenas de MB no se justifica hoy. Se documenta la decisión acá para no repetir la evaluación; revisar si el pipeline empieza a evaluar múltiples sets/mazos por corrida o a buscar en todo el catálogo.

### Changed

- **`latest_set.py` / `set_cards.py`:** migrados para usar `cache.py` en vez de su lógica de cache propia (mismo comportamiento, sin duplicación).

## [2026-08-11]

### Changed

- **`AGENTS.md`:** nueva sección "Coherencia con el proyecto y reutilización" (regla: primero buscar, luego construir; todo el HTTP a Scryfall pasa por `ScryfallClient`; nada de `requests` suelto) y nueva sección "Dependencias" (toda librería nueva se actualiza en `requirements.txt` en el mismo commit).
- **`TICKETS.md`:** nuevos tickets **T-107** (migrar `obtener_color_identity()` al `ScryfallClient`, asignado a Antony) y **T-108** (frontend Streamlit de consulta de cartas usando `ScryfallClient`, asignado a Antony).

## [2026-08-11]

### Added

- **T-202 (Extracción de cartas del set):** nuevo `mtg_commander/extraction/set_cards.py` con `obtener_cartas_del_set()`: arma la query `set:{code} id<={identity} -type:land`, pagina `/cards/search` con el parámetro `page` hasta agotar `has_more`, y cachea el resultado combinado en `outputs/cache/cards_{set}_{identity}.json` (24h). Maneja el 404 que devuelve Scryfall cuando la búsqueda no tiene resultados (no crashea, cachea lista vacía). Verificado con la API real: 48 cartas WUB de "Star Trek" en 0.38s, 0.01s en la 2da corrida (cache).
- **Tests de `set_cards.py`:** `mtg_commander/extraction/test_set_cards.py` (mockeando `ScryfallClient.get`) valida el armado de la query, paginación multi-página, cache vigente/vencido y el caso 404 sin resultados.
- **T-102 (Info individual de cartas vía `/cards/collection`):** nuevo `mtg_commander/context/card_info.py` con `obtener_info_cartas()`: parte el decklist en batches de hasta 75 nombres (`partir_en_batches`), deduplica antes de consultar, resuelve cada batch contra `/cards/collection` y normaliza el payload a los campos mínimos (`oracle_text`, `mana_cost`, `type_line`, `colors`, `color_identity`, `rarity`). Las cartas no encontradas se loguean como warning en vez de crashear. Verificado contra `data/yshtola_esper.txt`: 58/58 cartas resueltas.
- **Tests de `card_info.py`:** `mtg_commander/context/test_card_info.py` (mockeando `ScryfallClient.post`) valida el batching (160 → 3 batches), la deduplicación, el orden de salida y el manejo de `not_found`.
- **T-201 (Detección del último set + cache local):** nuevo `mtg_commander/extraction/latest_set.py` con `obtener_ultimo_set()`: filtra `/sets` por `set_type` (`expansion`/`core`) y elige el de `released_at` más reciente; cachea el listado en `outputs/cache/sets_cache.json` con ventana de validez de 24h; soporta override `--set {code}` vía pedido directo a `/sets/{code}` (no toca el cache). Verificado con la API real: 1ra corrida ~1.9s (descarga), 2da corrida ~0.01s (cache).
- **Tests de `latest_set.py`:** `mtg_commander/extraction/test_latest_set.py` (mockeando `ScryfallClient.get`, cache aislado en cada test) valida filtrado por tipo, cache vigente/vencido, override y el caso sin sets válidos.
- **T-003 (Serialización de nombres CSV):** `generar_nombre_csv()` migrado a `mtg_commander/serialization/naming.py`, con salida centralizada en `outputs/` (se crea automáticamente si no existe).
- **Tests de `naming.py`:** `mtg_commander/serialization/test_naming.py` valida unicidad (100 llamadas consecutivas sin colisión), formato del nombre y creación de la carpeta `outputs/`.

### Changed

- **`mtg_commander/extraction/client.py`:** `_request` acepta ahora un `json_body` opcional y se agregó `post(endpoint, json_body)` como punto de entrada público, necesario porque `/cards/collection` requiere POST con body JSON (a diferencia de `/sets` o `/cards/named`, que son GET).
- **`.gitignore`:** se agrega `outputs/` (cache local y CSVs generados en tiempo de ejecución no se versionan).

### Fixed

- **`naming.py` — colisión de nombres en llamadas consecutivas:** el timestamp original (resolución de segundos) generaba el mismo nombre si el pipeline se llamaba dos veces muy seguido, violando el criterio de aceptación de T-003. En este equipo Windows, hasta `datetime.now()` con microsegundos devolvía el mismo valor en llamadas inmediatas (resolución de reloj del sistema más gruesa que 1µs). Se resolvió agregando un sufijo aleatorio corto (`uuid.uuid4().hex[:8]`) además del timestamp legible, garantizando unicidad sin depender de la resolución del reloj.

## [2026-08-06]

### Added

- **T-101 (Cliente base de Scryfall):** nuevo `mtg_commander/extraction/client.py` con la clase `ScryfallClient`: sesión `requests.Session` con headers `User-Agent`/`Accept` fijos, rate limiting configurable por endpoint (500ms para `/cards/search`, `/cards/collection`, `/cards/named`, `/cards/random`; 100ms para el resto) y manejo de HTTP 429 con retry/backoff exponencial. Expone `get(endpoint, params)` como punto de entrada público.
- **Tests de `client.py`:** `mtg_commander/extraction/test_client.py` (mockeando `session.request` con `unittest.mock`, sin golpear la red real) valida que un 429 se reintenta hasta obtener éxito y que un 429 persistente agota los reintentos y lanza un `RuntimeError` controlado en vez de crashear.

## [2026-08-03]

### Added

- **T-001 (Setup del entorno):** virtualenv `.venv/` creado con dependencias instaladas y verificado (`import requests` OK). Estructura de paquetes `mtg_commander/` definida: `ingestion`, `context`, `extraction`, `evaluation` y `serialization` con sus `__init__.py`.
- **T-002 (Migración a `ingestion/local.py`):** `leer_decklist()` migrado a `mtg_commander/ingestion/local.py` con type hints estrictos, docstrings y manejo explícito de secciones: se procesan `Commander`/`Deck` y se descartan `Sideboard`/`Maybeboard`. También `leer_comandante()` para detectar el comandante del decklist.
- **T-103 (Comandante y color identity):** nuevo `mtg_commander/ingestion/commander.py` con `obtener_color_identity()` (consulta a Scryfall `/cards/named` con fallback exact→fuzzy, User-Agent custom y normalización al orden oficial WUBRG) y `detectar_comandante()` (`dataclass PerfilComandante`). Para Y'shtola devuelve comandante y `color_identity = ["W", "U", "B"]`.

### Changed

- **`Main.py`:** importa `leer_decklist()` desde el paquete nuevo; la advertencia de cartas repetidas pasa a `Main.py` con `collections.Counter` (O(n) en lugar de O(n²)); se integra la detección de comandante y color identity (PASO 1.5); se corrigen caracteres no-ASCII (`✓`) que rompían la consola en Windows (UnicodeEncodeError).
- **`data/yshtola_esper.txt`:** se corrige el nombre del comandante al oficial de Scryfall ("Y'shtola, Night's Blessed").

### Removed

- **`tarea1.py`:** eliminado (código migrado a `mtg_commander/ingestion/local.py`).

## [2026-08-03]

### Added

- **`TICKETS.md`:** backlog del proyecto desglosado por tareas, con responsable asignado según seniority (Antony / Mathias / Leonardo), dificultad, dependencias, criterios de aceptación y orden de ejecución sugerido.
- **`AGENTS.md` (Etapa 3):** se documentó la **detección del último set** como paso previo a la extracción: `GET /sets` filtrando por `set_type` (`expansion`/`core`) y `released_at` más reciente, con `GET /sets/{code}` como alternativa directa. El set detectado se pasa como parámetro a las queries.
- **`AGENTS.md` (Etapa 2):** se redefinió la generación de `estrategia.md` como **flujo propio de 3 pasos**: 2a enriquecimiento de cartas vía `/cards/collection`, 2b research web (Reddit/Google) con output intermedio `research.md`, y 2c síntesis con LLM (Pass 1).
- **`AGENTS.md` (Flujo de trabajo):** se agregó referencia al backlog `TICKETS.md` y a marcar tickets como completados al terminar.

### Changed

- **`README.md`:** se actualizó al estado real del proyecto (Etapa 1 y 5 parciales en `tarea1.py`/`tarea2.py`), se documentó el sub-flujo de Context Generation, la detección del último set en la Etapa 3 y la referencia a `TICKETS.md`.

## [2026-08-03]

### Changed

- **`AGENTS.md` (Etapa 3):** se documentaron los requisitos técnicos de la API de Scryfall (API pública sin cuenta ni API key, solo HTTPS, headers `User-Agent` y `Accept` obligatorios), los **rate limits correctos** (2 peticiones/segundo para `search`/`named`/`random`/`collection`; 10/segundo para el resto; manejo explícito del HTTP 429) y la **recomendación de caching** (cachear datos ≥24h y usar bulk data files para consultas en volumen). Se corrigió el delay previo de 50–100ms, insuficiente para `/cards/search`.
- **`AGENTS.md` (Modo Asistente Dinámico):** la pregunta de quién está interactuando (Antony, Mathias o Leonardo) ahora se dispara **al comienzo de cada sesión o ticket**, no solo al generar código. Esto evita que el agente omita identificar al integrante cuando la tarea no implica escribir código.

### Added

- **Convención de Conventional Commits en `AGENTS.md`:** formato fijo de mensajes de commit (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) para mantener un `git log` legible y facilitar la revisión en equipo.
- **Reglas de `.gitignore` y secretos en `AGENTS.md`:** artefactos de ejecución y archivos personales no se versionan; `estrategia.md` queda excluido del repositorio; nunca commitear claves de API ni tokens.
- **Política de README en `AGENTS.md`:** el `README.md` es la fuente viva de documentación, cada feature nueva se documenta ahí en el mismo commit.
- **Sección "Changelog" en `AGENTS.md`:** obligación de actualizar `CHANGELOG.md` al momento de pushear, con entradas agrupadas por categorías.

### Changed

- **`AGENTS.md` (Etapa 2):** se aclaró que `estrategia.md` se genera una vez por mazo, no se regenera si el mazo no cambia y **no se versiona ni se comparte** (es personal de cada integrante, excluido vía `.gitignore`).
- **`AGENTS.md` (Control de versiones):** se agregó la sincronización obligatoria con `git pull --rebase` antes de cada pull/push y la resolución de conflictos previa a continuar.

### Fixed

- N/A

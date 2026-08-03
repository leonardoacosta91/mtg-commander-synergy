# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

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

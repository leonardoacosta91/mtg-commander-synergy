# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

## [2026-08-03]

### Changed

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

# Learning OS — TASKS.md

Backlog ejecutable derivado de `IMPLEMENTATION_PLAN.md`.

## Reglas de ejecución

- Ejecutar en orden salvo dependencias explícitas.
- Una tarea no está `DONE` hasta que su aceptación y tests se cumplen.
- Trabajar en ramas `feature/<task-id>-<nombre>` y fusionar mediante PR a `main`.
- No implementar fases futuras anticipadamente.
- Si una tarea contradice una especificación normativa, detenerse y documentar el conflicto.
- Los tests de Obsidian usan únicamente vaults temporales.

Estados: `TODO → IN_PROGRESS → BLOCKED → DONE`.

---

# Fase 0 — GitHub y bootstrap

### T001 — Estructura inicial
**Estado:** DONE
**Dep:** —  
**Archivos:** raíz, `backend/`, `frontend/`, `scripts/`.  
**Aceptación:** estructura del repositorio creada y documentación normativa presente.

### T002 — Inicializar Git
**Estado:** DONE
**Dep:** T001  
`git init`, rama `main`, working tree limpio.

### T003 — `.gitignore`
**Estado:** DONE
**Dep:** T002  
Ignorar `.venv`, `node_modules`, builds, `.env`, bases SQLite locales, IDEs y caches; no ignorar código, tests, migraciones ni prompts.

### T004 — Commit inicial
**Estado:** DONE
**Dep:** T003  
Commit `chore: bootstrap learning os repository`.

### T005 — Crear GitHub remote
**Estado:** DONE
**Dep:** T004  
Crear repositorio GitHub privado por defecto; configurar `origin`; no inventar owner/URL.

### T006 — Workflow de ramas
**Estado:** DONE
**Dep:** T005  
Definir `main`, `feature/*`, `fix/*`, `chore/*`; `develop` es opcional.

### T007 — Protección de `main`
**Estado:** DONE (alcance reducido a propósito, ver nota)
**Dep:** T005  
PR requerido, checks de CI requeridos y sin force-push cuando la configuración de GitHub lo permita.

**Nota:** Bloqueada originalmente (repo privado en plan Free, 403 de la API de branch protection); desbloqueada el 2026-09-24 cuando el usuario hizo público el repositorio. Antes de aplicar nada se preguntó al usuario (`AskUserQuestion`) qué nivel quería, porque la especificación literal de la tarea ("PR requerido") habría roto el flujo de push directo a `main` usado en TODA la sesión hasta ahora (T130-T141, ninguno vía PR pese a que docs/AGENTS.md #18 documenta PR como flujo por defecto) -- una protección estricta con revisión de PR obligatoria habría bloqueado tanto al usuario como al propio agente de seguir con ese mismo patrón sin aviso. El usuario eligió la opción ligera: exige que los 3 checks de CI (`backend`, `frontend`, `e2e`) estén en verde y bloquea force-push/borrado de `main`, pero NO exige pull request -- `enforce_admins: false` y `required_pull_request_reviews: null`, así que el push directo sigue funcionando exactamente igual que hasta ahora. Aplicado vía `gh api -X PUT repos/e-serrano/Learning-OS/branches/main/protection`, verificado leyendo la configuración de vuelta.

### T008 — GitHub Actions
**Estado:** DONE
**Dep:** T010, T011  
Crear `.github/workflows/ci.yml`; ejecutar backend tests, Ruff, mypy, frontend build/tests.

### T009 — Templates GitHub
**Estado:** DONE
**Dep:** T005  
Issue bug/feature y PR template con cambios, motivo, tests e impacto en especificación.

### T010 — Backend bootstrap
**Estado:** DONE
**Dep:** T001  
Python 3.13+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest, httpx, Ruff, mypy, uv.

### T011 — Frontend bootstrap
**Estado:** DONE
**Dep:** T001  
React + TypeScript + Vite; `npm run build` funcional.

### T012 — Entorno de desarrollo
**Estado:** DONE
**Dep:** T010, T011  
`.env.example`, README de desarrollo y comandos reproducibles.

---

# Fase 1 — Configuración y onboarding

### T013 — Modelo de configuración local
**Estado:** DONE (modelo Pydantic `AppConfig`; persistencia migrada a SQLite en T034)
**Dep:** T010  
Configurar `vault_path`, provider, model, base URL, idioma y estado de onboarding. Sin secretos.

### T014 — Almacenamiento seguro de credenciales
**Estado:** DONE
**Dep:** T013  
Usar OS keyring/credential store para OpenAI, Anthropic, OpenRouter y NVIDIA. Nunca SQLite/Markdown/Git/logs/localStorage.

### T015 — Registro de providers
**Estado:** DONE
**Dep:** T010  
IDs: `mock`, `ollama`, `openai`, `anthropic`, `openrouter`, `nvidia_nim`, `openai_compatible`.

### T016 — Configuración de provider
**Estado:** DONE
**Dep:** T015  
`provider_id`, `model`, `base_url`, `credential_ref`, `enabled`, `is_default`.

### T017 — Adaptadores de providers
**Estado:** DONE (alcance dividido, ver nota)
**Dep:** T015, T016  
Implementar adapters separados; Anthropic no se trata como OpenAI-compatible; NVIDIA permite endpoint configurable.

**Nota de división:** T017 se solapaba con T051–T056 (un adapter real por provider, Fase 4). Para no anticipar Fase 4, T017 entrega: protocolo `AIProvider` (`app/ai/protocol.py`), `AIRequest`, excepciones (`app/ai/errors.py`) y `MockProvider` completo y determinista (`app/ai/adapters/mock.py`), que ya cubre "Anthropic no se trata como OpenAI-compatible" al exigir clases de adapter separadas por diseño del protocolo. Los adapters de red reales (Ollama/OpenAI/Anthropic/OpenRouter/NVIDIA/OpenAI-compatible) se implementan en sus tareas T051–T056 dedicadas.

### T018 — Health/capability check
**Estado:** DONE (validación estructural; ver nota)
**Dep:** T017  
Validar endpoint, credencial, modelo y capacidad mínima de structured output sin enviar contenido del vault.

**Nota de alcance:** `check_provider_capability` (`app/ai/capability_check.py`) valida localmente credencial/base_url/model requeridos según el registro de providers y nunca toca red ni vault. La validación en vivo (conexión real + round-trip de structured output) se añade cuando los adapters reales (T051–T056) existan; hasta entonces `ok=True` significa "configuración bien formada", no "provider confirmado alcanzable".

### T019 — Máquina de estados de onboarding
**Estado:** DONE
**Dep:** T013  
`WELCOME → VAULT → VAULT_SCAN → AI_PROVIDER → CREDENTIAL → MODEL → VALIDATE → FIRST_GOAL → COMPLETE`.

### T020 — UI selección de vault
**Estado:** DONE
**Dep:** T019  
Seleccionar directorio, validar existencia/lectura y mostrar resultado del scan read-only.

### T021 — UI selección de IA
**Estado:** DONE
**Dep:** T019, T015  
Cards para Ollama, OpenAI, Anthropic/Claude, OpenRouter, NVIDIA y OpenAI-compatible; explicar local/remoto y credenciales.

### T022 — UI credenciales/modelo
**Estado:** DONE (combinada con T023, ver nota)
**Dep:** T014, T021  
Introducir credencial de forma segura, elegir modelo y no conservar el secreto en estado persistente del frontend.

### T023 — Validación de provider en onboarding
**Estado:** DONE
**Dep:** T018, T022  
`select → credential → model → test → result → continue`.

**Nota T022/T023:** Implementadas como un único componente (`CredentialModelStep.tsx`) porque son una sola interacción de usuario continua (introducir modelo+credencial → probar conexión → ver resultado). Verificado manualmente en navegador: el valor de la credencial nunca aparece en ninguna respuesta de red ni se conserva en estado tras una validación exitosa.

### T024 — Onboarding resumible
**Estado:** DONE
**Dep:** T019  
Reabrir aplicación y continuar desde el último paso válido.

**Nota:** Verificado manualmente — recargar el navegador tras completar onboarding reabre directamente en el paso persistido (`GET /onboarding/status` en el montaje del wizard).

### T025 — API onboarding
**Estado:** DONE (implementada antes de T020–T024 UI; ver nota)
**Dep:** T013, T019  
`GET /onboarding/status`; `POST /onboarding/vault`; `POST /onboarding/ai-provider`; `POST /onboarding/ai-provider/validate`; `POST /onboarding/complete`.

**Nota de orden:** Implementada antes que T020–T024 (UI de onboarding) para respetar `AGENTS.md` §2 (API antes que UI; "no empezar por workflows de UI sin modelo estable detrás"). El grafo de `Dep` de T025 (T013, T019) ya lo permitía. Incluye un scanner de vault mínimo de solo lectura (`app/obsidian/onboarding_scan.py`) — la versión completa con frontmatter/hashing/índice es T037–T038 (Fase 3). `POST /onboarding/complete` exige vault + provider por defecto validado, tal como dice literalmente `API_SPEC.md` §13; el paso `FIRST_GOAL` avanza como paso de paso (pass-through) hasta que exista el servicio de creación de goals (T065, Fase 5).

### T026 — E2E onboarding
**Estado:** DONE
**Dep:** T020–T025  
Probar instalación limpia con Mock/Ollama y provider remoto simulado.

**Nota:** Cubierto por tests de integración de API (`backend/tests/api/test_onboarding.py`) que ejecutan el flujo completo `status → vault → ai-provider → validate → complete` con Mock, Ollama (local, sin credencial) y un provider remoto simulado (Anthropic con credencial falsa), más verificación manual en navegador real contra el backend real (vault válido/ inválido, selección de provider, fallo por credencial faltante, resumibilidad tras recarga). No se añadió un framework de E2E de navegador (Playwright) dedicado — no es necesario aún y evita fijar una decisión de infraestructura de testing sin necesidad clara.

---

# Fase 2 — Dominio y SQLite

### T027 — SQLite engine
**Estado:** DONE
**Dep:** T010, T013  
Foreign keys ON, WAL, busy timeout, timestamps UTC.

### T028 — Alembic
**Estado:** DONE
**Dep:** T027  
Migración desde DB vacía y esquema versionado.

### T029 — Domain enums
**Estado:** DONE
**Dep:** T010  
Todos los enums de `DOMAIN_MODEL.md` como valores string canónicos.

### T030 — Domain entities
**Estado:** DONE
**Dep:** T029  
Goal, Concept, Skill, Evidence, Exercise, Attempt, Evaluation, Mistake, Review, Session, Activity, Project, Assessment.

### T031 — Value objects
**Estado:** DONE
**Dep:** T030  
Mastery 0..5, confidence/retention 0..100, importance/difficulty 1..5.

### T032 — Repository ports
**Estado:** DONE
**Dep:** T030  
Interfaces para goals, concepts, evidence, sessions, exercises, reviews, mistakes, vault, AI, clock e IDs.

**Nota:** `app/domain/ports.py`. El puerto "AI" no se redeclara — `app.ai.protocol.AIProvider` (T017) ya cumple ese contrato. Métodos mantenidos deliberadamente mínimos (add/get/update + 1-2 queries justificadas por los índices de `DATABASE_SCHEMA.md` §3); se ampliarán en T035 según necesidad real de los servicios. `EvidenceRepository` no tiene `update`/`delete` (append-only).

### T033 — SQLAlchemy models
**Estado:** DONE
**Dep:** T028, T030  
Implementar tablas de `DATABASE_SCHEMA.md` sin usar ORM models como domain entities.

**Nota:** 17 tablas en `app/persistence/models/` (una por archivo, agrupadas como en `DATABASE_SCHEMA.md` §2), más los 6 índices de §3. Timestamps como `TEXT` (no `DateTime` nativo) para conformidad byte-exacta con el esquema — la conversión datetime↔ISO-8601 es responsabilidad de los repositories (T035). Migración `fd57ee07b3b9_domain_schema` generada con `alembic revision --autogenerate` y verificada (upgrade contra DB vacía, FKs correctas, 17 tablas + `alembic_version`).

### T034 — Config tables migration
**Estado:** DONE
**Dep:** T033  
Crear `app_settings` y `ai_provider_configs`; credential_ref nunca contiene el secreto.

**Nota:** Migración `570ee5d78516_local_configuration`. `ConfigStore` (T013) reescrito de JSON a SQLite (mismo `load()`/`save()`, constructor ahora recibe `db_path`). Verificado con flujo completo de onboarding vía HTTP real contra DB migrada real (no solo TestClient). `Settings.config_path`/`LEARNINGOS_CONFIG_PATH` eliminados (ya no se usan). `DEVELOPMENT.md` actualizado: `alembic upgrade head` ahora requerido antes de arrancar el backend.

### T035 — Repositories
**Estado:** DONE
**Dep:** T032, T033  
CRUD y métodos de consulta necesarios; evidence append-only.

**Nota:** `app/persistence/repositories/` — implementación SQL de los 7 puertos de T032 (Sql{Goal,Concept,Evidence,Session,Exercise,Review,Mistake}Repository). `SqlEvidenceRepository` no tiene `update`/`delete` (verificado con test explícito de ausencia). Descubierto durante la implementación: mapear entre entidades de dominio y modelos ORM requiere gestionar campos que no coinciden 1:1 — `Skill`/`Session` no tienen `created_at` en el dominio pero la tabla sí (el repository lo sintetiza); `Exercise` empaqueta `skill_ids`/`prerequisite_ids`/`success_criteria`/`hints`/`common_mistakes`/`transfer_variant` en `metadata_json` porque `DATABASE_SCHEMA.md` no tiene columnas dedicadas, mientras que `concept_ids` viene de la tabla join `exercise_concepts`. Corregido un bug real: clases ORM sin `relationship()` declarado no se ordenan automáticamente en el flush, así que insertar padre+hijo en una sola transacción sin `flush()` intermedio puede violar FK aunque ambos objetos ya estén en la sesión.

### T036 — Persistence tests
**Estado:** DONE
**Dep:** T035  
CRUD, FK, transacciones, rollback, append-only y migraciones.

**Nota:** CRUD/FK/append-only/migraciones ya cubiertos por T027/T033/T034/T035. Añadido `tests/persistence/test_transactions.py`: rollback explícito, rollback automático por excepción antes de commit, persistencia entre sesiones, rollback conjunto multi-tabla (goal+concept+evidence) cuando una FK falla a mitad de transacción, y verificación de que evidence acumula (nunca sobrescribe) a través de escrituras secuenciales. 202 tests backend en total.

---

# Fase 3 — Obsidian

### T037 — Vault resolver
**Estado:** DONE
**Dep:** T013  
Validar root y bloquear path traversal fuera del vault.

**Nota:** `app/obsidian/vault_resolver.py`. Falla rápido en construcción si el root no existe/no es directorio/no es legible (distinto del check "suave" de `onboarding_scan.py`, que muestra errores en la UI en vez de lanzar). `resolve()` bloquea tanto `../` como inyección de rutas absolutas (un solo `relative_to()` cubre ambos, por cómo pathlib ancla rutas absolutas al unir).

### T038 — Markdown scanner
**Estado:** DONE
**Dep:** T037  
Scan recursivo read-only; ignorar `.obsidian/`.

**Nota:** `app/obsidian/markdown_scanner.py`, sobre `VaultResolver`. Ignora también `Attachments/`/`Templates/` por defecto (configurable), tal como `OBSIDIAN_SCHEMA.md` §14 documenta como default. Este scanner alimenta el índice de vault (T042); el scan resumido de onboarding (`onboarding_scan.py`, T025) queda como está — sirve una necesidad distinta (feedback de UI) y ya está probado en navegador real.

### T039 — Frontmatter parser
**Estado:** DONE
**Dep:** T038  
Parseo YAML tolerante a errores sin abortar todo el scan.

**Nota:** `app/obsidian/frontmatter.py`, usa `yaml.safe_load` (nunca `load`). Nunca lanza excepción — YAML mal formado, bloque sin cerrar o frontmatter no-mapping se reportan vía `error`, dejando `body` con el contenido original intacto para no perder texto. `pyyaml` añadido como dependencia explícita (antes solo transitiva vía alembic).

### T040 — Managed sections parser
**Estado:** DONE
**Dep:** T038  
`get_section`/`replace_section` para marcadores Learning OS.

**Nota:** `app/obsidian/managed_sections.py`. `replace_section` añade la sección si no existe; lanza `ManagedSectionError` si hay BEGIN sin END (en vez de adivinar y arriesgar corromper el archivo). Contenido fuera de marcadores nunca se toca (verificado con test que confirma texto de usuario intacto tras un replace).

### T041 — Hashing
**Estado:** DONE
**Dep:** T038  
SHA-256 por archivo.

### T042 — Vault index
**Estado:** DONE
**Dep:** T034, T041  
Persistir path, hash, tipo, managed ID, metadata, indexed_at y missing.

**Nota:** `app/obsidian/vault_index.py` (`VaultIndexer.reindex()`), sobre `VaultResolver`+scanner+frontmatter+hashing. Corregido gap de esquema (igual que evidence.session_id): `vault_files` no tenía `managed_id`/`metadata_json`/`missing` pese a que T042 los exige explícitamente — añadidos vía migración nueva `017d17b1666e` con `server_default` (columnas NOT NULL sobre ALTER TABLE necesitan default en SQLite). `managed_id` solo se rellena si `managed_by: learning_os` está en el frontmatter. Archivos borrados del disco se marcan `missing=True`, nunca se eliminan de la tabla; reaparecen como `missing=False` si el archivo vuelve.

### T043 — Conflict detection
**Estado:** DONE
**Dep:** T042  
Si hash actual != hash indexado, no escribir y devolver `VAULT_CONFLICT`.

**Nota:** `app/obsidian/conflict_detection.py` (`assert_no_conflict`, `VaultConflictError` — mapea a `VAULT_CONFLICT` de `API_SPEC.md` §11). Sin fila indexada no hay conflicto (archivo nuevo). Archivo indexado pero borrado del disco SÍ es conflicto. Usado por el atomic writer en T044.

### T044 — Atomic writer
**Estado:** DONE
**Dep:** T040, T043  
Temp file mismo directorio → flush → atomic replace → reread → verify.

**Nota:** `app/obsidian/atomic_writer.py` (`write_note`). Comprueba conflicto (T043) antes de escribir, escribe vía temp file + `os.replace` (mismo patrón que `ConfigStore` de T034), relee y verifica byte-a-byte, y actualiza el índice de vault (T042) con el nuevo hash. Verificado: escritura en conflicto nunca toca el archivo (la edición externa sobrevive intacta), sin ficheros temporales residuales, y bloqueo de path traversal heredado de `VaultResolver`.

### T045 — Diff engine
**Estado:** DONE
**Dep:** T044  
Diff before/after legible para UI.

**Nota:** `app/obsidian/diff_engine.py` (`generate_diff`), sobre `difflib` de stdlib. Devuelve dos formas: `unified` (texto estándar para mostrar tal cual) y `lines` (desglose línea a línea tipado equal/added/removed, para una UI custom inline/side-by-side). Sin dependencias nuevas.

### T046 — Change proposals
**Estado:** DONE
**Dep:** T045  
Estados `pending/approved/rejected/applied/conflicted/failed`; operaciones limitadas.

**Nota:** Gap de esquema igual que evidence.session_id y vault_files — `DATABASE_SCHEMA.md` nunca listaba `change_proposals` pese a que `SPECS.md` §16, `AI_CONTRACTS.md` §9 y `API_SPEC.md` §2 describen el flujo exacto. Añadida tabla vía migración nueva `b9c38d0c7cf0`. `app/obsidian/change_proposal.py`: enums `ProposalOperation` (4 valores, `AGENTS.md` §6) y `ProposalStatus` (6 valores) + `ChangeProposalRepository`. Aplicar una propuesta aprobada (T083) queda fuera de alcance — esto solo modela y persiste la propuesta.

### T047 — Obsidian tests
**Estado:** DONE
**Dep:** T037–T046  
Vault vacío/existente, malformed frontmatter, cambios externos, conflictos y preservación de texto del usuario.

**Nota:** `tests/obsidian/test_integration.py` consolida T037–T046 sobre un vault realista (nota simple + nota gestionada con secciones managed + prosa de usuario + frontmatter malformado). Cubre: vault vacío, vault mixto, frontmatter roto no aborta el scan del resto, cambio externo bloquea escritura sin tocar el archivo, y flujo completo propuesta→diff→aprobación→escritura→verificación con texto de usuario intacto y hash de índice actualizado. Fase 3 (Obsidian) completa — 292 tests backend en total.

---

# Fase 4 — AI

### T048 — Pydantic AI contracts
**Estado:** DONE
**Dep:** T010  
Implementar Planner, Diagnostic, Tutor, Exercise, Evaluator, Curator y Progress responses.

**Nota:** `app/ai/contracts.py`, las 7 respuestas de `AI_CONTRACTS.md` §4–10. Reutiliza `ExerciseType`/`FiveLevelScale`/`NormalizedScore` del dominio en vez de reinventar tipos. Refactor previo: `ProposalOperation` movido de `app.obsidian.change_proposal` a `app.domain.enums` (con re-export desde su ubicación original) para que `app.ai` (Curator) y `app.obsidian` compartan el mismo enum sin que una capa dependa de la otra. `roadmap_nodes`/`roadmap_edges` del Planner quedan como `list[dict]` — el spec no define su forma exacta, así que no se inventa una estructura.

### T049 — AI orchestrator
**Estado:** DONE
**Dep:** T048, T017  
Punto único para provider calls y `ai_runs`.

**Nota:** `app/ai/orchestrator.py` (`AIOrchestrator.generate`). Registra cada llamada en `ai_runs` — éxito y fallo — con latencia, hash de input (SHA-256, nunca el contenido crudo) y nombre del schema de respuesta; nunca guarda prompt/respuesta reales (`AI_CONTRACTS.md` §14). Reenvía la excepción original tras loguear el fallo.

### T050 — MockProvider
**Estado:** DONE
**Dep:** T048  
Respuestas deterministas para éxito, error, parcialidad, misconceptions y confidence.

**Nota:** `app/ai/adapters/mock_scenarios.py`, sobre el `MockProvider` genérico de T017. `AI_CONTRACTS.md` §8 no tiene campo "confidence" en `EvaluatorResponse` — se interpretó como escenarios de calibración de confianza (`ProgressResponse.calibration`, ya que ese SÍ tiene overconfidence/underconfidence): `progress_overconfident`/`progress_underconfident`/`progress_well_calibrated`. Factories deterministas verificadas con test explícito de determinismo (misma llamada, mismo resultado).

### T051 — OllamaProvider
**Estado:** DONE
**Dep:** T017  
Endpoint configurable, default local `http://localhost:11434`.

**Nota:** `app/ai/adapters/ollama.py`. Protocolo nativo `/api/chat` (no el shim OpenAI-compatible de Ollama), usando su propio soporte de structured output vía `format: <json schema>`.

### T052 — OpenAIProvider
**Estado:** DONE
**Dep:** T017  
API key segura, model configurable y structured output.

**Nota:** `app/ai/adapters/openai.py`, sobre la base compartida `_openai_compatible_base.py` (Chat Completions + `response_format: json_schema`).

### T053 — AnthropicProvider
**Estado:** DONE
**Dep:** T017  
Protocolo Anthropic nativo para Claude.

**Nota:** `app/ai/adapters/anthropic.py`. Messages API nativa, no la base OpenAI-compatible (`AGENTS.md` §20). Structured output vía tool use forzado (`tool_choice`) — patrón documentado de Anthropic para output fiable.

### T054 — OpenRouterProvider
**Estado:** DONE
**Dep:** T017  
Endpoint y model configurables.

**Nota:** `app/ai/adapters/openrouter.py`, sobre la base compartida (mismo wire format que OpenAI).

### T055 — NvidiaNimProvider
**Estado:** DONE
**Dep:** T017  
API key, endpoint y model configurables.

**Nota:** `app/ai/adapters/nvidia_nim.py`, sobre la base compartida; sin `base_url` por defecto (NIM puede ser self-hosted).

### T056 — OpenAICompatibleProvider
**Estado:** DONE
**Dep:** T017  
`base_url`, model y API key opcional.

**Nota:** `app/ai/adapters/openai_compatible.py`, sobre la base compartida. `_openai_compatible_base.py` (T052/T054/T055/T056 comparten esta implementación — mismo wire format Chat Completions; Ollama y Anthropic usan protocolos nativos propios). Probado con `httpx.MockTransport` (sin credenciales reales) por cada camino: éxito, error HTTP, JSON malformado, schema no coincidente y ausencia de campos esperados. Validación contra APIs reales en vivo queda para T122 (`AGENTS.md` §17: el suite normal no depende de un modelo externo).

### T057 — Retry policy
**Estado:** DONE
**Dep:** T049  
`validate → retry once → fallback → surface failure`; invalid output nunca muta estado.

**Nota:** `app/ai/retry_policy.py` (`RetryingProvider`, satisface `AIProvider` — compone de forma transparente con `AIOrchestrator`). Reintento incluye el error de validación en `constraints.previous_validation_error` para que el modelo pueda autocorregirse. Fallo de red (`AIProviderUnavailableError`) va directo a fallback sin reintento (no hay error de validación que reenviar). Si todo falla, se relanza la excepción original — nunca se devuelve un resultado sin validar.

### T058 — Prompt versioning
**Estado:** DONE
**Dep:** T049  
Crear `planner.v1`, `diagnostician.v1`, `tutor.v1`, `exercise_generator.v1`, `evaluator.v1`, `curator.v1`.

**Nota:** `app/ai/prompts.py`. Progress analyst no tiene versión (`AI_CONTRACTS.md` §10 no muestra un `prompt_version` de ejemplo, y T058 solo pide estos 6). Conectado de verdad: `_prompt.py` (usado por todos los adapters) busca la plantilla por `request.prompt_version` y usa sus instrucciones específicas de la tarea; si la versión no existe, degrada con un prompt genérico en vez de fallar. Política de versionado: nunca editar una versión publicada — añadir `tutor.v2`, etc.

### T059 — AI security tests
**Estado:** DONE
**Dep:** T050, T057  
Prompt injection desde vault se trata como datos; probar output inválido y provider unavailable.

**Nota:** `tests/ai/test_security.py`. Tres bloques: (1) inyección como datos — `system_prompt()` se deriva solo de `role`+`prompt_version` vía `PROMPT_REGISTRY`, nunca de `context`/`goal`/`task`/`constraints`, así que un payload de inyección puesto ahí nunca aparece en el system prompt; `user_prompt()` serializa con `json.dumps`, así que un payload que intenta romper la sintaxis JSON (comillas, llaves) queda contenido como valor string dentro de su campo, verificado con roundtrip `json.loads`. (2) Output inválido — reutiliza `AIOrchestrator`+`_AlwaysWrongShapeProvider` para confirmar que un fallo de validación se loguea en `ai_runs` con `success=False` y nunca se coacciona a una respuesta válida; test adicional confirma que Pydantic ignora atributos extra por construcción (no hay riesgo de inyección de atributos arbitrarios). (3) Provider unavailable — `RetryingProvider` con primary+fallback caídos re-lanza el error original en vez de fabricar cualquier dato por defecto.

---

# Fase 5 — Learning engine

### T060 — Context builder
**Estado:** DONE
**Dep:** T035, T038  
Seleccionar contexto por goal, concept, prerequisites, mistakes y práctica; nunca vault completo por defecto.

**Nota:** `app/services/context_builder.py` (`ContextBuilder.build(goal_id, concept_id)` → `list[dict]` apto para `AIRequest.context`). Señales implementadas de `AI_CONTRACTS.md` §12: goal, concept, prerequisite relationship, recent mistakes, recent practice (semantic similarity queda fuera del MVP — no hay infraestructura de embeddings). Sin dependencia de `VaultPort`: por diseño nunca puede tirar del vault completo. Mistakes filtra `resolved_at is None` y ordena por `last_seen` desc; practice (evidence) ordena por `timestamp` desc; ambos con cap configurable (`max_mistakes`, `max_recent_evidence`, `max_prerequisites`, default 5). Gap descubierto e implementado en el camino: `concept_relations` (tabla y `ConceptRelationModel` ya existían desde T033/migración inicial) no tenía puerto ni repositorio — añadido `ConceptRelationRepository` a `app/domain/ports.py` (`add`, `list_prerequisites_of`) y `SqlConceptRelationRepository`, con tests de repositorio dedicados en `tests/persistence/repositories/test_concept_relation.py`.

### T061 — Mastery engine
**Estado:** DONE
**Dep:** T035, T048  
Aplicar fórmula configurable de `DOMAIN_MODEL.md`; AI no asigna mastery directamente.

**Nota:** `app/services/mastery_engine.py`. `MasteryEngine.compute(concept) -> Concept` aplica la fórmula de `DOMAIN_MODEL.md` §18 sobre `Evidence` (nunca sobre output de AI). `MasteryWeights` (dataclass, pesos configurables inyectables, valida que sumen 1.0) con los defaults documentados. `recent_performance`/`historical_performance` se derivan de `evidence.correctness` (ventana de las últimas N evidencias vs. todo el histórico, N=5 configurable); `transfer_performance`/`independence` de sus campos homónimos en `Evidence`; `retention` viene de `Concept.retention` actual (no existe campo de retención en `Evidence`) normalizado a 0..1. Campos `None` en evidencia se excluyen del promedio (no cuentan como 0). Status derivado de `DOMAIN_MODEL.md` §17: sin evidencia → `unknown`; `recent_performance < 0.4` → `weak` (anula el tier de mastery, sea cual sea); si no, tiers `learning/developing/usable/strong/mastered` por umbrales de mastery. `needs_review` queda fuera de este motor — depende del scheduler de reviews (T063), no de mastery. No persiste nada — devuelve una copia del `Concept`; guardar es responsabilidad del caller vía `ConceptRepository.update()`.

### T062 — Mistake tracker
**Estado:** DONE
**Dep:** T035  
Agrupar misconceptions normalizadas y contar recurrencia.

**Nota:** `app/services/mistake_tracker.py`. `MistakeTracker.record(concept_id, goal_id, description, type=MISCONCEPTION, severity=MEDIUM) -> Mistake`. La AI solo da texto libre (`EvaluatorResponse.misconceptions: list[str]`, `AI_CONTRACTS.md` §8), así que la misma misconception recurrente puede venir con distinto wording entre intentos — `normalize()` (minúsculas, sin puntuación, whitespace colapsado) antes de comparar contra las `Mistake` existentes del concepto; sin infraestructura de embeddings (misma decisión que T060), el match es exacto sobre el texto normalizado, no fuzzy/semántico. Si hay match: incrementa `occurrences`, actualiza `last_seen`, y reabre (`resolved_at=None`) si estaba resuelto — una recurrencia es evidencia de que no estaba realmente resuelto. Si no hay match: crea `Mistake` nueva vía `IdGeneratorPort`/`ClockPort` (ports ya existían desde T032, sin adapter concreto aún — se añadirá cuando algo los cablee de verdad, probablemente Fase 6).

### T063 — Review scheduler
**Estado:** DONE
**Dep:** T061  
Scheduler MVP determinista; dejar interfaz preparada para FSRS.

**Nota:** `app/services/review_scheduler.py`. `SchedulingStrategy` (Protocol) es el punto de swap para T130 (FSRS, Fase 13) — recibe el `Review` previo completo (no solo `interval_days`), así una futura `FsrsScheduler` puede leer `previous.stability`/`previous.difficulty` (campos ya existentes en la entidad `Review`, sin usar por esta strategy MVP) sin cambiar la interfaz ni el código que la llama. `SimpleSpacedRepetitionScheduler` (default, `SPECS.md` §17 "MVP uses simple spaced repetition"): determinista — sin review previa usa `INITIAL_INTERVAL_DAYS=1.0`; con `correctness >= SUCCESS_THRESHOLD(0.6)` dobla el intervalo anterior (cap `MAX_INTERVAL_DAYS=180.0`); si no, resetea a `MIN_INTERVAL_DAYS=1.0`. `ReviewScheduler.schedule_next(...)` no persiste — devuelve el próximo `Review` (status `scheduled`); guardar es responsabilidad del caller vía `ReviewRepository.add()`. Los umbrales/constantes son valores MVP razonables sin más guía normativa específica en los docs; documentados aquí por si se ajustan en Fase 6+.

### T064 — Activity selector
**Estado:** DONE
**Dep:** T061–T063  
Priorizar importance, weakness, prerequisite, review, mistakes y transfer; exponer breakdown.

**Nota:** `app/services/activity_selector.py`. `ActivitySelector.rank(goal_id) -> list[ActivityCandidate]` (`concept_id`, `score`, `breakdown: dict[str, float]`) ordenada descendente. Implementa la fórmula de `DOMAIN_MODEL.md` §19 (`importance * weakness * prerequisite_factor * review_factor * mistake_factor * transfer_factor`) con un refinamiento documentado y permitido por el propio spec ("may refine the formula"): cada factor tiene un piso `MIN_FACTOR=0.1` en vez de poder llegar a 0, así un solo factor no anula por completo la prioridad (ej. un concepto ya `mastered` con review vencido no debería desaparecer del ranking solo por `weakness≈0`). `weakness=1-mastery/5`; `prerequisite_factor` = mastery medio de los prerequisites (`ConceptRelationRepository`, T060) /5, neutral (1.0) si no hay prerequisites; `review_factor` neutral si no hay `next_review`, piso si aún no toca, crece con días de retraso (cap `REVIEW_OVERDUE_CAP=3.0`); `mistake_factor` cuenta solo mistakes sin resolver (cap `MISTAKE_FACTOR_CAP=2.0`); `transfer_factor` = 1 - promedio de `evidence.transfer` (piso si ya hay buen transfer, neutral sin evidencia). El breakdown completo viaja en cada `ActivityCandidate`, así el ranking siempre es explicable (no un score opaco), cumpliendo el requisito explícito de `DOMAIN_MODEL.md` §19.

### T065 — Goal application service
**Estado:** DONE
**Dep:** T035, T060  
Crear goal y contexto inicial sin modificar vault automáticamente.

**Nota:** `app/services/goal_service.py`. `GoalApplicationService.create_goal(...) -> LearningGoal`: siempre crea en estado `draft` (`DOMAIN_MODEL.md` §17), genera `id`/timestamps vía `IdGeneratorPort`/`ClockPort`, persiste vía `GoalRepository.add()`. "Contexto inicial" en este punto es solo el propio registro del goal — concepts/roadmap no se crean aquí, vienen del pipeline diagnóstico (T066-T068), que es justo lo que el orden de dependencias de `TASKS.md` refleja. La restricción "sin modificar vault automáticamente" se aplica arquitectónicamente, no por convención: el servicio ni siquiera recibe un `VaultPort` en su constructor, así que no hay manera de que toque el vault por accidente (verificado con test de introspección sobre la firma de `__init__`). Valida `title` no vacío (`InvalidGoalError`) — única invariante de `DOMAIN_MODEL.md` §3 aplicable en creación.

### T066 — Diagnostic service
**Estado:** DONE
**Dep:** T048, T060, T065  
Recall + application + transfer; generar evidence.

**Nota:** `app/services/diagnostic_service.py`. `DiagnosticService.generate_items(goal_id, concept_ids) -> list[DiagnosticItem]` llama al rol `diagnostician` (`AI_CONTRACTS.md` §5, `prompt_version="diagnostician.v1"`) con contexto fusionado de `ContextBuilder` (T060) para todos los concepts pedidos (un solo item "goal" deduplicado + items "concept"/prerequisite/mistake/practice por cada concept_id) — la AI solo propone preguntas, nunca las califica. `DiagnosticService.record_response(...) -> Evidence` recibe una respuesta ya calificada (`correctness` puesto por el caller, ej. vía Evaluator) y genera `Evidence` con `source_type=assessment` (no existe un `EvidenceSourceType.diagnostic` explícito — `Assessment.type=diagnostic` en `DOMAIN_MODEL.md` §15 confirma que un diagnóstico ES un tipo de assessment). Decisión de mapeo no explícita en los docs, documentada aquí: `evidence_type="application"` también puebla `reasoning`, `evidence_type="transfer"` también puebla `transfer` (mismo nombre de campo) — así el motor de mastery (T061) y el activity selector (T064) reciben señal real de estos diagnósticos, no solo de `correctness`. `question`/`evidence_type` viajan en `evidence.metadata` para trazabilidad. Requiere `activity_id` real — igual que T035, asume que existe una Session (`mode=assessment`) + Activity ya creadas por el flujo que invoque el diagnóstico (Fase 6+); este servicio no crea sesiones. No se creó tabla/repositorio para `Assessment`/`AssessmentAttempt` (documentados en `DOMAIN_MODEL.md` §15 pero sin tabla en `DATABASE_SCHEMA.md` ni migración) — el MVP no los necesita, ya que el resultado observable del diagnóstico es la Evidence generada, no un registro de assessment separado; se añadirán si una fase posterior los requiere explícitamente.

### T067 — 80/20 planner
**Estado:** DONE
**Dep:** T066  
High leverage concepts, deferred topics y foco diagnóstico.

**Nota:** `app/services/planner_service.py`. `PlannerService.plan(goal_id) -> PlanningResult` (`high_leverage_concepts`, `deferred_topics`, `diagnostic_focus` — los 3 campos que pide el texto de la tarea). Llama al rol `planner` (`AI_CONTRACTS.md` §4, `prompt_version="planner.v1"`) con input `goal`/`user level`/`existing knowledge`/`target outcome`/`available time` armado directamente desde `GoalRepository`+`ConceptRepository` (sin `ContextBuilder`, T060, porque para un goal nuevo aún no hay ningún concept del que construir contexto — "existing knowledge" es la lista de concepts ya vinculados al goal, vacía si es nuevo). `PlannerResponse` trae también `roadmap_nodes`/`roadmap_edges`, pero este servicio no los usa ni persiste nada — convertir esa propuesta en `Concept`/`ConceptRelation`/`Roadmap` reales con validación de IDs/self-relations/ciclos es exactamente el trabajo de T068 (Roadmap service), que corre después. Este servicio es de solo-lectura: no depende de T060 ni T065 en el código porque no construye contexto ni crea el goal, solo lo consulta.

**Corrección (T079):** `PlanningResult` inicialmente NO incluía `roadmap_nodes`/`roadmap_edges` (solo los 3 campos filtrados). Al construir el E2E de T079 quedó claro que sin ellos ningún caller podía encadenar planner→roadmap desde una sola llamada a la AI — habría hecho falta una segunda llamada redundante solo para recuperar esos campos. Añadidos como pass-through sin validar (`list[dict]`, igual que en `PlannerResponse`); la validación/traducción a `RoadmapNode`/`RoadmapEdge` sigue siendo responsabilidad del caller (T068 ya lo documentaba así).

### T068 — Roadmap service
**Estado:** DONE
**Dep:** T067  
Nodos/dependencias; validar IDs, self-relations y ciclos.

**Nota:** `app/services/roadmap_service.py`. Gap grande encontrado e implementado en el camino: `DATABASE_SCHEMA.md` nunca documentó una tabla `roadmaps`, pese a que `DOMAIN_MODEL.md` §16 ya definía la entidad `Roadmap` (`id`, `goal_id`, `version`, `status`) desde el principio del proyecto — añadida (tabla + `RoadmapModel` + migración `3c9a2ac5a47d`, ciclo upgrade→downgrade→upgrade verificado, `RoadmapRepository` port + `SqlRoadmapRepository`). La tabla NO duplica el grafo (nodos/edges) — "nodes reference concepts and skills, edges contain a relationship type" (`DOMAIN_MODEL.md` §16) ya vive en `goal_concepts` y `concept_relations`; `roadmaps` es solo el marcador de versión activa/superseded. `RoadmapService.build_roadmap(goal_id, nodes: list[RoadmapNode], edges: list[RoadmapEdge]) -> Roadmap` valida primero (`RoadmapValidationError`): ids de nodo duplicados, edges con id desconocido (no está en `nodes`), self-relations (`source==target`), y ciclos (DFS 3-color sobre el grafo dirigido de edges) — ningún dato se escribe si la validación falla. Tras validar: crea o actualiza cada `Concept` (en concepts existentes solo toca `title`/`domain`/`importance`/`updated_at` — nunca `mastery`/`confidence`/`retention`/`status`, que son evidence-derived por `DOMAIN_MODEL.md` §4), enlaza a goal_concepts, añade `ConceptRelation`s (idempotente — no duplica si el edge ya existe, usando el nuevo `list_relations_from` del port), supersede el roadmap activo previo si existe, y crea uno nuevo (`version+1`). `RoadmapNode.domain` cae a `goal.domain` si no se especifica; si ninguno de los dos existe, falla explícitamente en vez de inventar un dominio. Gap secundario encontrado: `ConceptRepository.link_to_goal` existía en `SqlConceptRepository` desde T035 pero nunca se declaró en el port `ConceptRepository` — añadido ahora que un segundo servicio (además del propio repo) lo necesita. `roadmap_nodes`/`roadmap_edges` de `PlannerResponse` (T067) son dicts sin tipar en el contrato de IA; este servicio define y exige su forma concreta (`RoadmapNode`/`RoadmapEdge`) — traducir de uno a otro es responsabilidad del caller (Fase 6+).

---

# Fase 6 — Vertical slice de aprendizaje

### T069 — Session creation
**Estado:** DONE
**Dep:** T065, T068  
Crear sesión, modo y duración.

**Nota:** `app/services/session_service.py`. `SessionApplicationService.create_session(goal_id, mode, duration_minutes, objective=None) -> Session`. `duration_minutes` viene de `API_SPEC.md` §6 (`POST /goals/{goal_id}/sessions` body: `mode`+`duration_minutes`) pero `DATABASE_SCHEMA.md` no tiene columna para ello en `sessions` — se valida (`InvalidSessionError` si no es positivo) pero no se persiste; es input de planificación para T070 (next activity), no estado durable de la sesión. No hay ningún endpoint/tarea de "start session" separado en todo el backlog de Fase 6, así que crear la sesión la arranca directamente: `status=active`, `started_at=now` (no `planned`). `objective` es opcional — si no se da, se deriva del título del goal.

### T070 — Next activity
**Estado:** DONE
**Dep:** T064, T069  
Seleccionar objetivo/actividad y persistirla.

**Nota:** `app/services/next_activity_service.py`. `NextActivityService.select_next(session_id) -> Activity`: valida sesión existe y está `active`, usa `ActivitySelector.rank(goal_id)` (T064) y toma el concept top-1, crea un `Activity` (`type=exercise`, `status=active`, `sequence` = nº de activities existentes de la sesión + 1, `concept_ids=[top]`) y lo persiste. Gap encontrado: `activities` (tabla/`ActivityModel`) existía desde T033 pero no tenía puerto ni repositorio — añadido `ActivityRepository` (`add`/`get`/`list_by_session`/`update`) y `SqlActivityRepository` (empaqueta `concept_ids` en `payload_json`, igual que `SqlExerciseRepository` con sus campos extra). Esta es la selección *inicial* de actividad de una sesión — la readaptación tras cada respuesta (con señales de mastery/mistake/review recién actualizadas) es explícitamente el trabajo de T078 (Adaptive next activity), no de este servicio.

### T071 — Exercise generator
**Estado:** DONE
**Dep:** T048, T070  
Exercise con type, difficulty, concepts, success criteria, hints, solution, mistakes y transfer.

**Nota:** `app/services/exercise_generator_service.py`. `ExerciseGeneratorService.generate(goal_id, concept_id) -> Exercise`. Llama al rol `exercise_generator` (`AI_CONTRACTS.md` §7, `prompt_version="exercise_generator.v1"`) con contexto de `ContextBuilder` (T060) para el concept. `ExerciseGeneratorResponse` no incluye `id`/`goal_id`/`concept_ids` — los asigna este servicio (AI nunca asigna identidad/asociaciones, `AGENTS.md` #5), copiando el resto de campos (`type`, `difficulty`, `prompt`, `success_criteria`, `hints`, `solution`, `common_mistakes`, `transfer_variant`) 1:1 al `Exercise` de dominio y persistiendo vía `ExerciseRepository` (T035, sin cambios). `prerequisite_ids`/`skill_ids` quedan vacíos — la tarea no pide poblarlos y no hay lógica de inferencia de skills todavía.

### T072 — Answer submission
**Estado:** DONE
**Dep:** T071  
Persistir attempt y confidence.

**Nota:** `app/services/answer_submission_service.py`. `AnswerSubmissionService.submit_answer(exercise_id, session_id, answer, confidence) -> ExerciseAttempt`: valida que exercise y session existan y que la session esté `active` (reutiliza `SessionNotFoundError`/`InactiveSessionError` de T070), genera id/timestamp y persiste. Gap encontrado: `exercise_attempts` (tabla/`ExerciseAttemptModel`) existía desde T033 sin puerto ni repositorio — añadido `ExerciseAttemptRepository` (`add`/`get`) y `SqlExerciseAttemptRepository`. Discrepancia de schema notada, no corregida (no bloquea nada): la entidad `ExerciseAttempt` tiene `evaluation_id` pero `exercise_attempts` no tiene esa columna — el FK real va al revés (`evaluations.attempt_id`, `DATABASE_SCHEMA.md` #evaluations); el repositorio siempre devuelve `evaluation_id=None`. Solo persiste el intento crudo — calificarlo es trabajo del Evaluator (T073), no de este servicio.

### T073 — Evaluator
**Estado:** DONE
**Dep:** T048, T072  
Evaluar correctness, reasoning, completeness, independence y transfer.

**Nota:** `app/services/evaluator_service.py`. `EvaluatorService.evaluate(attempt_id) -> Evaluation`. Llama al rol `evaluator` (`AI_CONTRACTS.md` §8, `prompt_version="evaluator.v1"`) con el prompt/solution/success_criteria del exercise + la respuesta/confidence del attempt. Gap encontrado: `evaluations` (tabla/`EvaluationModel`) existía desde T033 sin puerto ni repositorio — añadido `EvaluationRepository` (`add`/`get`, append-only como `Evidence`) y `SqlEvaluationRepository`. `Evaluation.provider`/`model` se rellenan leyendo `AIOrchestrator.provider_name`/`.model` — añadidas como properties públicas del orchestrator (antes privadas) para que un caller pueda sellar la misma procedencia que ya se loguea en `ai_runs` sobre sus propios registros evidenciales. Este servicio solo guarda el juicio de la AI como evidencia inmutable (`DOMAIN_MODEL.md` §9: "AI evaluations are evidence, not absolute truth") — convertirlo en `Evidence` que afecta mastery es trabajo de T074.

### T074 — Evidence creation
**Estado:** DONE
**Dep:** T073  
Convertir evaluación válida en evidence inmutable.

**Nota:** `app/services/evidence_creation_service.py`. `EvidenceCreationService.create_evidence(evaluation_id, activity_id) -> list[Evidence]`. Encadena `Evaluation → ExerciseAttempt → Exercise` para reunir los campos que faltan (`concept_ids`, `goal_id`, `difficulty`, `session_id`). Un exercise puede apuntar a varios concepts (`concept_ids: list[str]`) pero `Evidence` solo tiene un `concept_id` — este servicio genera un `Evidence` por concept (fan-out), todos comparten scores/activity/session. `activity_id` no es derivable de la cadena evaluation→attempt→exercise (ni `ExerciseAttempt` ni `exercise_attempts` lo registran) — lo da el caller, igual que `API_SPEC.md` §6 lo lleva en la URL (`/sessions/{id}/activities/{activity_id}/answer`), no en el attempt. Conversión de escala: `attempt.confidence` es `ConfidencePercent` (0..100) pero `Evidence.confidence` es `NormalizedScore` (0..1) — se divide entre 100. `evaluation.completeness` no tiene equivalente en `Evidence` (solo existe en `Evaluation`) — se queda fuera, correcto por diseño. `metadata` guarda `evaluation_id`/`attempt_id` para trazabilidad.

### T075 — Derived mastery update
**Estado:** DONE
**Dep:** T074, T061  
Recalcular mastery.

**Nota:** `app/services/mastery_update_service.py`. `MasteryUpdateService.update_mastery(concept_id) -> Concept`: wiring mínimo entre `MasteryEngine.compute()` (T061, que nunca persiste por diseño) y `ConceptRepository.update()`. Se llama tras crear Evidence (T074) para reflejar la evidencia nueva en `mastery`/`status`. No toca `last_practiced`/`next_review` — no lo pide el texto de la tarea y `next_review` es responsabilidad del review scheduler (T077).

### T076 — Mistake update
**Estado:** DONE
**Dep:** T074, T062  
Crear/incrementar misconception.

**Nota:** `app/services/mistake_update_service.py`. `MistakeUpdateService.record_from_evaluation(evaluation_id) -> list[Mistake]`: recorre `Evaluation → ExerciseAttempt → Exercise` (mismo patrón que T074) para obtener `goal_id`/`concept_ids`, y delega en `MistakeTracker.record()` (T062) por cada misconception reportada — la normalización/recurrencia ya vive ahí, este servicio solo hace la wiring. Sin misconceptions reportadas devuelve `[]` sin tocar nada. Exercise multi-concept: cada misconception se registra contra TODOS los concepts del exercise (no hay mapeo misconception→concept en `EvaluatorResponse`, que es `list[str]` plano).

### T077 — Review creation
**Estado:** DONE
**Dep:** T075, T063  
Programar review futura.

**Nota:** `app/services/review_creation_service.py`. `ReviewCreationService.schedule_review(concept_id, goal_id, correctness) -> Review`: busca la `Review` completada más reciente del concept (nuevo `ReviewRepository.list_by_concept`, gap encontrado igual que en T073/T074/T076 — tabla/`ReviewModel` ya existían desde T033) como `previous` para `ReviewScheduler.schedule_next()` (T063), y persiste el resultado. Reviews sin completar (`completed_at is None`) se ignoran al buscar "previous" — no representan un ciclo de repaso ya vivido. `correctness` lo pasa el caller (mismo score que produjo el Evaluator, T073) para no repetir un tercer recorrido `Evaluation → ExerciseAttempt → Exercise` (T074 y T076 ya hacen ese recorrido cada uno por su cuenta).

### T078 — Adaptive next activity
**Estado:** DONE
**Dep:** T075–T077  
Seleccionar siguiente actividad con razón explicable.

**Nota:** `app/services/adaptive_activity_service.py`. `AdaptiveActivityService.select_next(session_id, just_completed_concept_id=None) -> AdaptiveActivityResult` (`activity`, `reason: ActivityCandidate`). Reutiliza `ActivitySelector.rank()` (T064) igual que T070 — como lee `Concept`/`Mistake`/`Review` en vivo, automáticamente refleja lo que T075-T077 acaban de escribir tras la respuesta, sin lógica adicional de "refresco". Dos diferencias deliberadas frente a T070 (que se queda como selección inicial de sesión, sin cambios de comportamiento — solo se extrajo `create_and_persist_activity()` a `next_activity_service.py` para compartirla): (1) evita repetir inmediatamente el concept recién trabajado si hay alternativa (un solo punto de evidencia rara vez cambia el ranking, así que sin esto la misma actividad se repetiría); (2) devuelve el `ActivityCandidate` completo (con su breakdown de T064) junto al `Activity` persistido, para que la selección sea explicable de verdad y no un score opaco — cumple literalmente "razón explicable".

### T079 — Core session E2E
**Estado:** DONE
**Dep:** T069–T078  
MockProvider ejecuta goal → diagnostic → roadmap → session → exercise → answer → evaluation → evidence → mastery → mistake → review.

**Nota:** `backend/tests/services/test_core_session_e2e.py`. Un solo test, todo con repos SQL reales sobre un engine SQLite real (no fakes) + `MockProvider` configurado para los 4 roles usados (`diagnostician`, `planner`, `exercise_generator`, `evaluator`). Narrativa: `select_basics` se siembra directamente como "conocimiento existente" (no existe un servicio de import de concepts todavía) — el diagnóstico lo evalúa primero, y el planner propone `window_functions` como concept nuevo de alto leverage construyendo sobre ese conocimiento (coincide con `AI_CONTRACTS.md` §4, "existing knowledge" es input real del planner) — así el orden literal del texto de la tarea (diagnostic antes que roadmap) se cumple sin contradecir que `DiagnosticService` necesita un concept ya persistido (nota de T066). El diagnóstico corre en su propia sesión/activity `mode=assessment` de corta vida (sembrada directo, sin pasar por `SessionApplicationService`) porque en este punto la sesión principal (T069) aún no existe. Corrección hecha aquí y aplicada retroactivamente a T067: `PlanningResult` no exponía `roadmap_nodes`/`roadmap_edges`, así que nada podía encadenar planner→roadmap con una sola llamada a IA — añadidos como pass-through. El resto del flujo usa exactamente los servicios de T069-T078 en orden, terminando con `AdaptiveActivityService.select_next()` para demostrar que el loop continúa. Verificado: 544 tests, ruff y mypy limpios.

---

# Fase 7 — Consolidación Obsidian

### T080 — Curator service
**Estado:** DONE
**Dep:** T074, T046, T058  
Generar propuesta de conocimiento.

**Nota:** `app/services/curator_service.py`. `CuratorService.propose(goal_id, concept_id, session_outcome=None) -> list[CuratorOperation]`. Único rol de IA que toca el vault de verdad (vía `VaultResolver`, solo lectura) — el resto de servicios (T060-T078) nunca lo tocan. Input según `AI_CONTRACTS.md` §9 (proposed changes, target note, current note, evidence, session outcome): `target_note` = `concept.obsidian_path` o `f"{concept.id}.md"` si aún no tiene uno; `current_note` = contenido real del archivo (string vacío si el archivo no existe todavía — caso "crear nota nueva"); evidencia reciente (cap `MAX_RECENT_EVIDENCE=5`) como contexto; `session_outcome` lo pasa el caller (no existe todavía un resumidor de sesión). Devuelve las operaciones SIN validar ni persistir — `CuratorResponse` documenta explícitamente que "the application validates every operation" antes de convertirse en `ChangeProposal`, y eso es T081, no este servicio.

### T081 — Proposal validator
**Estado:** DONE
**Dep:** T080  
Validar operation, path, section, concept ID y límites.

**Nota:** `app/services/proposal_validator.py`. `ProposalValidator.validate_and_persist(operations: list[CuratorOperation], concept: Concept) -> ValidationResult` (`accepted: list[ChangeProposal]`, `rejected: list[RejectedOperation]` con motivo). "operation" como enum ya lo valida el schema de `CuratorOperation` antes de llegar aquí (un valor inválido nunca pasaría de `AIInvalidOutputError`/T057) — lo que sí valida este servicio: `path` resuelve dentro del vault (reusa `VaultResolver`, sin traversal), no apunta a un directorio ignorado (`.obsidian/`/`Attachments/`/`Templates/`, mismo set que `markdown_scanner.DEFAULT_IGNORED_DIRS`), y termina en `.md`; "concept ID" se interpreta como que el path debe pertenecer de verdad al concept que se curó (coincide con `concept.obsidian_path` si existe, o con la convención `f"{concept.id}.md"` de `CuratorService` si no); `section` es obligatoria solo para `replace_managed_section`; límites `MAX_CONTENT_LENGTH=20000` y `MAX_OPERATIONS_PER_BATCH=20` (valores MVP razonables, sin cifra normativa en los docs). Las operaciones rechazadas se descartan, no se persisten — no son lo mismo que un `ChangeProposal` con `status=rejected` (eso es un humano rechazando un diff válido que sí llegó a existir).

### T082 — Diff approval API
**Estado:** DONE
**Dep:** T081  
Aprobar/rechazar propuestas.

**Nota:** `app/services/diff_approval_service.py`. `DiffApprovalService.approve(proposal_id)`/`.reject(proposal_id) -> ChangeProposal`: transición `pending → approved`/`pending → rejected` vía `ChangeProposalRepository.update_status()` (T046). "API" aquí es la capa de aplicación, no una ruta HTTP — `API_SPEC.md` §2 solo expone `apply`/`reject` como rutas (sin `/approve` separado) y esas rutas HTTP en sí son Fase 10 (T096-T108), todavía no construida. Solo se puede aprobar/rechazar una propuesta en `pending` — cualquier otro estado (`approved/rejected/applied/conflicted/failed`) levanta `InvalidProposalStatusError`, ya que son transiciones ya decididas.

### T083 — Apply approved change
**Estado:** DONE
**Dep:** T082, T044  
Escribir solo tras aprobación.

**Nota:** `app/services/apply_change_service.py`. `ApplyChangeService.apply(proposal_id) -> ChangeProposal`: exige `status=approved` (`ProposalNotApprovedError` si no) — nunca escribe una propuesta meramente `pending`. Calcula el contenido final según operación: `create_file` (falla si el path ya existe — nunca sobreescribe silenciosamente), `replace_managed_section` (`managed_sections.replace_section`, que ya maneja archivo/sección ausente creándola), `update_frontmatter` (reemplaza el bloque YAML completo, preserva el body vía `parse_frontmatter` — no existe un serializador de frontmatter que preserve comentarios/formato, eso es alcance mayor que "aplicar un cambio aprobado"), `add_link` (añade `proposal.content` como línea nueva al final, tal cual lo vio y aprobó el usuario en el diff). La escritura real (conflicto, atomic replace, reread-verify, índice) es enteramente `write_note` de T044 — este servicio solo decide QUÉ escribir y reacciona al resultado: `VaultConflictError` → `status=conflicted`, `AtomicWriteVerificationError` o error de cómputo de contenido → `status=failed`, éxito → `status=applied`.

### T084 — Verify write
**Estado:** DONE
**Dep:** T083  
Releer, verificar contenido y actualizar índice.

**Nota:** `app/services/write_verification.py`. Releer/verificar-bytes/actualizar-índice ya es exactamente lo que hace `write_note` (T044) — `verify_write(proposal, written_content)` es una segunda comprobación, independiente y semántica: reparsea el contenido ya escrito (que `write_note` ya garantizó que coincide byte a byte con lo calculado) a través de los MISMOS helpers que el resto de la app usa para leer una nota (`get_section`/`parse_frontmatter`), por tipo de operación — detecta un bug en CÓMO se calculó el contenido nuevo (T083's `_compute_content`), no en cómo se escribió a disco. Cableado dentro de `ApplyChangeService.apply()` justo después de `write_note()`: si falla, `status=failed` igual que un fallo de verificación byte-a-byte. Camino de fallo real y alcanzable (no forzado): YAML mal formado en `proposal.content` para `update_frontmatter` pasa el validador de T081 (no parsea YAML) pero lo atrapa esta verificación tras escribirse.

### T085 — Knowledge E2E
**Estado:** DONE
**Dep:** T080–T084  
Session → proposal → diff → approval → Markdown actualizado sin perder texto.

**Nota:** `backend/tests/services/test_knowledge_e2e.py`. Vault real en disco + engine SQLite real + `MockProvider` para `curator`. Nota inicial con texto escrito a mano fuera de cualquier managed section (código de ejemplo, preguntas) — la aserción final confirma que sigue intacto tras aplicar. Corrección hecha aquí: `ApplyChangeService._compute_content` (privado) pasó a `compute_content` (público, sin efectos secundarios — solo lee) porque no había forma de previsualizar el diff de una propuesta `pending` sin ese método; el paso "diff" de este E2E (`generate_diff(before, after)` antes de aprobar) es precisamente lo que necesita. Flujo completo: `CuratorService.propose` (T080) → `ProposalValidator.validate_and_persist` (T081) → diff preview vía `compute_content`+`generate_diff` → `DiffApprovalService.approve` (T082) → `ApplyChangeService.apply` (T083, que internamente corre `verify_write` de T084) → `status=applied` y Markdown final con la sección nueva y todo el contenido humano preservado.

---

# Fase 8 — Reviews y transferencia

### T086 — Today's reviews
**Estado:** DONE
**Dep:** T063, T077  
Query de reviews vencidas.

**Nota:** `app/services/todays_reviews_service.py`. `TodaysReviewsService.list_today() -> list[Review]`. `ReviewRepository.list_due(before)` (T035) solo filtra por `scheduled_at`, no por status — una review `completed`/`skipped` cuyo `scheduled_at` ya pasó seguiría "matcheando". Este servicio añade el filtro que falta: solo `scheduled`/`overdue` (los dos estados "todavía no resueltos") cuentan como "vencida hoy". No transiciona nada a `overdue` — eso sería un efecto secundario dentro de una query de solo lectura; `API_SPEC.md` §7 (`GET /reviews/today`) no lo pide.

### T087 — Review completion
**Estado:** DONE
**Dep:** T086  
Responder, evaluar y reprogramar.

**Nota:** `app/services/review_completion_service.py`. `ReviewCompletionService.complete_review(review_id, activity_id, answer, confidence) -> ReviewCompletionResult` (`completed_review`, `evidence`, `next_review`). `Review` no tiene exercise/prompt propio (`DOMAIN_MODEL.md` §11), así que "evaluar" no puede reusar el rol Evaluator (T073, que necesita prompt/solution/success_criteria reales) — se auto-reporta: `EvidenceSourceType.REVIEW` es su propia fuente dedicada, y `correctness = confidence/100` directamente (la confianza del usuario en su propio recall). Orden importa: marca la review vieja `completed` (con `completed_at`) ANTES de llamar a `ReviewCreationService.schedule_review()` (T077, reusado sin cambios) — así su búsqueda de "previous review completada" encuentra justo la que se acaba de completar y crece el intervalo desde ahí. `Evidence.difficulty` no tiene fuente natural en una review (el `difficulty` de `Review` es el parámetro FSRS, escala distinta, siempre `None` bajo el scheduler MVP) — usa `DEFAULT_REVIEW_DIFFICULTY=3` como valor medio razonable. `answer` se guarda en `evidence.metadata`, no se usa para calificar.

### T088 — Retention update
**Estado:** DONE
**Dep:** T087  
Usar evidencia de review para retention.

**Nota:** `app/services/retention_update_service.py`. `RetentionUpdateService.update_retention(concept_id) -> Concept`: promedia `correctness` de evidencia `source_type=review` (ventana de las últimas 5, igual patrón que `MasteryEngine`, T061) y la escribe como `Concept.retention` (0..100). Solo evidencia de tipo review cuenta — deliberado: retention mide "cuánto se recuerda tras un hueco sin practicar", justo lo que mide un review espaciado, a diferencia de un exercise normal (que mide aplicación inmediata). Cierra el círculo con T061: `MasteryEngine` ya lee `Concept.retention` como uno de sus 5 inputs, pero nada lo escribía hasta ahora. Sin evidencia de review, deja el concept sin tocar (no persiste) — la retención decayendo con el tiempo sin evidencia no está modelada aquí, así que no tiene sentido escribir un valor arbitrario cuando no hay señal.

### T089 — Transfer assessment
**Estado:** DONE
**Dep:** T068, T073  
Generar situaciones nuevas, no copias del ejercicio.

**Nota:** `app/services/transfer_assessment_service.py`. `TransferAssessmentService.generate_transfer_scenario(goal_id, concept_id) -> Exercise`. No hay rol de IA dedicado a "transfer" entre los 7 de `AI_CONTRACTS.md` — reusa `exercise_generator` (T071, `prompt_version="exercise_generator.v1"`) pero mete en `task` los prompts de los exercises previos del concept (`ExerciseRepository.list_by_concept`, gap encontrado — no existía, añadido igual que otros repos de esta fase) como contenido a NO repetir, más una instrucción explícita pidiendo transferir a un contexto nuevo. Gap documentado igual que en T066: no existe tabla `Assessment`/`AssessmentAttempt` (`DOMAIN_MODEL.md` §15 la describe, `DATABASE_SCHEMA.md` nunca la tuvo) — el MVP no la necesita aquí tampoco, el artefacto observable es el `Exercise` generado + la `Evidence` que T090 producirá al calificarlo, no un registro de assessment separado.

### T090 — Assessment completion
**Estado:** DONE
**Dep:** T089  
Evaluar transferencia e independencia.

**Nota:** `app/services/assessment_completion_service.py`. `AssessmentCompletionService.complete_assessment(exercise_id, session_id, activity_id, answer, confidence) -> AssessmentCompletionResult`. Un transfer scenario ES un `Exercise` normal (T089 lo persiste igual que cualquier otro), así que calificarlo no necesita lógica nueva — encadena exactamente el pipeline ya construido: `AnswerSubmissionService` (T072) → `EvaluatorService` (T073) → `EvidenceCreationService` (T074). Lo que añade T090: convierte los scores crudos `transfer`/`independence` (ya presentes en toda evaluación, `AI_CONTRACTS.md` §8, no específicos de transfer) en un juicio explícito, con umbral, medible — `transfer_demonstrated`/`independence_demonstrated` (bool, umbral `0.6`, mismo valor que `ReviewScheduler.SUCCESS_THRESHOLD` de T063 — una sola barra "suficientemente bueno" consistente en el código en vez de un segundo número arbitrario). Responde directamente al texto de T091: "una transferencia posterior MEDIBLE", no un score enterrado dentro de un `Evaluation`.

**Fix posterior (mismo T090):** `create_evidence` (T074) derivaba `source_type` únicamente del `Exercise` subyacente, y `Exercise` no tiene ningún campo que marque "esto es una transfer assessment" (T089 lo persiste como Exercise normal) — así que la Evidence que este servicio producía quedaba siempre `source_type=exercise`, nunca `source_type=assessment`, pese a que ese valor del enum (`EvidenceSourceType.ASSESSMENT`) ya existe y se usa correctamente en `diagnostic_service.py`. Corregido añadiendo un parámetro explícito `source_type: EvidenceSourceType = EvidenceSourceType.EXERCISE` a `EvidenceCreationService.create_evidence` (el default preserva el flujo normal de `AnswerFlowService`, el único otro caller); `AssessmentCompletionService.complete_assessment` pasa `source_type=EvidenceSourceType.ASSESSMENT` explícitamente, ya que es el único punto de la cadena que sabe que se trata de un flujo de assessment. `test_review_transfer_e2e.py` (T091) tenía la aserción `EvidenceSourceType.EXERCISE in sources` para la evidence del transfer assessment — documentaba el bug, no el comportamiento correcto — corregida a `EvidenceSourceType.ASSESSMENT`. Tests nuevos en `test_evidence_creation_service.py` (default a `EXERCISE`, `source_type` explícito respetado, aplicado a cada fila del fan-out) y `test_assessment_completion_service.py` (evidence del pipeline completo trae `source_type=assessment`).

### T091 — Review/transfer E2E
**Estado:** DONE
**Dep:** T086–T090  
Concepto débil genera review y una transferencia posterior medible.

**Nota:** `backend/tests/services/test_review_transfer_e2e.py`. Engine SQLite real + `MockProvider` para `exercise_generator` y `evaluator`. Narrativa: concept `weak` (mastery bajo, `next_review` ya pasado) con una review sembrada directamente (representa que ya se generó por estar débil — la lógica de CUÁNDO programar una review por debilidad es del activity selector, T064, ya cubierto en su propio test) → `TodaysReviewsService` la lista como vencida (T086) → `ReviewCompletionService` la completa con confidence alta, autoreportada (T087) → `RetentionUpdateService` deriva `retention=85.0` de esa misma evidencia (T088) → `TransferAssessmentService` genera un escenario nuevo para el mismo concept (T089) → `AssessmentCompletionService` lo califica y confirma `transfer_demonstrated=True`/`independence_demonstrated=True` (T090). Aserción final: la evidencia del concept incluye tanto `source_type=review` como `source_type=exercise` — cierra el círculo "weak → review → transferencia posterior medible" pedido literalmente por el texto de la tarea. Con esto termina la Fase 8 (Reviews y transferencia).

---

# Fase 9 — Projects

### T092 — Project generation
**Estado:** DONE
**Dep:** T089  
Proyecto práctico vinculado a conceptos.

**Nota:** `app/services/project_generation_service.py`. `ProjectGenerationService.generate_project(goal_id, concept_ids) -> Project`. Gap notablemente más grande que los anteriores: `DATABASE_SCHEMA.md` nunca tuvo tabla `projects` (a diferencia de `Assessment`, `Project` sí necesita persistencia real — vida multi-día, `GET /projects/{id}`, `status` con transiciones) — añadidas `projects`+`project_concepts` (mirror de `exercise_concepts`) vía migración `82877dc3cd7c`, `ProjectRepository`+`SqlProjectRepository`. Corrección de entidad: `Project` no tenía forma de registrar a qué concepts está vinculado pese a que el propio texto de la tarea lo exige ("vinculado a conceptos") — añadido `concept_ids: list[str]` (documentado en `DOMAIN_MODEL.md` §14). Sin rol de IA dedicado a "project" entre los 7 de `AI_CONTRACTS.md` — reusa `exercise_generator` (mismo precedente que T089), con contexto fusionado entre todos los concepts (`_merged_context`, igual patrón que `DiagnosticService`/T066) y una instrucción explícita pidiendo un proyecto práctico multi-paso, no un exercise suelto. Compromiso documentado: `ExerciseGeneratorResponse` no tiene campo `title` (no fue diseñado para proyectos) — se deriva de la primera línea del `prompt`, truncada a `MAX_TITLE_LENGTH=80`; añadir un 8º rol de IA solo para esto habría sido un cambio mayor y más arriesgado a un contrato normativo cerrado de 7. `ProjectTask` (T093) queda fuera de este servicio — el diagrama de entidades lo menciona pero no tiene campos propios en ningún doc; se resuelve como `Activity` con `type=project_task` (el valor ya existe en `ActivityType`), no una tabla nueva.

### T093 — Project tasks
**Estado:** DONE
**Dep:** T092  
Tareas y criterios de éxito.

**Nota:** `app/services/project_task_service.py`. `ProjectTaskService.create_tasks(project_id) -> ProjectTasksResult` (`session`, `tasks: list[Activity]`). Confirma la decisión documentada en T092: `ProjectTask` no es una tabla nueva — es un `Activity` con `type=project_task`, dentro de una `Session` dedicada con `mode=project` (ambos valores de enum ya existían para exactamente esto). Cada `success_criteria` del proyecto se convierte en una tarea 1:1 — T092 reusa `exercise_generator`, que solo devuelve un prompt y una lista de criterios, así que no hay un desglose de tareas generado aparte por la IA, y un criterio de éxito ya es una unidad de trabajo concreta y verificable. `Activity` no tiene campo de texto libre para la descripción — convención: la tarea N corresponde a `project.success_criteria[N-1]` (mismo orden que `Activity.sequence`, 1-based). Efecto secundario razonable: un proyecto `proposed` pasa a `active` al generar sus tareas (mismo patrón que Session/Goal, aunque `Project` no tiene reglas de transición documentadas en `DOMAIN_MODEL.md` §17).

### T094 — Project submission
**Estado:** DONE
**Dep:** T093  
Registrar entregables/evidence.

**Nota:** `app/services/project_submission_service.py`. `ProjectSubmissionService.submit_task(project_id, task_id, deliverable) -> ProjectSubmissionResult` (`task`, `evidence: list[Evidence]`). Marca la task `Activity` como `completed` y crea una `Evidence` por concept (`source_type=project`) con todos los campos de score en `None` — solo registra que se entregó algo, calificarlo (independencia, transferencia) es T095, aparte, igual split que exercises (`AnswerSubmissionService`/T072 vs `EvaluatorService`/T073). `MasteryEngine` (T061) ya ignora campos `None`, así que esta evidencia no calificada es inerte hasta que T095 añada una segunda `Evidence` con scores reales para el mismo concept — nunca sesga nada por sí sola. El texto del deliverable (`Activity` sigue sin campo de texto libre, mismo gap de T093) va a `evidence.metadata`, igual que las respuestas de diagnostic/review (T066, T087).

### T095 — Project evaluation
**Estado:** DONE
**Dep:** T094  
Evaluar independencia y transferencia.

**Nota:** `app/services/project_evaluation_service.py`. `ProjectEvaluationService.evaluate_submission(project_id, task_id, session_id, deliverable) -> list[Evidence]`. `Project` no tiene `Exercise`/`ExerciseAttempt` (ver nota T092), así que `EvaluatorService` (T073) no es reusable tal cual — construye su propio `AIRequest` (`role=evaluator`, mismo contrato `EvaluatorResponse`, mismo precedente de reuso que T089/T092) usando `objective`/`success_criteria` del proyecto como `prompt`/`success_criteria` y el deliverable como `answer` (`solution=""`, no hay solución de referencia para un proyecto abierto). Crea una segunda `Evidence` por concept, esta vez con scores reales (`correctness`, `reasoning`, `independence`, `transfer`) — complementa la `Evidence` sin calificar de T094, que queda inerte (`MasteryEngine` ignora `None`) hasta esta llamada. Con esto cierra la Fase 9: `Project` completo tiene generación (T092) → tasks (T093) → submission (T094) → evaluation (T095), igual split submit/evaluate que exercises (T072/T073) y reviews (T087).

---

# Fase 10 — API completa

### T096 — Goal routes
**Estado:** DONE
**Dep:** T065  
Implementar endpoints de goals.

**Nota:** `app/api/goals.py` (`GoalResponse`/`CreateGoalRequest`) sobre `GoalApplicationService` (T065), vía `app/api/dependencies.py`. Exactamente los 5 endpoints de `API_SPEC.md` §1: `POST/GET /goals`, `GET/POST /goals/{id}`, `/pause`, `/complete`. `GoalApplicationService` no tenía `get_goal`/`list_goals`/`pause_goal`/`complete_goal` — solo `create_goal` (T065) — añadidos aquí, `pause`/`complete` validan la transición exacta de `DOMAIN_MODEL.md` §17 (`active -> paused`, `active -> completed`) y devuelven `SESSION_STATE_ERROR` (409) si no. Gap real detectado: nada en el código activa un goal (`draft -> active` no tiene disparador en ningún servicio existente) — así que hoy `pause`/`complete` sobre un goal recién creado (`draft`) siempre conflictúa; no se inventa una activación implícita aquí porque no es responsabilidad de esta tarea (candidato natural: T101 roadmap generate o T102 diagnostic start, el primer paso real de "trabajar el goal"). T096 es también la primera ruta real (aparte de onboarding, que no pasa por un `ApplicationService`) — no existía ninguna implementación concreta de `ClockPort`/`IdGeneratorPort` fuera de los fakes de test; añadidas `SystemClock`/`UuidIdGenerator` en `app/api/dependencies.py` junto con `get_engine` (cacheado) y `get_goal_repository`, mismo sitio donde ya vivían `get_config_store`/`get_credential_store`.

### T097 — Vault routes
**Estado:** DONE
**Dep:** T046  
Configure/scan/changes/apply/reject.

**Nota:** `app/api/vault.py`, los 5 endpoints exactos de `API_SPEC.md` §2. `apply` encadena `DiffApprovalService.approve()` (T082) + `ApplyChangeService.apply()` (T083) en una sola llamada — la API nunca expone un `/approve` separado (documentado ya en el propio docstring de `diff_approval_service.py`), así que esta ruta es literalmente el "future route handler" que ese comentario anticipaba. Un conflicto de escritura (`VaultConflictError`) no se traduce a un error HTTP — `ApplyChangeService` ya lo absorbe marcando la proposal `conflicted`/`failed` y devolviéndola con 200 (igual para `reject`, que solo usa `CONFLICT` 409 para "esta proposal ya no está pending"). Gap real de `POST /vault/scan`: ninguna función existente producía la forma `{files_scanned, managed_files, changed_files, errors}` — `VaultIndexer.reindex()` (T042) no devuelve ni hashes previos ni errores de escaneo, y cambiar su firma habría roto los tests de T044/T045 que ya aserts sobre `list[VaultIndexEntry]` directamente — añadido `app/services/vault_scan_service.py` (`VaultScanService.scan()`) que envuelve `reindex()` sin tocarlo: compara `content_hash` antes/después por path y llama `scan_markdown_files()` aparte (barato, solo un recorrido de directorio) para los `errors`. `GoalApplicationService` (T096) ya había mostrado el patrón de "faltan Clock/IdGenerator reales" — aquí el gap equivalente es `VaultResolver` en `dependencies.py`: `get_vault_resolver` recibe `store` vía `Depends(get_config_store)` (no como llamada interna directa, a diferencia de `get_goal_repository`/`get_engine` en T096) precisamente para que `app.dependency_overrides` pueda interceptarlo en tests — sin eso, `VAULT_UNAVAILABLE` no sería testeable end-to-end. Gap documentado y no resuelto aquí: `get_engine()`/`get_settings()` siguen sin aislamiento de test real (usan `Settings().db_path` vía `lru_cache`, no inyectable) — los tests de API evitan el problema sobreescribiendo directamente el `Depends` de nivel de ruta (`get_vault_scan_service`, `get_apply_change_service`, etc.) con instancias reales sobre un engine de test, mismo patrón que T096; arreglarlo de verdad es trabajo para quien primero necesite correr la app contra un proceso real y persistente (candidato natural: T120 fresh-install E2E).

### T098 — Onboarding routes
**Estado:** DONE (ya satisfecha por T025)
**Dep:** T025  
Implementar contratos de onboarding.

**Nota:** Sin cambios de código. T025 ya implementó exactamente los 5 endpoints que `API_SPEC.md` §13 documenta (`GET /status`, `POST /vault`, `POST /ai-provider`, `POST /ai-provider/validate`, `POST /complete`) — adelantada respecto a la numeración de fases por la regla de `AGENTS.md` §2 (API antes que UI). §13 no menciona `FIRST_GOAL` en absoluto ni exige un goal para `/complete` (solo vault + provider validado, tal como T025 ya implementa) — el paso `FIRST_GOAL` es puramente interno a `app/onboarding/state_machine.py`, no una ruta, así que ahora que `GoalApplicationService`/`POST /goals` existen (T065/T096) no hay nada que enlazar aquí. T098 queda como referencia de fase, sin trabajo adicional.

### T099 — Provider configuration routes
**Estado:** DONE
**Dep:** T015–T018  
Leer configuración sin secretos y validar provider/model.

**Nota:** `app/api/providers.py`. `API_SPEC.md` §14 no define rutas propias, solo política ("nunca devolver API keys") + la lista de IDs soportados — sin ruta explícita que seguir, se interpreta el texto de la tarea literalmente: solo lectura + validación, sin ruta de guardado (los providers solo se escriben vía onboarding, T025; cambiar el provider por defecto post-onboarding queda fuera de alcance). Mismo patrón que T097 (`/vault/*` standalone junto a `/onboarding/vault`): `GET /providers` (registro estático, `list_providers()`, ya sin secretos por construcción), `GET /providers/config` (lee `AppConfig` vía `ConfigStore`, omitiendo `credential_ref` por completo del `ConfiguredProvider` de respuesta -- aunque solo es una referencia de keyring y no el secreto en sí, omitirlo entero es más simple de defender que razonar sobre qué podría filtrar), `POST /providers/validate` (reusa `check_provider_capability`, T018, igual que `POST /onboarding/ai-provider/validate` pero sin el acoplamiento al state machine de onboarding).

### T100 — Knowledge routes
**Estado:** DONE
**Dep:** T061  
Knowledge explorer y filtros.

**Nota:** `app/services/knowledge_explorer_service.py` (`KnowledgeExplorerService`) + `app/api/knowledge.py`, los 3 endpoints exactos de `API_SPEC.md` §3 (`GET /goals/{id}/knowledge` con filtros `status`/`mastery_lt`/`next_review_before`, `GET /concepts/{id}`, `GET /concepts/{id}/relations`). Puramente de lectura -- sin cómputo de mastery en vivo, solo lee/filtra los campos ya materializados de `Concept` (`MasteryUpdateService`/T062 y `RetentionUpdateService` los mantienen al día tras cada evidence). Reusa `GoalNotFoundError`/`ConceptNotFoundError` de `context_builder.py` (T060) en vez de redefinirlos -- mismo precedente que T095's `ProjectNotFoundError`. De paso corrige un descuido real de T096: `GoalApplicationService` había añadido su propio `GoalNotFoundError`/`InvalidGoalTransitionError` pero nunca se exportaron desde `app/services/__init__.py` -- al intentar exportar aquí ambos junto al `GoalNotFoundError` ya existente de `context_builder.py` el choque de nombres se hizo evidente; resuelto con alias `GoalApplicationNotFoundError` para el de `goal_service.py` (dos excepciones con el mismo nombre pero significados ligeramente distintos: "goal no existe" en general vs. en el contexto específico de `GoalApplicationService`).

### T101 — Roadmap routes
**Estado:** DONE
**Dep:** T068  
Generate/get/recalculate.

**Nota:** `app/services/roadmap_generation_service.py` (`RoadmapGenerationService`) + `RoadmapService.get_roadmap()` (extiende T068) + `app/api/roadmap.py`, los 3 endpoints exactos de `API_SPEC.md` §4. `generate` y `recalculate` son literalmente la misma operación -- `build_roadmap()` ya supersede el roadmap activo y sube la versión, así que ambas rutas llaman al mismo `generate_roadmap()`, sin dos implementaciones. Gap real: nada conectaba T067 (planner, produce `roadmap_nodes`/`roadmap_edges` como `list[dict]` sin forma fija, `AI_CONTRACTS.md` nunca fija sus claves más allá de un ejemplo vacío) con T068 (`RoadmapService.build_roadmap`, que exige `RoadmapNode`/`RoadmapEdge` tipados) -- añadido el conversor dict->tipado en `roadmap_generation_service.py`, que levanta el mismo `RoadmapValidationError` de T068 para claves requeridas ausentes/mal tipadas (`id`/`title` en nodos, `source`/`target` en edges) y usa los defaults del dataclass para las opcionales (`importance`, `domain`, `relation`). Gap mucho más grande, compartido por T101-T106: **no existía ninguna forma de construir un `AIProvider` real desde la configuración guardada** -- todo el trabajo de IA hasta ahora corría en tests con `MockProvider` inyectado a mano. Añadido `app/ai/provider_factory.py` (`build_default_provider`), que resuelve el provider `is_default`+`enabled` de `AppConfig.ai_providers`, resuelve el credential real desde `CredentialStore` vía `credential_ref`, y construye el adapter correcto (`OllamaProvider`/`OpenAIProvider`/`AnthropicProvider`/`OpenRouterProvider`/`NvidiaNimProvider`/`OpenAICompatibleProvider`/`MockProvider`) reusando los flags `requires_api_key`/`requires_base_url` del `PROVIDER_REGISTRY` (T018) en vez de redefinir esa lógica. Envuelto en `RetryingProvider` sin fallback (ninguna ruta configura uno todavía). `app/api/dependencies.py` gana `get_ai_orchestrator` (primera vez que un `Depends` construye un `AIOrchestrator` real) + `get_planner_service`/`get_roadmap_service`/`get_roadmap_generation_service`. Esta ruta es también la primera en traducir `AIProviderUnavailableError`/`AIInvalidOutputError` (`AI_CONTRACTS.md` §13) a los códigos `AI_UNAVAILABLE`/`AI_INVALID_OUTPUT` de `API_SPEC.md` §11 -- por ahora vía try/except local igual que las demás rutas; T108 (manejo de errores de API) es el lugar natural para consolidar esto en un exception handler global si T102-T106 repiten el mismo patrón.

### T102 — Diagnostic routes
**Estado:** DONE
**Dep:** T066  
Start diagnostic.

**Nota:** `app/services/diagnostic_session_service.py` (`DiagnosticSessionService`) + `app/api/diagnostic.py`, el único endpoint de `API_SPEC.md` §5 (`POST /goals/{id}/diagnostic/start`, sin body documentado). Cierra exactamente el gap que la propia nota de T066 ya señalaba: `DiagnosticService.record_response` exige un `activity_id` real y "asume que existe una Session (mode=assessment) + Activity ya creadas por el flujo que invoque el diagnóstico" -- este es ese flujo. Sin `concept_ids` en el request, se diagnostican todos los concepts ya vinculados al goal (`ConceptRepository.list_by_goal`), lo que solo tiene sentido tras generar un roadmap (T101) -- `NoConceptsForGoalError` (409 `SESSION_STATE_ERROR`) si el goal aún no tiene ninguno. El texto de cada pregunta nunca se persiste por su cuenta (`Activity` sigue sin campo de texto libre, mismo gap de T093/T094) -- se devuelve una única vez en la respuesta HTTP y solo reaparece en `Evidence.metadata` cuando T066's `record_response` califica la respuesta (T103, próxima ruta, consumirá esto). Mismo manejo de `AIProviderUnavailableError`/`AIInvalidOutputError` -> `AI_UNAVAILABLE`/`AI_INVALID_OUTPUT` que T101, vía `get_ai_orchestrator` (T101) reusado sin cambios.

### T103 — Session routes
**Estado:** DONE
**Dep:** T069–T078  
Start/get/next/answer/complete.

**Nota:** `app/api/sessions.py`, los 5 endpoints exactos de `API_SPEC.md` §6. La tarea más grande de la Fase 10 hasta ahora -- compone T069-T078 completos en 3 servicios nuevos:

- `SessionApplicationService` (T069) ganó `get_session`/`complete_session` -- solo tenía `create_session`. `complete_session` exige `active` (`DOMAIN_MODEL.md` §17: "Invalid transitions must be rejected by the domain layer"), nueva `InvalidSessionTransitionError`, mismo patrón que `GoalApplicationService`/T096.
- `app/services/activity_content_service.py` (`ActivityContentService`) resuelve el gap real de T070/T078: `NextActivityService.select_next`/`AdaptiveActivityService.select_next` solo devuelven un `Activity` (referencias a concepts, sin prompt/pregunta) -- generar contenido real exige llamar a `ExerciseGeneratorService` (T071) aparte. Pero entonces `POST .../activities/{id}/answer` necesita un `exercise_id` que la URL nunca lleva y que nada persistía -- **gap de esquema real, no anticipado por ninguna nota de T069-T078**: añadido `Activity.exercise_id: str | None` (`DOMAIN_MODEL.md` §13), empaquetado en `payload_json` igual que `concept_ids` (mismo precedente que T070). `attach_exercise()` genera el Exercise y lo persiste de vuelta en el Activity antes de devolver el contenido.
- `app/services/answer_flow_service.py` (`AnswerFlowService`) encadena T072-T078 completos en una sola llamada (secuencia exacta confirmada contra `test_core_session_e2e.py`): `AnswerSubmissionService.submit_answer` -> `EvaluatorService.evaluate` (IA) -> `EvidenceCreationService.create_evidence` + `MistakeUpdateService.record_from_evaluation` -> por cada concept tocado: `MasteryUpdateService.update_mastery` + `ReviewCreationService.schedule_review` -> `AdaptiveActivityService.select_next` + `ActivityContentService.attach_exercise` para el `next_activity` embebido. `"knowledge_updates"` no tiene forma en ningún doc (`API_SPEC.md` solo muestra `[]`) -- definida aquí: una entrada por concept con `mastery`/`status`/`mistakes_recorded`/`next_review_scheduled_at`, exactamente lo que un cliente necesita sin una segunda vuelta.

Decisión de diseño no derivada de ningún doc: el `content` de `/next` omite deliberadamente `solution`/`common_mistakes` del Exercise -- mostrárselos al alumno antes de intentar el ejercicio anularía el ejercicio.

Primera vez que se ensambla el grafo completo de dependencias de IA/sesión en `app/api/dependencies.py` (17 nuevos `get_*`) -- mismo patrón de `Depends()` anidados que T101/T102, mismo manejo de `AIProviderUnavailableError`/`AIInvalidOutputError` -> `AI_UNAVAILABLE`/`AI_INVALID_OUTPUT` (esta ruta llama IA dos veces: `ExerciseGeneratorService` en `/next` y en el `next_activity` embebido de `/answer`, y `EvaluatorService` en `/answer`).

### T104 — Review routes
**Estado:** DONE
**Dep:** T086–T088  
Today/complete.

**Nota:** `app/services/review_flow_service.py` (`ReviewFlowService`) + `app/api/reviews.py`, los 2 endpoints exactos de `API_SPEC.md` §7. `GET /reviews/today` es un passthrough directo a `TodaysReviewsService` (T086), sin cambios. `POST /reviews/{id}/complete` cierra dos gaps reales:

1. `ReviewCompletionService.complete_review` (T087) exige un `activity_id` real, pero `evidence.activity_id` es FK `NOT NULL` a `activities`, que a su vez tiene FK `NOT NULL` a `sessions` -- y una review standalone (bajo `/reviews/*`, no `/sessions/*`) no tiene ninguno de los dos. `SessionMode.REVIEW`/`ActivityType.REVIEW` ya existían para exactamente este caso -- `ReviewFlowService` crea un Session+Activity mínimos, ya `completed`, solo para satisfacer la FK (mismo precedente que la sesión de diagnóstico de T102, pero de una sola vez en vez de multi-turno). El Session+Activity se persisten **antes** de llamar a `complete_review`, porque es esa llamada la que escribe la Evidence que apunta a ellos vía FK.
2. La propia nota de T088 ya señalaba el hueco: "MasteryEngine ya lee Concept.retention... pero nada lo escribía hasta ahora" -- construyó la escritura, no quién la llama. `ReviewFlowService` es ese llamador, replicando lo que `AnswerFlowService` (T103) ya hace para evidence de exercises: actualiza retention (T088) y luego mastery (T075) justo después de crear la evidence que los alimenta -- retention primero porque `MasteryEngine` la lee como uno de sus inputs.

De paso, corregido un tipo inconsistente entre tareas hermanas: `ReviewCompletionService.complete_review` (T087) tipaba `confidence: int` mientras que `AnswerSubmissionService.submit_answer` (T072) ya usaba `ConfidencePercent` -- alineado a `ConfidencePercent` en ambos servicios de reviews. La respuesta de `/complete` no tiene forma documentada en `API_SPEC.md` (solo el request) -- definida aquí como `completed_review`+`next_review`+`concept` (mastery/retention/status), mismo criterio que T103's `knowledge_updates`: lo que el cliente necesita sin una segunda llamada.

### T105 — Assessment routes
**Estado:** DONE
**Dep:** T089–T090  
Create/get/answer/complete.

**Nota:** `app/services/assessment_session_service.py` (`AssessmentSessionService`) + `app/api/assessments.py`, los 4 endpoints exactos de `API_SPEC.md` §8 (ninguno con request/response documentado). Mismo hueco FK que T102/T104: una transfer assessment (T089) es solo un Exercise generado, y calificarla (T090's `AssessmentCompletionService`, sin tocar) escribe Evidence cuyo `activity_id` es FK `NOT NULL` a `activities`→`sessions` -- `POST /goals/{id}/assessments` no tiene ninguno de los dos, así que `AssessmentSessionService.create_assessment` crea un Session (`mode=assessment`) + Activity (`type=assessment`) reales antes de que generar el Exercise persista algo. A diferencia de T102/T104, este Session queda `active` en vez de pre-completado: reusa el split "answer = calificación completa, complete = cerrar sesión" que T103 estableció y T104 citó como precedente -- `/answer` llama a `AssessmentCompletionService.complete_assessment` (T090) sin cambios, `/complete` llama a `SessionApplicationService.complete_session` (T103) sin cambios, así que ninguno de los dos servicios ya probados necesitó tocarse. `assessment_id` en la URL es el id del Activity, no un identificador nuevo -- mismo precedente que T103/T104 de que el Activity es la unidad direccionable. `concept_id` requerido en el body de `POST /goals/{id}/assessments` pese al silencio del spec -- `generate_transfer_scenario` (T089) lo necesita y una transfer assessment es inherentemente de un solo concept, a diferencia del diagnostic multi-concept de T102. Mismo manejo de `AIProviderUnavailableError`/`AIInvalidOutputError` -> `AI_UNAVAILABLE`/`AI_INVALID_OUTPUT` que T101-T104, vía `get_ai_orchestrator` reusado sin cambios; `app/api/dependencies.py` gana `get_transfer_assessment_service`/`get_assessment_session_service`/`get_assessment_flow_service`.

**Fix posterior (mismo T105):** `AssessmentCompletionService.complete_assessment` (T090) escribe Evidence puntuada pero nunca llamaba a `MasteryUpdateService`/`ReviewCreationService` -- mismo hueco que la nota de T088 ya señalaba para retention ("MasteryEngine ya lee... pero nada lo escribía"), cerrado para reviews por `ReviewFlowService` (T104) y aquí por `app/services/assessment_flow_service.py` (`AssessmentFlowService`), que envuelve `AssessmentCompletionService` sin tocarlo y, tras la calificación, actualiza mastery + agenda la siguiente review por cada concept que la evidence tocó (mismo patrón que T103's `AnswerFlowService`), además de marcar el Activity `completed` (movido aquí desde `AssessmentSessionService.mark_activity_completed`, ahora eliminado -- una sola responsabilidad de cierre de flujo en un solo sitio). La ruta `/answer` pasa a depender de `AssessmentFlowService` en vez de `AssessmentCompletionService` directamente; la respuesta gana `updated_concepts` (concept_id/mastery/status) para que el cliente vea el efecto sin una segunda llamada.

### T106 — Project routes
**Estado:** DONE
**Dep:** T092–T095  
Create/list/get/task submit.

**Nota:** `app/services/project_session_service.py` (`ProjectSessionService`) + `app/services/project_flow_service.py` (`ProjectFlowService`) + `app/api/projects.py`, los 4 endpoints exactos de `API_SPEC.md` §9 (ninguno con request/response documentado). `POST /goals/{id}/projects` combina T092 (`ProjectGenerationService.generate_project`) + T093 (`ProjectTaskService.create_tasks`) en una sola llamada -- el spec no tiene una ruta separada de "generar tareas", mismo patrón de combinar que T102 ya aplica a session+items del diagnostic. `POST /projects/{id}/tasks/{task_id}/submit` combina T094 (`ProjectSubmissionService.submit_task`, Evidence sin puntuar) + T095 (`ProjectEvaluationService.evaluate_submission`, Evidence puntuada) en la única ruta que el spec documenta -- a diferencia de las assessments (T090/T105), que sí tienen dos rutas separadas (`/answer` + `/complete`), projects solo tiene `submit`, así que aquí no hay equivalente a "cerrar sesión" por separado. Aplicado desde el principio (no como fix posterior, aprendido del gap detectado en T105) el mismo cierre de bucle mastery/review: ni `ProjectSubmissionService` ni `ProjectEvaluationService` llamaban a `MasteryUpdateService`/`ReviewCreationService` tras escribir evidence -- `ProjectFlowService` lo hace tras la evaluación, una vez por concept que la evidence puntuada tocó, mismo patrón que `AnswerFlowService`/`ReviewFlowService`/`AssessmentFlowService`. `GET /projects/{id}` devuelve solo los campos propios del Project persistido, no sus tareas -- `Project` no tiene `session_id` (`DOMAIN_MODEL.md` §14) y no existe ninguna forma persistida de encontrar la Session que `create_tasks` generó para él, así que inventar esa columna solo para soportar un re-listado de tareas que el spec nunca pide habría sido un cambio mayor del que esta tarea exige; el cliente conserva los `task_id` de la respuesta de creación, mismo patrón que T103's `/next` para `activity_id`. Mismo manejo de `AIProviderUnavailableError`/`AIInvalidOutputError` -> `AI_UNAVAILABLE`/`AI_INVALID_OUTPUT` que T101-T105, vía `get_ai_orchestrator` reusado sin cambios; `app/api/dependencies.py` gana `get_project_repository`/`get_project_generation_service`/`get_project_task_service`/`get_project_session_service`/`get_project_submission_service`/`get_project_evaluation_service`/`get_project_flow_service`.

### T107 — Progress route
**Estado:** DONE
**Dep:** T061–T088  
Resumen de mastery, concepts, weak, reviews y sesiones.

**Nota:** `app/services/progress_service.py` (`ProgressService`) + `app/api/progress.py`, el único endpoint de `API_SPEC.md` §10 (`GET /goals/{id}/progress`), con response documentado exactamente: `mastery`, `concepts_total`, `mastered`, `weak`, `due_reviews`, `recent_sessions`. Puramente de agregación sobre estado ya materializado -- mismo split "solo lectura, sin cómputo" que T100 ya estableció para `KnowledgeExplorerService`. Dos decisiones no derivadas de ningún doc: (1) `mastery` se normaliza a 0..1 (`MAX_MASTERY = 5.0`) -- `Concept.mastery` es escala 0..5 (`DOMAIN_MODEL.md` §18), pero el ejemplo del spec (`0.62`) solo tiene sentido como fracción, consistente con cómo se presentan confidence/retention en el resto de la API; (2) `recent_sessions` cuenta las sesiones del goal iniciadas en la última semana (`RECENT_SESSIONS_WINDOW_DAYS = 7`) -- "recent" no está definido en ningún doc, una semana es la lectura MVP más natural para una app de repetición espaciada. `due_reviews` filtra `ReviewRepository.list_due(now)` (T063, sin scope de goal, mismo passthrough sin scope que ya usa `TodaysReviewsService`/T086) por `goal_id` en memoria -- `Review` ya lleva `goal_id` (`DOMAIN_MODEL.md` §11), sin necesitar tocar el repositorio. Gap real de puerto sí encontrado: `SessionRepository` nunca tuvo forma de listar las sesiones de un goal (solo `add`/`get`/`update`) -- añadido `list_by_goal` al protocolo (`app/domain/ports.py`) y a `SqlSessionRepository`, mismo tipo de gap fix que T068's `RoadmapRepository`/T092's `ProjectRepository` cuando un agregado necesitó una query que no existía.

### T108 — API error handling
**Estado:** DONE
**Dep:** T096–T107  
Códigos normativos: `VALIDATION_ERROR`, `NOT_FOUND`, `CONFLICT`, `VAULT_CONFLICT`, `VAULT_UNAVAILABLE`, `AI_UNAVAILABLE`, `AI_INVALID_OUTPUT`, `SESSION_STATE_ERROR`, `PERMISSION_DENIED`.

**Nota:** Auditoría + consolidación, no una ruta nueva. Confirmado por inspección (`grep` de cada llamada `_error("<CODE>", ...)` en las 11 rutas de T096-T107) que todo código usado es uno de los 9 normativos de `API_SPEC.md` §11 -- `VAULT_CONFLICT` y `PERMISSION_DENIED` siguen sin usarse: `VAULT_CONFLICT` es absorbido por `ApplyChangeService` (T083/T097, la proposal queda `conflicted` con 200, nunca sale como HTTP error, decisión ya documentada en T097) y `PERMISSION_DENIED` no tiene ningún caso de uso en esta app local-first de un solo usuario -- ninguno de los dos es un hueco, solo código reservado sin disparador todavía. Consolidación real: cada uno de los 11 módulos de ruta (`goals`, `vault`, `knowledge`, `roadmap`, `diagnostic`, `sessions`, `reviews`, `assessments`, `projects`, `progress`, `onboarding`) tenía su propio `_error()` local byte-idéntico -- señalado ya desde la nota de T101 como "candidato natural para consolidar en T108 si el patrón se repite lo suficiente", y para T107 se había repetido 11 veces. Todo colapsado en `app/api/errors.py` (`api_error()` + `NORMATIVE_ERROR_CODES`), importado en las 11 rutas y también en `app/api/dependencies.py` (`get_vault_resolver`/`get_ai_orchestrator`, que construían el mismo envelope a mano por tercera vez). Bug real encontrado en la auditoría, no solo duplicación: `onboarding.py` (T025, anterior a que T096+ estableciera la convención) tenía su propio `_error(code, message, status_code=400)` con default -- cuatro de sus llamadas a `SESSION_STATE_ERROR` confiaban en ese default y devolvían HTTP 400, mientras que *todas* las demás rutas del API mapean `SESSION_STATE_ERROR` a 409. `api_error()` no tiene default (`status_code` es posicional obligatorio) precisamente para que un default divergente no pueda volver a esconderse -- corregidas las 4 llamadas a 409 explícito, y actualizados los 2 tests de `test_onboarding.py` que aserteaban el 400 incorrecto. Sin exception handler global: un catch-all para excepciones no anticipadas habría escondido bugs reales de desarrollo bajo un código no documentado en absoluto por `API_SPEC.md` -- los 9 códigos normativos son la lista cerrada a mantener, no una invitación a inventar un décimo.

# Fase 11 — Frontend

### T109 — App shell
**Estado:** DONE
**Dep:** T011, T098  
Routing y navegación.

**Nota:** Primera tarea de Fase 11. `App.tsx` antes de esto montaba `<OnboardingWizard />` sin condición alguna -- ningún camino llevaba a nada más tras completar onboarding (`FinishStep`'s rama `alreadyComplete` solo mostraba un mensaje estático "You're all set", callejón sin salida). Añadido `react-router-dom` (única dependencia de routing del proyecto, ninguna guía previa en los docs sobre qué librería usar). `App.tsx` ahora decide entre `OnboardingWizard` y el shell routeado: `OnboardingWizard` gana un prop opcional `onFinished` que dispara un `useEffect` cuando `status.onboarding_step === 'COMPLETE'` (ya sea recién completado o ya completo al cargar) -- sin tocar su lógica interna de pasos, mínimo diff sobre código ya testeado. `app/shell/AppShell.tsx` (nav lateral + `<Outlet />`) + `app/shell/routes.tsx` (tabla de rutas) + `app/shell/Placeholder.tsx` (stand-in reusable para las 9 páginas que T111-T119 reemplazan una a una: Dashboard, Goal, Roadmap, Knowledge Explorer, Session, Reviews, Assessment, Project, Vault Changes). Nav solo enlaza páginas sin scope de goal (Dashboard/Reviews/Vault) -- las rutas con `:goalId`/`:sessionId`/etc. son alcanzables por URL pero sin link propio todavía, porque nada antes de T111 (Dashboard) puede listar goals para enlazar a ellas. Verificado en navegador real (no solo tests): flujo completo de onboarding (vault real del repo, provider mock) hasta `Finish setup`, confirmando la transición al shell routeado, navegación por clic entre Dashboard/Reviews/Vault, deep-link directo a una ruta con params (`/goals/goal_1/roadmap`), y el fallback de ruta desconocida a Dashboard -- los tests de Vitest cubren lo mismo pero con `fetch` mockeado, así que esta fue la primera confirmación real contra el backend vivo. La verificación en vivo encontró un bug real de contraste en modo oscuro (`color-scheme: light dark` ya activo en `index.css`, pero `.app-nav a` fijaba `color: #222` sin fondo emparejado -- ilegible en fondo oscuro): corregido dejando el color heredar en el estado normal y solo fijando `color`+`background` juntos en `:hover`/`.active`, igual patrón que `onboarding.css` ya usa en sus cajas (botones, provider cards). Tests nuevos: `App.test.tsx` (transición a shell cuando el status ya es `COMPLETE`) y `shell/routes.test.tsx` (cada placeholder resuelve en su ruta, más el fallback).

### T110 — Onboarding UI
**Estado:** DONE (ya satisfecha por T020–T024)
**Dep:** T020–T024, T098  
Completar onboarding de vault/provider/model.

**Nota:** Sin cambios de código -- `OnboardingWizard.tsx` ya ensambla T020 (`VaultStep`), T021 (`ProviderStep`), T022/T023 (`CredentialModelStep`) y T024 (resumible vía `GET /onboarding/status` al montar) en la máquina de pasos completa (`WELCOME → VAULT_SCAN → AI_PROVIDER → VALIDATE → COMPLETE`), y las 4 tareas ya estaban `DONE` individualmente con su propio criterio de aceptación ("verificado manualmente en navegador", sin tests automatizados -- patrón ya establecido, no introducido aquí). La verificación en navegador real hecha para T109 (vault real del repo → provider mock → modelo+test de conexión → finish → entra al shell routeado) ejercitó el flujo completo de principio a fin contra el backend vivo, cerrando el mismo criterio de aceptación para T110. `CredentialModelStep` confirma en el propio código los invariantes de seguridad que T022/T023 ya documentaban: el campo de credencial es `type="password"`, se limpia del estado (`setCredential('')`) justo tras una validación exitosa, y nunca se envía a ningún sitio salvo `POST /onboarding/ai-provider/validate`.

### T111 — Dashboard
**Estado:** DONE
**Dep:** T107  
Estado general y siguiente acción.

**Nota:** `frontend/src/dashboard/Dashboard.tsx`, primera página real del shell (T109) reemplazando su placeholder. Ningún task de Fase 11 se llama "crear goal" -- sin este formulario, un install nuevo con cero goals sería un callejón sin salida en la UI (el backend ya tiene `POST /goals` desde T096, nada lo exponía). Decisión no derivada de ningún doc: el dashboard con cero goals muestra directamente el formulario de creación (sin toggle), y con uno o más goals lo colapsa detrás de un botón "+ New goal" -- prioriza el caso de primer uso. "Siguiente acción" implementado como el agregado de `due_reviews` de `GET /goals/{id}/progress` (T107) sobre todos los goals: si es >0, banner con link a `/reviews`; si es 0, mensaje de "al día". Cada goal se muestra como card (título, status, barra de mastery normalizada 0..1 tal como T107 ya la define, concepts_total/mastered/weak, due_reviews si >0) enlazando a `/goals/:goalId` (T112). Extraído `src/api/client.ts` (helper `request()` + `ApiError`) desde `api/onboarding.ts`, que antes lo definía en solitario -- mismo principio de T108 (backend): consolidar antes de que un segundo cliente API (`api/goals.ts`, nuevo aquí) lo duplique. `onboarding.ts` re-exporta `ApiError` desde el nuevo módulo para no romper ninguno de sus imports existentes. Verificado en navegador real contra el backend vivo: dashboard vacío → crear goal → aparece la card con datos reales de `/goals/{id}/progress` → click en la card navega a `/goals/:id`. `dashboard.css` aplica desde el principio la regla de contraste en modo oscuro que T109 tuvo que corregir a posteriori (texto plano sin color explícito hereda bien; un color fijo necesita `background` emparejado) -- sin bug esta vez, evitado por diseño.

### T112 — Goal view
**Estado:** DONE
**Dep:** T096, T107  
Mastery, weak concepts, reviews y roadmap.

**Nota:** `frontend/src/goal/GoalView.tsx`, reemplaza el placeholder de `/goals/:goalId`. El dep list es literalmente T096+T107 -- interpretado como: la lista *enumerada* de weak concepts (no solo el número) y el grafo de roadmap son responsabilidad de sus propias páginas (Knowledge explorer T114, dep T100; Roadmap view T113, dep T101), esta página solo muestra los 4 números que `GET /goals/{id}/progress` (T107) ya da de un vistazo (mastery, concepts_total/mastered/weak, due_reviews, recent_sessions) con links de salida a ambas -- mismo split resumen/detalle que el Dashboard (T111) ya usa para sus goal cards. Extraído `frontend/src/shared/MasteryBar.tsx` desde el `GoalCard` del Dashboard -- segundo uso del mismo bloque visual, mismo umbral de consolidación que T108 aplicó en el backend (una vez repetido, no dos). Acciones de ciclo de vida limitadas a lo que `GoalApplicationService` realmente expone (T096): pausar/completar, solo visibles cuando `status === 'active'` -- no se inventa una acción "activar" para goals `draft`, porque no existe ese endpoint (T096 lo señaló ya como hueco real, activación es efecto secundario de generar un roadmap, T101). Nuevas funciones en `api/goals.ts`: `getGoal`, `pauseGoal`, `completeGoal`. Verificado en navegador real: goal `draft` recién creado muestra sus stats en cero sin botones de pausar/completar (correcto, dado que no está activo), y los links a Roadmap/Knowledge Explorer navegan a sus rutas correctas.

### T113 — Roadmap view
**Estado:** DONE
**Dep:** T101  
Dependencias y progreso.

**Nota:** `frontend/src/roadmap/RoadmapView.tsx`, reemplaza el placeholder de `/goals/:goalId/roadmap`. Renderiza nodes/edges como lista legible en vez de un diagrama node-link -- ninguna otra página de la Fase 11 intenta renderizado de grafo todavía, y una lista ya transmite todo lo que pide la tarea (progreso por concept vía `MasteryBar` reusado de T112, dependencias derivadas de edges `PREREQUISITE_OF` como "Requires: X, Y") sin la complejidad añadida de un layout engine para una página MVP. Nota de tipo real: `RoadmapNode.mastery` es escala 0..5 (`DOMAIN_MODEL.md` §18) a diferencia de `GoalProgress.mastery` (T107, ya normalizado 0..1) -- `MasteryBar` sigue esperando 0..1, así que aquí se divide por `MAX_MASTERY=5` en el punto de uso en vez de cambiar el componente compartido. Maneja los 3 estados reales de la ruta: sin roadmap aún (`RoadmapNotFoundError` → 404 `NOT_FOUND`, muestra CTA "Generate roadmap"), generado (lista de nodes), y `Recalculate` (mismo botón reusable, ambos llaman a `generate_roadmap` en el backend per T101's nota -- son la misma operación). Verificado en navegador real: el estado vacío y el botón "Generate roadmap" renderizan correctamente contra el backend vivo; `MockProvider` no tiene forma de configurar una respuesta fuera de tests automatizados, así que generar un roadmap real no se pudo verificar por HTTP en vivo -- en su lugar se verificó que un fallo real de IA (`AI_INVALID_OUTPUT` de verdad, no simulado) se propaga y se muestra legible en modo oscuro; el render de la lista de nodes poblada queda cubierto por Vitest con datos mockeados de forma realista (misma forma que la respuesta real de `GET /goals/{id}/roadmap`).

### T114 — Knowledge explorer
**Estado:** DONE
**Dep:** T100  
Conceptos, evidence y weaknesses.

**Nota:** `frontend/src/knowledge/KnowledgeExplorer.tsx`, reemplaza el placeholder de `/goals/:goalId/knowledge`. "Evidence" leído como las señales ya materializadas en `Concept` (mastery, confidence, retention, last_practiced) -- T100 es la única dependencia y ninguna ruta de la API expone `Evidence` cruda como recurso HTTP (`EvidenceRepository` es interno a `MasteryEngine`/`RetentionUpdateService`), mismo criterio de "ceñirse a lo que el dep list realmente da" que T112 ya aplicó. "Weaknesses" es el filtro `status` que `GET /goals/{id}/knowledge` (T100) ya soporta -- expuesto como dropdown, sin UI separada. Cada concept es una fila expandible/colapsable (sin ruta nueva): al expandir, fetch lazy de `GET /concepts/{id}/relations` (T100) cacheado por concept_id, resolviendo `target_id` a título cuando el concept destino está en la lista actualmente cargada (mismo goal), con fallback al id crudo si no. Verificado en navegador real con concepts sembrados directamente vía `SqlConceptRepository`/`SqlConceptRelationRepository` (no hay forma de crear concepts sin IA -- ni diagnóstico ni roadmap generation son viables con `MockProvider` fuera de tests automatizados, mismo límite que T113 encontró): filtro por status, expansión mostrando mastery/confidence/retention, y resolución de relación a título ("related to → Subqueries") todo correcto y legible en modo oscuro.

### T115 — Session UI
**Estado:** DONE
**Dep:** T103  
Actividad, respuesta, confidence, hints, feedback y next.

**Nota:** `frontend/src/session/SessionUI.tsx`, reemplaza el placeholder de `/sessions/:sessionId` -- el núcleo del loop de aprendizaje. Ninguna página anterior de la Fase 11 tenía forma de *crear* una session, así que `GoalView` (T112) gana un botón "Start session" (`POST /goals/{id}/sessions` con `mode=guided`/`duration_minutes=30` fijos -- sin selector de modo, MVP) que navega a `/sessions/:id`. La respuesta de `/answer` (`AnswerFlowService`, T103) ya trae embebido el `next_activity` -- "Continue" nunca vuelve a llamar a `/next`, solo reemplaza `activity` por `result.next_activity.content` directamente; cuando `next_activity` es `null` la única salida es `/complete`. Hints ocultos por defecto tras un toggle "Show hints" -- mismo criterio de diseño ya documentado en T103's propio backend (mostrarlos de entrada anula el ejercicio). Maneja `SESSION_STATE_ERROR` de `/next` (goal sin candidatos, p.ej. sin roadmap/diagnostic aún) como estado propio "Nothing to work on yet" en vez de error genérico, y una session ya no-activa al cargar la página se muestra directamente como completa sin intentar pedir actividad. Verificado en navegador real de punta a punta: click en "Start session" desde `GoalView` → crea la session real → navega → muestra correctamente "Nothing to work on yet" contra un goal sin concepts (mismo límite de `MockProvider` fuera de tests que T113/T114 ya encontraron para generar contenido real vía IA) -- el loop completo de responder/continuar/finalizar queda cubierto por 6 tests de Vitest con datos mockeados en la forma exacta de `AnswerFlowService`'s respuesta real.

### T116 — Reviews UI
**Estado:** DONE
**Dep:** T104  
Completar reviews.

**Nota:** `frontend/src/reviews/ReviewsUI.tsx`, reemplaza el placeholder de `/reviews` (ya enlazado en el nav de `AppShell` desde T109). Más simple que la Session UI (T115): sin round-trip al servidor para "qué sigue" -- `GET /reviews/today` (T104) ya da la cola completa por adelantado, avanzada localmente (`index++`) tras cada `/complete`, sin re-fetch. Reusa `MasteryBar` (T112) para el mastery del concept devuelto, tercer uso del componente compartido. Verificado en navegador real de punta a punta contra el backend vivo (sin límite de `MockProvider` esta vez -- completar una review es self-reported, T087, no llama a IA): review sembrada directamente vía `SqlReviewRepository` → responder con confidence → grading real → mastery/retention/next-review actualizados y visibles → cola vacía muestra "You're all caught up".

### T117 — Assessment UI
**Estado:** DONE
**Dep:** T105  
Transfer/final assessment.

**Nota:** `frontend/src/assessment/AssessmentUI.tsx`, reemplaza el placeholder de `/assessments/:assessmentId`. A diferencia de la Session UI (T115), sin cadena de actividades -- una transfer assessment (T089/T105) es un solo exercise por creación, calificado atómicamente (`AssessmentCompletionService`, T090), así que tras `/answer` el único paso siguiente es `/complete`, nunca otro exercise. Iniciada desde el Knowledge Explorer (T114): una assessment es inherentemente de un solo concept (`generate_transfer_scenario` exige `concept_id`, T089), y esa es la única página que ya lista concepts individualmente para elegir uno -- botón "Start transfer assessment" añadido a la fila expandida de cada concept, llamando a `POST /goals/{id}/assessments`. Badges de `transfer_demonstrated`/`independence_demonstrated` (T090's juicio explícito sobre los scores crudos) con fondo+color emparejados desde el primer intento -- mismo patrón de contraste en modo oscuro que T109 estableció y T116 confirmó, sin bug nuevo esta vez. Verificado en navegador real: click en "Start transfer assessment" desde Knowledge Explorer → crea la assessment real → navega → mismo límite de `MockProvider` que T113/T115 (`ExerciseGeneratorResponse` sin respuesta configurada) surge correctamente como error legible; el loop de responder/badges/completar queda cubierto por 3 tests de Vitest con datos mockeados en la forma exacta de la respuesta real del backend.

### T118 — Projects UI
**Estado:** DONE
**Dep:** T106  
Proyecto y tareas.

**Nota:** `frontend/src/project/ProjectView.tsx` (ruta `/projects/:projectId`) + sección "Projects"/botón "Start project" añadidos a `GoalView` (T112). A diferencia de assessments (un solo concept), un project es multi-concept (`POST /goals/{id}/projects` exige `concept_ids: list[str]`, T106) y ninguna página lista concepts con selección múltiple todavía -- "Start project" usa pragmáticamente *todos* los concept_ids ya vinculados al goal (`GET /goals/{id}/knowledge` sin filtro, T100), interpretado como "proyecto de práctica que cubre todo el material actual del goal", sin construir un selector nuevo. Gap real heredado de T106, no introducido aquí: `GET /projects/{id}` deliberadamente nunca devuelve tasks (T106's nota: sin `Project -> Session` persistido para resolverlas) -- así que la lista de tasks solo existe justo tras crear el project, pasada vía `navigate(path, {state: {tasks}})` desde `GoalView`; recargar `/projects/:id` o abrirlo desde un link guardado muestra el project sin tasks, con una nota explícita en vez de fallar en silencio. Verificado en navegador real: goal sin concepts → "Start project" muestra el guard local ("no concepts yet") sin llamar a IA; goal con un concept seedeado → mismo límite de `MockProvider` que T113/T115/T117 (`ExerciseGeneratorResponse`) surge correctamente como error de página completa (mismo patrón ya establecido en todas las páginas de esta fase, no una regresión nueva). El loop de listar tasks/enviar deliverable/ver evaluación queda cubierto por Vitest con datos mockeados en la forma exacta de `SubmitTaskResponse`.

### T119 — Vault diff UI
**Estado:** DONE
**Dep:** T097  
Before/after + approve/reject.

**Nota:** `frontend/src/vault/VaultDiffUI.tsx`, reemplaza el placeholder de `/vault` (ya enlazado en el nav desde T109) -- última tarea de la Fase 11. `ChangeProposal` (T044) nunca tuvo campo "before", y ninguna ruta de la API expone el contenido actual de una nota (el vault es de solo lectura desde el frontend salvo por los mecanismos específicos de scan/write ya construidos) -- "before" se muestra como placeholder honesto ("(new file)" para `create_file`, "(current content not available via this API)" para el resto) en vez de fabricar algo, mismo criterio que T118 ya aplicó a su propio hueco real. "Approve" es `/apply`, que ya encadena approve+apply en una sola llamada (nota propia de T097: no existe una ruta `/approve` separada); un conflicto o fallo vuelve como 200 con la proposal marcada `conflicted`/`failed` (T097), no como error HTTP, así que esta página lee `result.status` tras la llamada en vez de depender de una excepción. Dado que ningún flujo de la app crea proposals todavía (el rol Curator, T080+, no tiene disparador de UI en ninguna tarea de esta fase), la lista está vacía en uso normal hasta que exista esa pieza -- el botón "Rescan vault" (`POST /vault/scan`, T097) sigue siendo útil por sí solo para reindexar. Verificado en navegador real de punta a punta contra el backend vivo, sin límite de `MockProvider` esta vez (nada aquí llama a IA): proposal sembrada directamente vía `ChangeProposalRepository` con un path de scratch aislado (nunca aprobada, para no escribir de verdad en `docs/` del propio repo) → expandir muestra before/after correctos → Reject actualiza el status en vivo → Rescan vault reindexa los 11 archivos reales de `docs/` y refresca la lista. Con T119, la Fase 11 (Frontend) queda completa: T109-T119, las 11 tareas, todas `DONE`.

Última limpieza de la fase: `frontend/src/shell/Placeholder.tsx` eliminado -- sus 9 usos en `routes.tsx` (uno por página placeholder, T109-T118) fueron reemplazándose una a una a medida que cada tarea aterrizaba su página real, y T119 reemplazó el último; sin ninguna referencia restante, era código muerto.

---

# Fase 12 — Release MVP

### T120 — Fresh-install E2E
**Estado:** DONE
**Dep:** T110  
Install → onboarding → vault → provider → goal.

**Nota:** Primera tarea de la Fase 12 -- y el primer test de esta clase en el repo. Todo lo anterior (Vitest bajo `src/`) mockea `fetch`; esto necesita un navegador real contra un backend Python real y un frontend Vite real simultáneamente, algo que ni pytest ni Vitest pueden hacer -- Playwright (`@playwright/test`, nuevo devDependency) es la elección estándar para exactamente este caso, sin alternativa más ligera razonable dentro de este stack. `backend/scripts/run_e2e_backend.py` borra y re-migra una base de datos SQLite desechable (`backend/data/e2e.sqlite3`, vía `LEARNINGOS_DB_PATH`, ya soportado por `Settings`) antes de arrancar uvicorn en cada run -- así "fresh install" es de verdad fresh, no solo un DB persistido entre corridas. Escrito en Python (no chaineado en el `command` de `webServer`) a propósito: `rm -rf && uvicorn` no funciona igual en `cmd.exe` (CI... no, dev Windows) que en `sh` (CI Linux), y `playwright.config.ts` invoca este script idénticamente en ambos. El escenario (`e2e/fresh-install.spec.ts`) cubre exactamente el texto de la tarea -- vault real (fixture `e2e/fixtures/vault/`) → provider Mock → validar → goal -- sin tocar el límite de `MockProvider` que T113/T115/T117/T118 encontraron en verificación manual: `POST /onboarding/ai-provider/validate` (T018) y `POST /goals` (T096) no llaman a `AIOrchestrator.generate()`, así que todo el escenario es genuinamente automatizable de punta a punta contra el mock provider real, sin canned response. `vite.config.ts` gana `exclude: [...configDefaults.exclude, 'e2e/**']` -- sin esto, el glob por defecto de Vitest también intenta correr los specs de Playwright y falla (`test()` de `@playwright/test` fuera de un run de Playwright). Nuevo job `e2e` en CI (`.github/workflows/ci.yml`, separado de `backend`/`frontend` porque necesita ambos toolchains) -- verificado localmente corriendo `npm run test:e2e` dos veces de punta a punta antes de commitear, ambas en verde.

### T121 — Full canonical-loop E2E
**Estado:** DONE
**Dep:** T079, T085, T091, T095, T119  
GOAL → DIAGNOSE → 80/20 → ROADMAP → LEARN → PRACTICE → FEEDBACK → ADAPT → CONSOLIDATE → REVIEW → TRANSFER → PROJECT → EVALUATE.

**Nota:** A diferencia de T120, esto no puede ser un test de navegador: cada paso IA-dependiente necesita una respuesta enlatada de `MockProvider.set_response()`, que solo es configurable desde Python, nunca vía HTTP -- un test Playwright se bloquearía en la primera llamada IA real. Es en cambio un test de integración backend (`backend/tests/e2e/test_canonical_loop.py`, `TestClient` + `app.dependency_overrides`), el mismo patrón ya probado por cada test de ruta T096-T119, aplicado aquí a todo el recorrido de una sola vez en lugar de a una ruta aislada. `app.dependency_overrides` solo intercepta lo que una ruta recibe vía `Depends(...)` -- cada `get_X_repository()`/`get_engine()` que un provider llama internamente (no vía `Depends`) es invisible a los overrides, así que el test reconstruye a mano el árbol completo de repositorios/servicios sobre un único engine SQLite en `tmp_path` y un único `AIOrchestrator`/`MockProvider` compartidos, y sobreescribe solo las ~19 funciones `get_X_service`/`get_X_repository` de nivel de ruta que cada endpoint usa directamente.

El orden real diverge del texto de SPECS.md (GOAL → DIAGNOSE → 80/20 → ROADMAP): `DiagnosticSessionService` (T102) exige conceptos ya vinculados al goal, y solo `RoadmapService.build_roadmap` (T068) los crea y vincula -- así que ROADMAP corre antes que DIAGNOSE. No es una decisión nueva de esta tarea: ya la establece la propia nota de T102, y `PlannerService.plan()` (T067) devolviendo `roadmap_nodes`/`roadmap_edges` junto al 80/20 significa que una sola llamada a `/roadmap/generate` ya cubre 80/20 + ROADMAP juntos.

CONSOLIDATE no tiene ruta: `grep` confirma que `CuratorService` (T080) y `ProposalValidator` (T081) están completos pero nunca se invocan desde ningún flujo de aplicación ni ruta API en todo el repo -- un gap real, no un artefacto de este test. En vez de inventar wiring de producción "siempre activo" que ninguna tarea especifica (una decisión de arquitectura/producto fuera del alcance de T121), el test ejercita el pipeline directamente en Python (`propose` → `validate_and_persist`), y entrega el `ChangeProposal` resultante a la ruta real `POST /vault/changes/{id}/apply` (T097) para la mitad de aprobación humana que sí existe. Este gap queda documentado aquí para quien decida dónde debe dispararse el curator en producción.

### T122 — Provider smoke matrix
**Estado:** DONE
**Dep:** T051–T056  
Mock en CI; Ollama/OpenAI/Anthropic/OpenRouter/NVIDIA/compatible en tests de entorno separado cuando haya credenciales.

**Nota:** `backend/tests/live/test_provider_smoke.py` -- un test por adapter real (no `MockProvider`), cada uno con su propio round-trip contra la API real: construye el provider desde variables de entorno `LEARNINGOS_LIVE_<PROVIDER>_*` (API key/modelo/base_url según lo que cada adapter exija) y llama `generate()` con un `AIRequest`/`response_model` mínimos, verificando que la respuesta real parsea contra el contrato. `docs/AGENTS.md` #17 ("Live model tests belong in a separate optional suite") se cumple con `@pytest.mark.skipif` por variable de entorno, no con exclusión de directorio: los 6 tests SIGUEN corriendo (y mostrándose como `skipped`) en `uv run pytest`/CI normal -- visibles mas no bloqueantes -- en vez de invisibles. Ningún modelo por defecto está hardcodeado: exigir la variable de entorno del modelo en cada caso evita que un default fijo empiece a fallar silenciosamente cuando un provider deprecia ese modelo, y nada corre sin que un humano decida explícitamente el modelo a usar. Distinto de T056's `tests/ai/adapters/test_provider_adapters.py` (`httpx.MockTransport`, sin red, cubre parsing/errores por cada wire format) -- esa suite ya prueba "el adapter interpreta bien la respuesta que *creemos* que la API real da"; esta prueba "la API real de verdad da esa respuesta", que solo puede confirmarse con red y credenciales reales.

### T123 — Vault security audit
**Estado:** DONE
**Dep:** T047, T085  
Path traversal, arbitrary writes, `.obsidian`, deletion, conflicts, atomic writes y preservación de texto.

**Nota:** Auditoría de las 7 categorías del texto de la tarea contra el código ya existente (`vault_resolver.py`, `proposal_validator.py`, `apply_change_service.py`, `conflict_detection.py`, `atomic_writer.py`, `managed_sections.py`) y su cobertura de tests. 6 de 7 ya estaban sólidamente cubiertas (path traversal: `../`, `../../`, inyección de ruta absoluta, en `test_vault_resolver.py`; conflicts/atomic writes/preservación de texto: `test_apply_change_service.py`; deletion: `ProposalOperation` nunca tuvo variante delete). Un gap real encontrado y corregido: el chequeo de directorio ignorado en `ProposalValidator._check` (`app/services/proposal_validator.py`) usaba `operation.path.startswith(f"{d}/")`, que solo atrapa `.obsidian/`, `Templates/`, `Attachments/` en la RAÍZ de la ruta -- inconsistente con `markdown_scanner.py`'s propio escaneo, que ya comprueba cada componente de la ruta. Una ruta como `notes/.obsidian/concept_1.md` pasaba el chequeo sin ser detectada. Corregido para comprobar todos los componentes de la ruta (`PurePosixPath(operation.path).parts[:-1]`), igual que el scanner. Explotabilidad práctica limitada hoy (`_path_belongs_to_concept` ya restringe `create_file` a `{concept.id}.md` o al `obsidian_path` legítimo del concepto, nunca controlado por la IA), pero es un boundary de seguridad nombrado explícitamente por esta tarea y debía ser correcto independientemente de esa segunda restricción (defensa en profundidad, docs/AGENTS.md #6: la IA nunca controla rutas de escritura sin validación). Regresión añadida en `tests/services/test_proposal_validator.py`. También se añadió `test_proposal_operation_has_no_delete_variant` en `tests/domain/test_enums.py` (`ProposalOperation` no estaba cubierto ahí) fijando el conjunto exacto de 4 operaciones permitidas, para que una futura adición al enum no pueda introducir una capacidad de borrado sin forzar una decisión visible y deliberada.

### T124 — Secrets/security audit
**Estado:** DONE
**Dep:** T014, T108  
No secrets en Git/DB/log/frontend; loopback; prompt injection.

**Nota:** Auditoría de las 6 categorías del texto de la tarea. Git: barrido `git grep` del árbol trackeado buscando patrones de credenciales reales (prefijos `sk-`, claves AWS, bloques `PRIVATE KEY`) -- cero coincidencias; `.gitignore` ya cubre `.env`, `*.sqlite3*` y `/data/`. DB: `CredentialStore` (T014) solo usa el keyring del SO; `AIProviderConfig`/`ConfigStore` (verificado en `app/config/models.py`) solo persisten `credential_ref` (clave de lookup opaca), nunca el secreto -- confirmado en cada punto de escritura (`app/api/onboarding.py`) y lectura (`app/api/providers.py`, que además documenta explícitamente "Never returns `credential_ref`" en sus respuestas). Log: `grep` de `logger.`/`print(` cruzado con `credential|api_key|secret|password` en todo `backend/app` -- cero coincidencias. Loopback: el propio default de `uvicorn.Config` es `127.0.0.1` (verificado inspeccionando su firma), `DEVELOPMENT.md` nunca pasa `--host`, `run_e2e_backend.py` (T120) fija `127.0.0.1` explícitamente, y `app/main.py` ya restringe CORS a orígenes loopback únicamente con comentario explícito -- sin gap. Prompt injection: ya cubierto exhaustivamente por T059 (`tests/ai/test_security.py`) -- reutilizado, no reimplementado.

Frontend: único gap real encontrado. `CredentialModelStep.tsx` ya usaba `type="password"`/`autoComplete="off"`/estado React transitorio (nunca localStorage), pero solo limpiaba el credential del estado tras una validación EXITOSA -- en un intento fallido, la clave permanecía en memoria del componente hasta el siguiente submit o desmontaje. Corregido moviendo la limpieza a un bloque `finally` (se ejecuta siempre, éxito o fallo). Este archivo -- y el directorio `onboarding/` entero -- no tenía ningún test hasta ahora; se añadió `CredentialModelStep.test.tsx` cubriendo específicamente el comportamiento de seguridad (input `type=password`, limpieza tras éxito, limpieza tras fallo), sin intentar cubrir el resto del wizard de onboarding, fuera del alcance de esta auditoría.

### T125 — Documentation audit
**Estado:** DONE
**Dep:** T120–T124  
README, instalación, onboarding, providers, troubleshooting, arquitectura y testing.

**Nota:** `README.md` tenía un `## Status` desactualizado ("Early bootstrap") pese a 123/138 tareas hechas -- corregido con el conteo real y la fase actual. `DEVELOPMENT.md` ganó las 6 secciones que el texto de la tarea pide y que no existían: Onboarding (los 4 pasos reales del wizard, `frontend/src/onboarding/steps/`), Providers (tabla de los 7 ids de `provider_registry.py` con sus requisitos, más cómo se validan en vivo), Testing (las 5 suites reales -- unit/integration backend, E2E de bucle canónico T121, smoke de providers en vivo T122, unit frontend, E2E de navegador T120 -- con cuál corre por defecto y cuál en CI, ya que antes solo había un bloque `Quality gates` de 4 líneas sin explicar qué cubre cada cosa), Troubleshooting (9 errores reales con su causa, derivados de código real: tabla faltante sin migrar, CORS, `AI_UNAVAILABLE`, `VAULT_UNAVAILABLE`, keyring en Windows, etc.) y Architecture (el diagrama de capas de `docs/AGENTS.md` con la ubicación real de cada capa en `backend/app/`). Un gap real de documentación encontrado en el camino: `.env.example` presentaba `LEARNINGOS_HOST`/`LEARNINGOS_PORT` como si controlaran el bind real del servidor, pero nada en el comando de desarrollo documentado (`uv run uvicorn app.main:app --reload`) los lee -- son campos vivos de `Settings` (T014) que coinciden por casualidad con el default de uvicorn, no wiring real. Corregido el comentario para no inducir a error, sin tocar código (T125 es auditoría de documentación, no de features; el propio default de uvicorn ya es el correcto para T124's loopback binding).

### T126 — Release candidate v0.1.0
**Estado:** DONE
**Dep:** T125  
CI green, tests green, build green, working tree limpio y tag `v0.1.0`.

**Nota:** El working tree arrastraba, desde antes de esta serie de sesiones, ~18 archivos con drift de puro `ruff format` (comillas simples->dobles, colapso de llamadas multilínea) nunca tocados por el trabajo real de ninguna tarea -- dejados deliberadamente sin commitear en cada commit anterior para no mezclar diffs ajenos al scope de cada tarea. Verificado con `git diff` que el drift es 100% mecánico (sin cambios de lógica ni de schema en las dos migraciones afectadas) y que `uv run ruff format --check .` ya lo daba por correcto; comprobados de nuevo `pytest`/`ruff check`/`mypy` en verde, y commiteado aparte como `chore(backend): apply ruff format to pre-existing drift` -- el único commit de esta tarea. Confirmados en verde: CI (`gh run watch`), `uv run pytest` (808 passed, 6 skipped -- los 6 del smoke matrix de providers en vivo de T122, sin credenciales), `npm test` (51 passed), `npm run build`. Tag anotado `v0.1.0` creado sobre ese commit y pusheado a origin -- primera release candidate del MVP.

---

# Fase 13 — Post-MVP

No comenzar hasta T126:

### T127 — SQLite FTS
**Estado:** DONE

Full-text search over vault Markdown content: `GET /api/v1/vault/search?q=<query>` (docs/API_SPEC.md #2), backed by a `vault_files_fts` SQLite FTS5 virtual table.

**Nota:** El texto de la tarea (solo un título, sin dependencias ni criterios explícitos en TASKS.md) se interpretó con `docs/ROADMAP.md` Fase 10 ("SQLite FTS, embeddings, semantic retrieval, relevance scoring, context inspection") -- FTS es la base léxica de ese grupo, independiente de embeddings (T128) y no bloqueada por ellos. No confundir con "semantic similarity", la señal de ranking que `docs/AI_CONTRACTS.md` #12 ya lista como pendiente en `context_builder.py` -- esa es semántica (T128/T129), esta es léxica (coincidencia de palabras), una capacidad nueva y separada: buscar notas del vault por contenido, algo que la app no podía hacer en absoluto hasta ahora (`ContextBuilder` nunca lee contenido de notas; el único lugar que lee una nota real es `CuratorService`, y solo la nota objetivo de un concepto concreto).

Una tabla virtual FTS5 no es expresable como modelo declarativo de SQLAlchemy -- `app/persistence/models/vault_search.py` define el DDL crudo una sola vez (`VAULT_SEARCH_FTS_CREATE_SQL`) y lo reutiliza en dos sitios: un listener `after_create`/`after_drop` sobre `Base.metadata` (para que cada test que usa `Base.metadata.create_all()` la tenga automáticamente, sin tocar ningún test existente) y la migración `9ad53fa4ea88`. `VaultIndexer.reindex()` (T042) ya lee el contenido completo de cada archivo para hashearlo -- se aprovechó ese mismo punto para reconstruir por completo la fila FTS de cada path en cada escaneo (borrar + reinsertar), en vez de mantenerla sincronizada de forma incremental vía triggers de contenido externo de SQLite: más simple y correcto para una tabla que ya se reconstruye desde un escaneo completo en cada uso. A diferencia de `vault_files`, un archivo `missing` borra su fila FTS en vez de marcarla -- la búsqueda es una vista del contenido *actual*, no una auditoría histórica.

`VaultSearchService.search()` envuelve cada palabra de la consulta como su propia frase FTS5 literal (en vez de la query completa como una sola frase) -- así caracteres de operador de FTS5 (`"`, `*`, `-`, `AND`/`OR`/`NOT`) en la entrada del usuario nunca se interpretan como sintaxis ni pueden provocar un error, pero varias palabras siguen combinándose con AND (comportamiento por defecto de FTS5 para términos separados por espacio), así que "sql window" encuentra igual una nota que dice "window sql" -- envolver la query entera como una sola frase (primer intento, corregido tras fallar un test) habría exigido coincidencia exacta de orden, rompiendo la búsqueda multi-palabra normal.
### T128 — Embeddings
**Estado:** DONE

Genera y persiste un vector de embedding por archivo indexado del vault: `POST /api/v1/vault/embeddings/generate` (docs/API_SPEC.md #2), tabla `vault_embeddings`.

**Nota:** Igual que T127, el texto de la tarea era solo un título. Decisión de arquitectura real, no trivial: los embeddings necesitan un protocolo de proveedor de IA totalmente distinto al existente. `AIProvider.generate(request, response_model) -> BaseModel` (T017) está pensado para salida estructurada de chat completions casada con uno de los 7 roles de `AI_CONTRACTS.md`; un endpoint de embeddings devuelve vectores crudos para texto arbitrario, un wire protocol diferente por completo (Anthropic no tiene endpoint de embeddings en absoluto). Forzar embeddings a través de `AIProvider.generate()` habría exigido inventar un `AIRequest`/`response_model` sin significado real. Se creó en su lugar un protocolo paralelo y completo: `EmbeddingProvider` (`app/ai/embedding_protocol.py`, un solo método `embed(texts) -> list[list[float]]`, ya loteado), adapters (`MockEmbeddingProvider` determinista por hash SHA-256; `OpenAICompatibleEmbeddingAdapter` compartido por OpenAI/OpenRouter/NVIDIA NIM/OpenAI-compatible sobre `POST {base_url}/embeddings`, hermano del `_openai_compatible_base.py` de T051-T056 pero con endpoint y forma de request/response propios; `OllamaEmbeddingProvider` sobre el `/api/embed` nativo de Ollama), `EmbeddingOrchestrator` (hermano de `AIOrchestrator`, T057, registra en `ai_runs` con `role="embedding"` ya que no hay `AIRequest`/`response_model` que loguear) y `build_default_embedding_provider` (hermano de `build_default_provider`, T101, reutiliza credential_ref/base_url del provider de IA por defecto ya configurado -- no existe ninguna tarea de onboarding UI para elegir un "provider de embeddings" separado, e inventar esa superficie de configuración está fuera de alcance, mismo criterio que T118/T119).

`ProviderDescriptor` (T015) ganó `supports_embeddings: bool` -- capacidad de protocolo (Anthropic=False, el resto True), distinta de si ESTE despliegue tiene un modelo de embedding por defecto configurado. Solo 3 providers tienen un default real y funcionan de punta a punta: Mock (sin red, siempre funciona), Ollama (`nomic-embed-text`, local, sin coste) y OpenAI (`text-embedding-3-small`, estable y bien conocido). OpenRouter/NVIDIA NIM/OpenAI-compatible no tienen un id de modelo de embedding universal seguro que hardcodear (catálogos por cuenta o self-hosted) -- `NoDefaultEmbeddingModelError` documenta el hueco honestamente en vez de adivinar un modelo que podría dar 404, mismo patrón "documentar el hueco real" que T112/T118/T119/T121 ya establecieron.

Decisión de coste explícita: a diferencia de `vault_files_fts` (T127, gratis, local, reconstruida en cada `/vault/scan`), generar embeddings con un provider real cuesta dinero/cuota por archivo -- por eso `POST /vault/embeddings/generate` es una acción separada y explícita, nunca automática dentro de `/vault/scan`. `EmbeddingService.generate_for_vault()` compara `vault_files.content_hash` contra el hash guardado junto al último embedding de cada archivo y salta los que no cambiaron, así que ejecuciones repetidas son baratas. `vault_embeddings` es una tabla declarativa normal (a diferencia de la FTS5 de T127, un vector no necesita almacenamiento SQLite especial) con migración por autogenerate -- nota para el futuro dejada en esa migración: autogenerate contra la revisión de T127 también propone borrar y recrear las tablas internas de sombra de FTS5, que hay que quitar a mano porque no son parte de `Base.metadata`.

No incluye aún búsqueda por similitud (eso es T129, "Semantic retrieval" -- un paso deliberadamente separado en el propio texto del backlog); T128 es solo generación y persistencia.

### T129 — Semantic retrieval
**Estado:** DONE

Búsqueda por similitud de embeddings sobre el vault: `GET /api/v1/vault/search/semantic?q=<query>` (docs/API_SPEC.md #2), consume la infraestructura de T128.

**Nota:** Alcance deliberadamente acotado al mismo patrón que T127/T128: un endpoint de recuperación nuevo y aditivo, no una reescritura de `ContextBuilder`. `SemanticSearchService` (`app/services/semantic_search_service.py`) embebe la query con el `EmbeddingOrchestrator` actual, compara por coseno contra cada fila de `vault_embeddings` cuyo `model` coincide con el modelo de embedding vigente (mismo criterio de T128: vectores de modelos distintos son incomparables, así que una fila con modelo obsoleto se excluye en vez de romper el ranking), y devuelve los `limit` mejores resultados con su `title` (buscado en `vault_files_fts`, T127, para no duplicar lógica de extracción de título). Sin dependencia de numpy -- el backend no la tenía como dependencia y el volumen de notas de un vault no la necesita; similitud de coseno en Python puro. Ruta separada de `/vault/search` (léxica) a propósito: modos de fallo distintos (query FTS mal formada vs. provider de embeddings no disponible) y coste por query distinto (gratis/local vs. llamada de red real), fusionarlas habría ocultado cuál de las dos falló.

Se decidió explícitamente NO conectar esto a `ContextBuilder` (T060) pese a que `docs/AI_CONTRACTS.md` #12 lista "semantic similarity" como una de sus 6 señales de ranking y su propio docstring decía "out of scope -- no hay infraestructura de embeddings todavía" (ya desactualizado tras T128, corregido aquí). Conectarlo habría hecho que cada llamador existente de `get_context_builder()` (diagnóstico, ejercicios, evaluaciones de transferencia, proyectos, curator) dependiera de golpe de que el provider de IA por defecto soporte embeddings -- y Anthropic no los soporta, así que un despliegue funcionando sobre Anthropic se habría roto en silencio. Esa decisión (cableado real en el pipeline de contexto de IA, con manejo de fallo best-effort) es más grande y arriesgada que "añadir un endpoint de recuperación" y queda fuera de esta tarea, documentada en `docs/AI_CONTRACTS.md` #12 y en el docstring de `context_builder.py` para quien la retome.

### T130 — FSRS
**Estado:** DONE

Implementación real del algoritmo FSRS como `SchedulingStrategy` alternativa (docs/SPECS.md #17: "MVP uses simple spaced repetition. Future versions may use FSRS.").

**Nota:** Igual que T127/T128/T129, el texto de la tarea era solo un título; se ubicó el hueco real cruzando `docs/ROADMAP.md` Fase 11 ("Advanced learning: FSRS, knowledge graph UI, interview mode") con el propio swap point que T063 dejó preparado a propósito. `review_scheduler.py` (T063) ya definía `SchedulingStrategy` (Protocol con un único método `next_interval(previous, correctness) -> SchedulingResult`) y el `Review` entity ya tenía `stability`/`difficulty` sin usar (docs/DOMAIN_MODEL.md #11) -- exactamente para este momento. `FsrsScheduler` (`app/services/fsrs_scheduler.py`, nuevo) implementa ese mismo Protocol: modelo de memoria de dos parámetros (stability/difficulty) sobre una curva de olvido power-law, con los pesos por defecto de FSRS-4.5 publicados por el proyecto open-spaced-repetition. Es una reimplementación independiente de las fórmulas publicadas, no un port de ninguna librería concreta.

Dos adaptaciones necesarias al dominio existente, documentadas en el docstring del módulo: (1) FSRS puntúa cada repaso en una escala de 4 grados (Again/Hard/Good/Easy); esta app solo tiene `correctness` continuo (0..1, el mismo que ya usa `SimpleSpacedRepetitionScheduler`) -- `_grade_from_correctness` lo mapea a los 4 grados con límites que extienden el `SUCCESS_THRESHOLD=0.6` ya existente. (2) el Protocol `next_interval(previous, correctness)` no recibe reloj, así que el tiempo transcurrido desde el repaso anterior (necesario para estimar retrievability) se aproxima con `previous.interval_days` (el hueco que se programó) en vez de tiempo real transcurrido -- cambiar la firma del Protocol para pasar `now` habría roto el propio contrato que T063 fijó y su test `test_custom_strategy_is_used_ready_for_fsrs_style_swap`. Un `previous` Review sin `stability`/`difficulty` (programado por el scheduler MVP) se trata como si no hubiera historial -- FSRS arranca limpio con las fórmulas de primer repaso en vez de asumir una base inválida.

Decisión explícita de alcance, mismo criterio que T129 con `ContextBuilder`: `FsrsScheduler` NO se conecta como estrategia por defecto. `get_review_scheduler()` (`app/api/dependencies.py`) sigue construyendo `SimpleSpacedRepetitionScheduler` sin cambios -- cambiar el default habría alterado el comportamiento de intervalo de cada review existente en el sistema (18 archivos de test dependen de los intervalos deterministas exactos del MVP: `1.0`, `8.0`, `MIN_INTERVAL_DAYS`, `MAX_INTERVAL_DAYS`), una decisión de producto/retención distinta de "el algoritmo existe y está disponible". `FsrsScheduler` es ya un swap-in totalmente funcional (`ReviewScheduler(clock, ids, strategy=FsrsScheduler())`, probado en `test_fsrs_scheduler.py::test_fsrs_scheduler_is_a_drop_in_strategy_for_review_scheduler`) para quien decida activarlo explícitamente; conectarlo como default de producción queda para una tarea futura dedicada.

### T131 — Knowledge graph UI
**Estado:** DONE
**Dep:** T114  
Node-link graph rendering of a goal's concepts and relations.

**Nota:** Igual que T127-T130, el texto de la tarea era solo un título; se ubicó cruzando `docs/ROADMAP.md` Fase 11 ("Advanced learning: FSRS, knowledge graph UI, interview mode") con la propia nota de alcance que T113 (Roadmap view) ya dejó por escrito: "renders the node/edge graph as a readable list rather than a node-link diagram -- no other Phase 11 page attempts graph rendering yet". T131 es esa tarea: la primera visualización real de nodos-y-aristas de la app. `frontend/src/knowledge/KnowledgeGraph.tsx` (nuevo) es un componente SVG puro sin dependencia externa (el frontend no tenía -- ni tiene ahora -- ninguna librería de gráficos/diagramas; mismo criterio "sin dependencia nueva" que T129 aplicó en backend para similitud de coseno). Layout por niveles: nivel 0 = concepts sin prerequisito `PREREQUISITE_OF` dentro del set actual de nodos, cada otro concept se ubica una fila por debajo del más profundo de sus propios prerequisitos -- misma dirección de arista que `RoadmapView` (T113) ya interpreta (source = el prerequisito, target = el concept que lo necesita). Ciclos (no deberían darse, pero las relaciones pueden venir de IA y no están garantizadas acíclicas) se cortan con un set "en progreso": un concept que se referencia a sí mismo en su propia cadena cae a nivel 0 en vez de recursar indefinidamente.

No existe un endpoint HTTP "relations de todo un goal" (`GET /concepts/{id}/relations` es de a un concept), así que activar la vista Graph dispara un fetch en paralelo de las relaciones de cada concept ya cargado y las funde en el mismo cache `relationsById` que la vista de lista (T114) ya usaba de forma perezosa por fila -- misma llamada subyacente, solo eager en vez de on-expand. Al reusar `concepts` tal cual, el grafo respeta el filtro de `status` activo -- una arista cuyo otro extremo quedó fuera del filtro simplemente no se dibuja (el grafo solo puede dibujar nodos que tiene), verificado en navegador real filtrando a `mastered` y viendo el grafo reducirse a un solo nodo. Seleccionar un nodo reusa `toggleExpand`/un `ConceptDetailsPanel` extraído de `ConceptRow` -- un único camino de renderizado de detalle para ambas vistas (lista y grafo), incluido el botón "Start transfer assessment".

Verificado en navegador real sembrando concepts/relations directamente vía SQLite (mismo límite de `MockProvider` sin generación real de contenido vía IA fuera de tests que T113/T114/T115 ya documentaron): 3 concepts, una relación `PREREQUISITE_OF` y una `RELATED_TO` -- el grafo coloca "Common Table Expressions" (prerequisito) una fila arriba de "Window Functions" con flecha dirigida, "Subqueries" sin prerequisito queda en la fila superior junto a CTE, seleccionar un nodo muestra el panel de detalle correcto (mastery/confidence/retention/relations) y "Start transfer assessment" dispara la misma llamada real a `POST /goals/{id}/assessments` (falla con el mismo `MockProvider has no configured response for ExerciseGeneratorResponse` ya documentado, no un bug nuevo). 9 tests nuevos de Vitest (7 en `KnowledgeGraph.test.tsx` para layout/aristas/selección/truncado, 2 en `KnowledgeExplorer.test.tsx` para el flujo fetch-y-render del toggle) + 60/60 suite completa, `tsc -b` y `oxlint` limpios.

### T132 — Socratic mode
**Estado:** DONE
**Dep:** T103  
Turno interactivo con el rol de IA Tutor, en modo Socrático: `POST /sessions/{session_id}/tutor` (docs/API_SPEC.md #6).

**Nota:** Igual que T127-T131, el texto de la tarea era solo un título. El hueco real, a diferencia de T127-T131, no era "falta infraestructura nueva" sino "existe infraestructura sin usar": `TutorResponse` (`app/ai/contracts.py`) y el prompt `tutor.v1` (`app/ai/prompts.py`) llevaban definidos desde las tareas tempranas de la capa de IA (T017/T058) -- cada uno de los otros 5 roles de `AI_CONTRACTS.md` (planner, diagnostician, exercise_generator, evaluator, curator) ya tenía un service/route real; tutor era el único sin ningún consumidor, verificado por grep (`TutorResponse`/`tutor.v1` solo aparecían en los propios archivos de contrato y en tests de la capa de IA, nunca en un `api/*.py` o `services/*.py`). `SessionMode.SOCRATIC` (`app/domain/enums.py`) llevaba el mismo destino: un valor de enum reservado desde el modelado temprano de dominio, aceptado y persistido por `SessionApplicationService.create_session()` pero sin ningún efecto de comportamiento en ningún sitio.

`TutorService` (`app/services/tutor_service.py`, nuevo) cierra ambos huecos a la vez: consume `TutorResponse`/`tutor.v1` por primera vez, y le da a `SessionMode.SOCRATIC` su primer efecto real -- `.ask()` rechaza con `SessionNotSocraticError` cualquier sesión cuyo `mode` no sea `socratic` (nuevo, junto a `SessionNotFoundError`/`InactiveSessionError` reutilizados de `next_activity_service.py`, mismo criterio de no duplicar excepciones que T128 ya estableció). Sigue el mismo patrón de wiring que `ExerciseGeneratorService`/`TransferAssessmentService`: `ContextBuilder.build(goal_id, concept_id)` para contexto (prerequisitos, mistakes, práctica reciente -- exactamente los inputs que `AI_CONTRACTS.md` #6 declara para el tutor), `AIOrchestrator.generate(request, TutorResponse, session_id=session_id)` (pasando `session_id` para que `ai_runs` quede trazado a la sesión, a diferencia de `ExerciseGeneratorService` que no tiene sesión en su alcance).

Decisión de diseño deliberada: la app nunca fuerza `mode` (`explain|question|hint|feedback|reflection`) por código -- "AI proposes, the Learning Engine decides" (docs/SPECS.md) aquí significa que el engine decide la ESTRUCTURA (un `TutorResponse` válido) pero la estrategia instruccional real por turno sigue siendo juicio legítimo del modelo. En su lugar, el estilo Socrático se induce vía `AIRequest.constraints` (`{"style": "socratic", "instructions": SOCRATIC_STYLE_INSTRUCTION}`), un campo que `_prompt.py` ya serializaba al prompt de usuario sin cambios de adapter. Sin persistencia de diálogo propia -- el caller reenvía `history` completo en cada turno; un turno de tutor no genera `Evidence` (`docs/DOMAIN_MODEL.md` #6 no tiene un `source_type` "tutor"/"socratic") ni actualiza mastery, misma distinción "andamiaje interactivo, no loop evaluado" que `AI_CONTRACTS.md` traza entre Tutor y Evaluator.

Alcance explícitamente NO incluido, mismo criterio que T129/T130 de separar "la capacidad existe y es real" de "está conectada a todo lo que podría usarla": sin frontend. `SessionUI.tsx` (T115) no tiene selector de `mode` -- crea sesiones con `mode="guided"` fijo (nota propia de T115), así que hoy no hay ni siquiera un camino de UI para crear una sesión `socratic` de entrada. Construir un selector de modo más una UI de chat Socrático (turnos, historial, distintos renders por `mode` de respuesta) es un problema de UI bastante más grande que T131 (que reutilizó cada componente/ruta existente) y una decisión de diseño propia que no correspondía inventar dentro de esta tarea -- documentado en `docs/AI_CONTRACTS.md` #6 para quien la retome. `POST /sessions/{id}/tutor` es ya una ruta real, probada y usable directamente vía API mientras tanto.

12 tests nuevos (7 en `tests/services/test_tutor_service.py`, 5 en `tests/api/test_sessions.py`) + 901/901 suite completa (901 = 889 previos + 12 nuevos), ruff/mypy limpios.

### T133 — Teach-back mode
**Estado:** DONE
**Dep:** T103  
Genera un prompt de teach-back y lo evalúa por el pipeline normal de exercise/evaluación: `POST /goals/{goal_id}/teach-back`, `GET /teach-back/{teach_back_id}` (docs/API_SPEC.md #8).

**Nota:** Igual que T130-T132, el patrón era "existe infraestructura reservada sin usar", no "falta infraestructura". Tres puntos de enganche ya vivían en `app/domain/enums.py` desde el modelado temprano de dominio y nunca tuvieron efecto de comportamiento en ningún sitio (verificado por grep antes de empezar): `SessionMode.TEACH_BACK`, `ExerciseType.TEACH_BACK` y `EvidenceSourceType.TEACH_BACK`. El hallazgo más importante fue el último: `EvidenceCreationService.create_evidence()` (T074) hardcodeaba `source_type=EvidenceSourceType.EXERCISE` sin mirar nunca el `type` real del Exercise subyacente -- así que incluso si alguna vez se generaba un exercise `type=teach_back` (posible desde T071, `ExerciseType` ya incluía ese valor), su Evidence quedaba mal etiquetada como `exercise` igual que cualquier otra. Fix quirúrgico de una rama: `source_type = TEACH_BACK if exercise.type == ExerciseType.TEACH_BACK else EXERCISE`, sin tocar el resto de la lógica ni el comportamiento por defecto (los 22 tests previos del archivo siguen pasando sin cambios).

`TeachBackService` (`app/services/teach_back_service.py`, nuevo) es hermano directo de `TransferAssessmentService` (T089): sin rol de IA dedicado para "teach-back" entre los 7 contratos de `AI_CONTRACTS.md`, así que reutiliza `exercise_generator`/`exercise_generator.v1` sesgando `task` con una instrucción explícita, mismo patrón. Diferencia deliberada de su hermano: `TransferAssessmentService` deja `type` enteramente a criterio del modelo (un escenario de transferencia puede ser legítimamente cualquier `ExerciseType`); aquí la aplicación fuerza `Exercise.type=ExerciseType.TEACH_BACK` en el Exercise persistido sin importar qué devuelva el modelo -- a diferencia de "transfer" (que no es un `type`, es un estilo de escenario ortogonal), teach-back SÍ tiene un `ExerciseType` propio ya reservado para esto, así que forzarlo da una garantía estructural barata en vez de confiar en que el prompt baste. `TeachBackSessionService` (nuevo) es hermano de `AssessmentSessionService` (T105): mismo hueco de scaffolding FK (responder escribe Evidence cuyo `activity_id` exige una `Activity`/`Session` reales), misma solución de crear Session+Activity+Exercise juntos en un solo POST.

Diferencia de alcance deliberada frente a Assessment, más pequeña a propósito: sin servicio de completion dedicado. `AssessmentCompletionService` existe solo porque además computa un juicio pass/fail umbralizado de transfer/independence sobre la evaluación (T090); teach-back no tiene ningún juicio adicional equivalente que calcular, así que responder y evaluar reutilizan sin cambios `POST /sessions/{id}/activities/{id}/answer` (`AnswerFlowService`, T103) y `POST /sessions/{id}/complete` -- ninguna ruta nueva de answer/complete, solo create+get. `TeachBackSessionService.get_teach_back()` tampoco puede replicar el chequeo `activity.type != ActivityType.ASSESSMENT` de su hermano porque `ActivityType` no tiene (ni necesita) un valor teach-back propio -- la Activity usa el mismo `type=EXERCISE` que cualquier exercise activity, así que la identidad se verifica por el `mode` de la Session dueña en su lugar.

Efecto colateral honesto descubierto durante esta tarea, explícitamente fuera de alcance: `AssessmentCompletionService` (T090) también reutiliza `EvidenceCreationService.create_evidence()` sin cambios, así que la evidencia de assessments TAMBIÉN queda etiquetada `source_type=exercise` en vez de `EvidenceSourceType.ASSESSMENT` (que sigue sin uso en ningún sitio salvo `diagnostic_service.py`, un mapeo aparte). Es un bug real, preexistente a T133 y sin relación con teach-back -- corregirlo aquí habría sido scope creep sobre una tarea ya cerrada (T090/T105); queda anotado para quien lo retome en vez de arreglado de paso.

15 tests nuevos (2 en `tests/services/test_evidence_creation_service.py`, 4 en `tests/services/test_teach_back_service.py`, 5 en `tests/services/test_teach_back_session_service.py`, 4 en `tests/api/test_teach_back.py`) + 916/916 suite completa (916 = 901 previos + 15 nuevos), ruff/mypy limpios.

### T134 — Voice
**Estado:** DONE
**Dep:** T115  
Entrada por voz (dictado de respuesta) y salida por voz (leer el prompt en voz alta) en la Session UI, vía las Web Speech APIs nativas del navegador.

**Nota:** A diferencia de T130-T133, aquí no había ningún punto de enganche reservado en `enums.py` ni en ningún contrato -- "Voice" (docs/ROADMAP.md Fase 11) era terreno en blanco. La decisión de alcance real: NO es una capacidad de proveedor de IA (nada de endpoint de speech-to-text/text-to-speech en el backend, ningún adapter nuevo, ninguna credencial nueva) sino una capacidad **nativa del navegador** -- `SpeechRecognition`/`webkitSpeechRecognition` (entrada) y `SpeechSynthesis` (salida), ambas ya soportadas sin ninguna llamada de red ni coste, consistente con el principio local-first del proyecto y con la disciplina de "sin dependencia nueva" que el frontend ya mantenía (`package.json` seguía con solo react/react-dom/react-router-dom tras T131). Construir esto como capacidad de IA habría significado inventar un octavo rol en `AI_CONTRACTS.md` sin ningún proveedor real que lo soporte de forma consistente (Anthropic no tiene STT/TTS; solo algunos serían viables) -- desproporcionado para una sola tarea y contrario al criterio ya usado en T128 para embeddings (proveedores declaran capacidades reales, no se inventan).

Dos componentes nuevos en `frontend/src/shared/` (mismo patrón de componente compartido que `MasteryBar`, con su propio `voice.css`): `VoiceInputButton.tsx` (dictado -- botón que activa `SpeechRecognition`, no continuo/no interim, dispara `onTranscript` una vez por locución) y `ReadAloudButton.tsx` (lectura -- `SpeechSynthesisUtterance` estándar de la lib DOM de TypeScript, sin problema de tipado). `SpeechRecognition` no forma parte del DOM lib estándar de TypeScript (API no estandarizada formalmente, prefijo `webkit` en Safari) -- tipado mínimo propio (`SpeechRecognitionLike`) en vez de `any`. Ambos renderizan `null` cuando el navegador no expone la API (incluido jsdom por defecto, así que invisibles en toda la suite de tests existente sin cambiarla) -- mismo criterio de degradación elegante que el resto de la app ya usa (p.ej. límites de `MockProvider` fuera de tests).

Integrados en `SessionUI.tsx` (T115, única página con el loop de respuesta): `ReadAloudButton` junto al prompt de la actividad, `VoiceInputButton` junto al textarea de respuesta (el transcript se concatena al valor existente en vez de reemplazarlo, para permitir dictar en varias tandas). Verificado end-to-end lo que es verificable: 16 tests nuevos de Vitest (aserciones de render/click/toggle/callback con las Speech APIs stubbeadas) más los 6 tests existentes de `SessionUI.test.tsx` sin cambios (confirma que los botones no aparecen ni rompen nada cuando las APIs no existen, el caso jsdom). Fase "answering" de `SessionUI` no verificable en navegador real con datos sembrados por el mismo límite ya documentado en T113/T114/T115/T131 (`MockProvider` sin respuesta configurada fuera de tests automatizados) -- en su lugar se confirmó en el navegador real de esta sesión, vía consola, que `window.SpeechRecognition`/`webkitSpeechRecognition`/`speechSynthesis` existen y son detectables (`{hasSpeechRecognition: true, hasWebkitSpeechRecognition: true, hasSpeechSynthesis: true}`) -- la detección de features apuntará correctamente a un navegador Chromium real, no solo en jsdom mockeado.

10 tests nuevos (5 en `VoiceInputButton.test.tsx`, 5 en `ReadAloudButton.test.tsx`; los 6 de `SessionUI.test.tsx` quedan sin tocar) + 70/70 suite completa (70 = 60 previos + 10 nuevos), `tsc -b` y `oxlint` limpios.

### T135 — Browser extension
**Estado:** DONE
**Dep:** T081, T119  
Web clipper Manifest V3: guarda una selección de cualquier página como `ChangeProposal` pendiente (`extension/`, `POST /vault/clip`, docs/API_SPEC.md #2).

**Nota:** A diferencia de T130-T134, aquí no había NADA reservado en ningún doc (ni enum, ni contrato, ni mapeo obvio a una API del navegador como T134 tuvo con Web Speech) -- "Browser extension" (docs/ROADMAP.md Fase 11) era además un tipo de entregable estructuralmente distinto a T127-T134: no una ruta más del backend ni una página más del SPA, sino un artefacto separado (manifest + service worker) con su propia superficie de permisos, que plausiblemente tocaba la postura de seguridad ya existente (`main.py` fija `allow_origins` al origen exacto de Vite). Dada esa ambigüedad real y el cambio de forma del entregable, se preguntó al usuario antes de construir nada (`AskUserQuestion`): qué debía hacer la extensión en concreto, y si convenía acometerla ahora dado su tamaño/forma distintos. Usuario eligió "Web clipper" y "construir ahora, acotado pequeño".

Backend: `ClipService` (`app/services/clip_service.py`, nuevo) es un camino de creación de `ChangeProposal` paralelo y más pequeño que `ProposalValidator` (T081) -- deliberadamente NO lo reutiliza, porque `ProposalValidator._check()` exige que cada operación pertenezca a un concept ya existente (`path == concept.obsidian_path` o la convención `{concept.id}.md`), y un clip no tiene concept asociado todavía: es material fuente sin distillar, el mismo rol que cumple el propio web clipper de Obsidian (aterriza en un inbox, se organiza después). Cada clip crea un `CREATE_FILE` bajo `Clippings/<timestamp>-<slug>.md`; el frontmatter (source/title/clipped_at) se serializa con `yaml.safe_dump` en vez de f-string manual, para que URLs/títulos con `:`, comillas, etc. no puedan producir YAML inválido o inyectar campos. Reutiliza el pipeline de revisión existente sin cambios (`GET /vault/changes`, `POST /vault/changes/{id}/apply`/`reject`, Vault diff UI de T119) -- un clip nunca se escribe al vault directamente, mismo principio "input externo nunca muta estado, la app valida y el usuario aprueba" (docs/AGENTS.md #5/#9) aplicado a input del navegador en vez de salida de IA.

Extensión (`extension/`, nuevo directorio a nivel de repo, sibling de `backend/`/`frontend/`): Manifest V3 mínimo -- sin popup, sin options page, sin iconos custom (evita generar assets de diseño, fuera de alcance de esta sesión backend/frontend). Un único menú de clic derecho sobre texto seleccionado ("Save selection to Learning OS") vía `contextMenus`, feedback por badge del toolbar (`chrome.action.setBadgeText`, verde/rojo, se limpia solo a los 4s) en vez de `chrome.notifications` (que exige un `iconUrl` obligatorio -- otro asset que evitar). El service worker de background hace `fetch()` directo a `http://127.0.0.1:8000/api/v1` (puerto por defecto documentado en DEVELOPMENT.md, sin flag `--port`) -- decisión de arquitectura clave: un MV3 background service worker con `host_permissions` sobre el origen destino queda EXENTO de CORS (a diferencia de un content script o una popup page, que corren en el origen de la página visitada), así que enrutar cada request por este service worker significa que el `allow_origins` de `main.py` (bloqueado al origen exacto de Vite) nunca necesitó tocarse -- la superficie de seguridad existente queda intacta.

Verificado de las dos formas posibles: (1) extremo backend, real, de punta a punta -- servidor dev real en el puerto 8000, `curl` con el payload EXACTO que `background.js` envía, confirmado: crea el proposal con frontmatter YAML seguro, aparece en `/vault/changes`, se aplica y el archivo queda escrito en disco con el contenido correcto; también verificado el path de error (selección en blanco → 400 `VALIDATION_ERROR`, mismo shape que `background.js` parsea). (2) extremo extensión: NO instalable/verificable en el navegador de esta sesión -- `chrome://extensions` no es una URL alcanzable por las herramientas de automatización del Browser pane (rechazada explícitamente, "not a valid file path or URL"); `manifest.json` validado como JSON válido y `background.js` validado con `node --check` (sintaxis válida), documentados pasos de carga manual en DEVELOPMENT.md para quien lo pruebe con Chrome real. Límite honesto declarado, no ocultado.

11 tests nuevos backend (7 en `tests/services/test_clip_service.py`, 4 en `tests/api/test_vault.py`) + 931/931 suite completa (931 = 920 previos + 11 nuevos), ruff/mypy limpios.

### T136 — Obsidian plugin
**Estado:** DONE
**Dep:** T081, T119  
Plugin de Obsidian que lista `ChangeProposal` pendientes con botones Apply/Reject en un panel lateral, dentro de la propia app (`obsidian-plugin/`, consume `GET/POST /vault/changes*` ya existentes).

**Nota:** Igual que T135, sin nada reservado en ningún doc y un tipo de entregable estructuralmente distinto (plugin corriendo dentro del proceso Electron de Obsidian, no una ruta más del backend ni una página del SPA). Se preguntó al usuario antes de construir nada (`AskUserQuestion`): "revisar cambios pendientes dentro del vault" vs. "widget de reviews/progreso"; eligió la primera -- trae el mismo loop de revisión que ya existe en la Vault diff UI (T119) al propio Obsidian, en vez de una pestaña de navegador aparte.

A diferencia de T135, esta tarea NO añadió nada al backend -- `GET /vault/changes`, `POST /vault/changes/{id}/apply`, `POST /vault/changes/{id}/reject` ya existían íntegros desde T081/T119 y el plugin simplemente los consume tal cual; cero endpoints nuevos, cero tests de backend nuevos. Todo el trabajo de esta tarea es un artefacto nuevo (`obsidian-plugin/main.js`/`manifest.json`/`styles.css`), JS plano escrito a mano sin bundler/TypeScript (Obsidian carga `main.js` directo vía `require` de CommonJS) -- mismo criterio "sin tooling de build nuevo para algo tan pequeño" que T135 aplicó a la extensión. Usa `requestUrl` de la propia API de Obsidian en vez de `fetch` -- documentado por Obsidian específicamente porque evita la aplicación de CORS del renderer, mismo razonamiento que llevó a T135 a enrutar todo por el background service worker de la extensión en vez de un content script.

Verificación: igual que T135, no instalable en el navegador de esta sesión (Obsidian es una app Electron aparte, ni siquiera alcanzable como `chrome://` lo fue para la extensión) -- validación estática (`node --check main.js`, JSON válido de `manifest.json`) más el hecho de que los tres endpoints que consume son exactamente los mismos, sin cambios, que T081/T119 ya prueban extensivamente y que T135 además verificó de punta a punta contra un servidor real (crear → listar → aplicar). Sin test harness JS nuevo (Jest u otro) para un único archivo de ~120 líneas -- desproporcionado para el alcance pedido, mismo criterio que T135 (que tampoco tiene tests JS propios para `background.js`). Límite honesto declarado, no ocultado.

Sin tests nuevos (backend sin cambios) -- 931/931 suite completa sin regresión, `node --check`/JSON válidos en los dos archivos del plugin.

### T137 — Code execution sandbox
**Estado:** DONE
**Dep:** ninguna (sin persistencia, sin AI, sin vault)  
Petición directa del usuario ("continue with T137", 2026-09-24) para el título suelto de Fase 11. Consola SQL "try it": el usuario ejecuta su propio SQL contra una base SQLite en memoria desechable, ve el resultado real, antes de responder un ejercicio.

**Nota:** A diferencia de T135/T136 (tipo de entregable ambiguo pero de bajo riesgo), "code execution sandbox" es ambiguo Y de alto riesgo -- ejecutar código es una frontera de seguridad real (aislamiento, límites de recursos, qué lo dispara), no solo una elección de formato de artefacto. Se preguntó al usuario (`AskUserQuestion`, dos preguntas) antes de escribir nada: (1) para qué sirve -- consola "try it" informativa vs. el Evaluator ejecutando código para calificar vs. ambas; (2) qué puede ejecutar y con qué aislamiento -- SQL en SQLite en memoria vs. Python en subproceso vs. multi-lenguaje con contenedores. Usuario eligió las dos opciones recomendadas: consola "try it" (informativa, nunca alimenta evaluación -- docs/AGENTS.md #9, mastery sigue derivado solo de evidencia AI-evaluada) + SQL únicamente contra SQLite en memoria (ni subprocess propio ni Docker -- docs/AGENTS.md #25, "no añadas infraestructura prematuramente").

Diseño (`app/services/sql_sandbox_service.py`, nuevo, sin dependencias -- ni domain, ni persistence, ni AI): cada llamada abre su propia conexión SQLite `:memory:`, la descarta al terminar -- nunca toca el engine real de la app ni ningún archivo. La única vía de escape de un `:memory:` normal es `ATTACH DATABASE 'ruta' AS nombre`, que SÍ podría abrir un archivo real -- denegada explícitamente vía el callback `set_authorizer` de `sqlite3` (verificado con test real, no solo documentado). `load_extension` (código nativo arbitrario) permanece deshabilitado por omisión -- nunca se llama `enable_load_extension(True)`. Límite de pared de 5s vía `threading.Timer` + `conn.interrupt()`; resultado capado a 200 filas (`truncated` si excede); hasta 50 statements por envío, 20.000 caracteres máx.

El punto no trivial: `sqlite3.Connection.execute()` solo permite UN statement -- un script con DDL de setup + INSERT + SELECT final (el caso real de "prueba tu query") necesita partirse en statements individuales primero. `_split_statements()` (función pura, muy testeada: 6 tests dedicados) recorre carácter a carácter respetando comillas (con escape de comilla doblada), comentarios de línea `--` y de bloque `/* */`, para que un `;` dentro de un string o comentario nunca cuente como límite de statement -- solo el statement final que produce filas (si las produce) se devuelve.

API (`app/api/sandbox.py`, nuevo): `POST /sandbox/sql` (docs/API_SPEC.md #16). Un SQL en blanco/sobredimensionado es 400 `VALIDATION_ERROR`; un error de SQL real (sintaxis, tabla inexistente, ATTACH denegado) es un 200 normal con `error` poblado -- igual que una respuesta de examen incorrecta no es un error HTTP, un error de SQL del propio usuario tampoco lo es.

Frontend: `SqlSandbox.tsx` (nuevo, `frontend/src/shared/`, mismo patrón de componente compartido colapsable que T134) -- un toggle "Try it: run SQL" junto al formulario de respuesta. Integrado solo en `SessionUI.tsx` (el loop principal), no en `AssessmentUI.tsx`/`ProjectView.tsx` -- mismo criterio de alcance que T134 ("única página con el loop").

Verificado real de punta a punta: servidor `uvicorn` real (no solo `TestClient`) -- `curl` contra el proceso real confirma script de 3 statements (CREATE+INSERT+SELECT) devuelve filas correctas, `ATTACH DATABASE` devuelve `"not authorized"`, SQL en blanco devuelve 400. No se sembró una sesión real de punta a punta en el navegador para el click-through de la UI -- el DB de desarrollo real del usuario solo tiene goals en estado `draft` (sin roadmap/diagnóstico), y generar una sesión completa habría requerido llamadas reales a IA y dejado más datos de prueba en su entorno real; límite honesto declarado en vez de fabricar una sesión falsa, cubierto en su lugar por tests de componente que ejercitan el toggle/ejecución/error contra fetch mockeado más una aserción de que el botón aparece dentro de `SessionUI` real.

21 tests nuevos backend (17 en `test_sql_sandbox_service.py` -- 11 del servicio + 6 del splitter puro --, 4 en `test_sandbox.py`) + 974/974 suite backend completa (974 = 953 previos + 21 nuevos) y 77/77 suite frontend completa (77 = 74 previos + 3 nuevos en `SqlSandbox.test.tsx`; `SessionUI.test.tsx` gana una aserción dentro de un test existente, no un test nuevo), ruff/mypy/tsc/oxlint limpios.

### T138 — Git integration
**Estado:** DONE
**Dep:** T044 (write_note), T083 (ApplyChangeService)  
Petición directa del usuario ("continue with T138", 2026-09-24) para el último título suelto de Fase 11. Commit automático y opt-in en el propio historial git del vault, uno por archivo, cada vez que la app aplica un cambio.

**Nota:** A diferencia de T137 (ambigüedad real, sin ningún ancla en los docs), "Git integration" resultó tener una especificación de facto ya escrita: docs/AGENTS.md #22 ("Git -- Si Git está presente: nunca reset, nunca force push, nunca borrar trabajo ajeno, nunca sobrescribir cambios sucios ajenos. Los commits automáticos son opt-in") lee como la lista de restricciones de exactamente esta funcionalidad, no como una regla genérica de higiene del agente -- por eso se procedió sin `AskUserQuestion` esta vez, a diferencia de T135/T136/T137, y se documenta aquí el razonamiento en vez de preguntarlo.

Diseño (`app/services/vault_git_service.py`, nuevo, sin dependencias de domain/AI/persistence -- solo `subprocess` + `VaultResolver`): `is_git_repo()` (`git rev-parse --is-inside-work-tree`) y `commit_file(path, message)`, que hace `git add -- <archivo>` seguido de `git commit -m ... -- <archivo>` -- nunca `git add -A` ni `git commit -a`, para que un cambio sin commitear en OTRO archivo del mismo repo (el usuario editando a mano en Obsidian mientras la app aplica un cambio) nunca quede arrastrado al commit de la app (docs/AGENTS.md #22, verificado con test real: `git status --porcelain` sigue mostrando el archivo ajeno como `??` después). Nunca reset, nunca force-push, nunca push a ningún remoto en absoluto -- solo historial local, mismo alcance "aplicación local" que el resto (docs/AGENTS.md #19/#25). Best-effort: `commit_file` nunca lanza excepción -- "no es un repo git", "git no está instalado", "nada que commitear" son todos `False`, mismo patrón de colaborador-opcional-defensivo que `MasteryCurationTriggerService` (T139) y del mismo modo no puede convertir un `apply()` ya exitoso en un fallo.

Integración: único punto de integración es `ApplyChangeService.apply()` -- justo después de marcar el proposal `APPLIED`, si tiene un `VaultGitService` opcional inyectado, intenta el commit del path exacto que acaba de escribir. Config: `AppConfig.git_auto_commit: bool = False` (mismo patrón opt-in que `language` de T140), leído por `get_apply_change_service` para decidir si construye el `VaultGitService` o pasa `None`. Nuevo `PATCH /settings/git-auto-commit` (docs/API_SPEC.md #15) junto al ya existente `GET/PATCH /settings/language`; `GET /settings` gana además `git_available` (informativo, de solo lectura -- si el vault configurado YA es un repo git ahora mismo, independiente de si el opt-in está activado) vía `is_vault_a_git_repo()` en `dependencies.py`, mismo patrón defensivo try/except HTTPException que `_build_curation_trigger` (T139) para que nunca rompa `GET /settings` solo porque el vault no está configurado todavía.

Frontend: `SettingsView.tsx` gana un checkbox "Git auto-commit", deshabilitado con explicación cuando `git_available` es `false` -- no se puede activar un ajuste que no podría hacer nada todavía.

Verificado con tests reales contra `git` real (no mocks) -- `test_vault_git_service.py` y los nuevos casos de `test_apply_change_service.py` hacen `git init` real en un `tmp_path`, aplican un cambio, y confirman con `git log`/`git status --porcelain` reales que el commit existe con el mensaje correcto y que un archivo ajeno sin commitear sigue intacto. No se probó contra el vault real del usuario ni se repuntó su `vault_path` real para un click-through en navegador -- mismo criterio que T137 de no tocar su entorno de desarrollo real solo para verificación; la cobertura real vino de subprocess `git` genuino en vez de mocks, que es la parte que de verdad importaba probar.

15 tests nuevos backend (7 en `test_vault_git_service.py`, 3 en `test_apply_change_service.py`, 3 en `test_dependencies.py`, 2 en `test_settings.py`) + 989/989 suite backend completa (989 = 974 previos + 15 nuevos) y 80/80 suite frontend completa (80 = 77 previos + 3 nuevos en `SettingsView.test.tsx`), ruff/mypy/tsc/oxlint limpios.

**Hallazgo sin resolver, fuera de alcance de esta tarea:** `docs/ROADMAP.md` Fase 11 lista explícitamente "interview mode" junto a FSRS/knowledge graph UI/Socratic/teach-back/voice/browser extension/Obsidian plugin/code execution sandbox/Git integration -- los otros nueve tienen tarea (T130-T138), pero "interview mode" nunca recibió número de tarea y sigue sin implementar. `docs/DOMAIN_MODEL.md` línea 249 ya reserva `interview` como valor de `SessionMode` (mismo patrón enum-reservado-y-muerto que `socratic`/`teach_back` tenían antes de T132/T133), así que el hueco de dominio ya existe, solo falta el servicio/contrato de IA/ruta que lo active -- probablemente un rol de IA nuevo (entrevista técnica simulada) sin contrato propio todavía en `docs/AI_CONTRACTS.md`. No se implementa aquí porque no fue lo pedido; queda documentado para quien decida retomarlo.

### T139 — Auto-curate the vault note when a concept becomes mastered
**Estado:** DONE
**Dep:** T080, T081, T075  
Petición directa del usuario (2026-09-23), no del backlog de Fase 13: cada vez que un concepto se confirma como aprendido (`ConceptStatus.MASTERED`), se propone automáticamente crear/ampliar su nota en Obsidian, en vez de dejarlo a una llamada manual.

**Nota:** Investigación previa a escribir código (siguiendo el mismo patrón de esta sesión: no adivinar, comprobar qué existe). Hallazgo clave, ya señalado explícitamente por la propia nota de T121: `CuratorService` (T080) y `ProposalValidator` (T081) estaban completos desde hace muchas tareas pero **nunca invocados desde ningún flujo de aplicación** -- "a real gap... documented here for whoever decides where curator should fire in production." Esta tarea es esa decisión.

Diseño: `MasteryCurationTriggerService` (nuevo, `app/services/mastery_curation_trigger_service.py`) recibe el status ANTERIOR y el `Concept` YA actualizado, y solo actúa en una transición real (`previous_status != MASTERED and updated.status == MASTERED`) -- nunca en cada evidencia posterior de un concepto ya dominado (coste de IA evitable, cero información nueva), pero SÍ vuelve a dispararse si el concepto cae por debajo de `mastered` y lo recupera más tarde (un segundo punto de síntesis es información genuinamente nueva -- así es como la nota "se va ampliando" tal como pidió el usuario, no una foto fija de una sola vez).

`MasteryUpdateService.update_mastery()` (T075) es el único punto de integración necesario: ya leía el concept ANTES de recalcularlo, así que detectar la transición ahí evita duplicar "leer status viejo, llamar a update_mastery, comparar" en sus 4 llamadores independientes (`AnswerFlowService`, `AssessmentFlowService`, `ProjectFlowService`, `ReviewFlowService` -- los 4 confirmados por grep, ninguno delega en otro). Gana un colaborador opcional `curation_trigger: MasteryCurationTriggerService | None = None` y se vuelve `async` (antes era sync); sus 4 llamadores pasan ahora `goal_id` además de `concept_id` y usan `await` -- `ReviewFlowService.complete_review` (antes sync) y su ruta en `api/reviews.py` pasan a `async def` como efecto colateral necesario, único cambio de firma pública de esta tarea.

Construcción defensiva en `app/api/dependencies.py` (`_build_curation_trigger`, nuevo): NUNCA debe romper el flujo principal de evidencia/mastery si el vault o el proveedor de IA no están configurados -- a diferencia de `get_vault_resolver`/`get_ai_orchestrator` (que lanzan `HTTPException` porque SU ruta sí depende de ellos), esta función reutiliza esas dos funciones tal cual pero atrapa `HTTPException` y devuelve `None` -- ningún caller de `get_mastery_update_service()` deja de funcionar solo porque el usuario aún no completó el onboarding de vault/IA, exactamente el mismo comportamiento que tenían antes de esta tarea.

Fix necesario descubierto al activar el flujo por primera vez en producción: `CuratorService`'s `target_path` fallback era `f"{concept.id}.md"` (plano, en la raíz del vault, p.ej. `concept_sql_window_functions.md`) -- no coincidía ni con la estructura por defecto de `docs/OBSIDIAN_SCHEMA.md` #2 (`03_Knowledge/Concepts/`) ni con su propio ejemplo de nomenclatura en #15 (`"Concept Title.md"`, por título, no por id). Inofensivo mientras el curator nunca se invocaba en producción; al activarlo aquí se vuelve un bug real e inmediatamente visible, así que se corrigió en la misma tarea: `sanitize_concept_filename()` (pública, compartida con `ProposalValidator._path_belongs_to_concept` para que ambos acuerden exactamente el mismo path) + `DEFAULT_CONCEPT_NOTES_DIR = "03_Knowledge/Concepts"`.

Verificación real de punta a punta (no solo tests aislados): script standalone contra SQLite real + `VaultResolver` real + `MockProvider` con `CuratorResponse` real -- concept STRONG→MASTERED por evidencia real, dispara el trigger, `CuratorService.propose()` real, `ProposalValidator.validate_and_persist()` real, proposal pendiente persistida con el path `03_Knowledge/Concepts/Window Functions.md` correcto, aprobada y aplicada exactamente como la ruta real `/vault/changes/{id}/apply`, archivo final verificado en disco con el contenido correcto (script de verificación, no committeado).

12 tests nuevos (7 en `test_mastery_curation_trigger_service.py`, 3 en `test_mastery_update_service.py`, 2 en `test_dependencies.py`) más ajustes en tests existentes para el nuevo convenio async/path (`test_proposal_validator.py`, `test_review_flow_service.py`, `test_curator_service.py`, `test_core_session_e2e.py`, `test_canonical_loop.py`) + 943/943 suite completa (943 = 931 previos + 12 nuevos), ruff/mypy limpios.

### T140 — App-wide language preference (app + AI-written vault notes)
**Estado:** DONE
**Dep:** T034 (ConfigStore/AppConfig), T080 (CuratorService)  
Petición directa del usuario (2026-09-24), no del backlog de Fase 13: una preferencia de idioma configurable que afecte tanto a la app como a las notas que la IA escribe en Obsidian.

**Nota:** Investigación previa (mismo patrón: comprobar qué existe antes de escribir código). Hallazgo: `AppConfig.language: str = "en"` (`app/config/models.py`) ya existía completo -- persistido por `ConfigStore`, expuesto en `GET /onboarding/status` -- desde antes de esta sesión, pero era un campo reservado-y-muerto igual que los enums de T130-T133: nada lo escribía tras el valor por defecto (sin endpoint de escritura post-onboarding) y nada lo leía para afectar una sola llamada a IA. Esta tarea cierra ambos lados.

Backend, lectura/escritura: `app/config/languages.py` (nuevo) define `SUPPORTED_LANGUAGES`, una lista cerrada (en/es/fr/de/pt/it) en vez de aceptar string libre -- el valor se inyecta más tarde en cada system prompt de IA, así que un string sin acotar aquí sería una segunda superficie de inyección de prompts (docs/AGENTS.md #14/#19) además de la ya cubierta por vault/context. `app/api/settings.py` (nuevo router, `GET /settings`, `PATCH /settings/language`) valida contra esa lista (400 `VALIDATION_ERROR` si no pertenece); `AppConfig.language` en sí sigue siendo un `str` simple sin cambios de tipo, para no romper el round-trip ya cubierto por `test_store.py` (que persiste valores arbitrarios como `"fr"` a través de `ConfigStore` sin ninguna validación en esa capa -- la validación vive en el límite de la API, no en el store).

Backend, efecto en IA: único punto de integración es `AIOrchestrator.generate()` (`app/ai/orchestrator.py`) -- gana un `language: str = "en"` de constructor (poblado en `get_ai_orchestrator` desde `config.language`) e inyecta `constraints["language"]` en cada `AIRequest` que no lo traiga ya explícito, antes de reenviarlo al provider. Cubre los 11 call-sites existentes (`tutor_service.py`, `curator_service.py`, `exercise_generator_service.py`, `evaluator_service.py`, `planner_service.py`, `diagnostic_service.py`, `project_generation_service.py`, `project_evaluation_service.py`, `transfer_assessment_service.py`, `teach_back_service.py`) sin tocar ninguno -- mismo razonamiento de "un solo punto de integración" que T139 aplicó a `MasteryUpdateService` en vez de sus 4 llamadores. `app/ai/adapters/_prompt.py::system_prompt` traduce `constraints["language"]` a UNA frase fija en inglés ("Respond in Spanish.", etc.) tomada del mismo diccionario cerrado -- nunca ecoa el valor crudo, así que un valor no reconocido (o hipotéticamente adversarial, si algún caller futuro construyera `constraints["language"]` a mano) degrada a no-op en vez de alcanzar el system prompt tal cual (verificado explícitamente con un payload de inyección en `test_prompts.py`, mismo patrón que `test_security.py` ya usa para vault/context).

Frontend: `SettingsView.tsx` (nuevo, `frontend/src/settings/`) -- página simple con un `<select>` poblado desde `supported_languages` (la app nunca hardcodea la lista, la pide al backend), guarda on-change vía `PATCH /settings/language`. Enlazada en `AppShell.tsx`/`routes.tsx` junto a Dashboard/Reviews/Vault, ruta `/settings` -- no forma parte del wizard de onboarding (es una preferencia cambiable en cualquier momento, no un paso con avance secuencial).

Verificado real de punta a punta en el navegador de esta sesión: servidor dev real (backend `uvicorn` + frontend Vite), `GET /settings` inicial (`en`), cambio a Spanish vía la UI real → "Saved." → confirmado por `curl` directo al backend que persistió (`language: "es"`), revertido a `en` al terminar para no dejar el entorno de desarrollo real del usuario en un estado distinto al que tenía.

14 tests nuevos: backend 10 (4 en `test_prompts.py`, 3 en `test_orchestrator.py`, 3 en `test_settings.py`) + 953/953 suite backend completa (953 = 943 previos + 10 nuevos); frontend 4 (3 en `SettingsView.test.tsx`, 1 en `routes.test.tsx`) + 74/74 suite frontend completa (74 = 70 previos + 4 nuevos). ruff/mypy/tsc/oxlint limpios.

### T141 — Interview mode
**Estado:** DONE
**Dep:** T132 (Socratic tutor turn)  
Petición directa del usuario ("start the interview mode task", 2026-09-24), spin-off del hallazgo señalado al cerrar T138: `docs/ROADMAP.md` Fase 11 nombra "interview mode" junto a los otros nueve ítems (FSRS...Git integration), pero nunca recibió número de tarea propio y `SessionMode.INTERVIEW` (docs/DOMAIN_MODEL.md, `app/domain/enums.py`) llevaba reservado y sin usar desde el modelado temprano de dominio -- mismo patrón enum-reservado-y-muerto que `SOCRATIC`/`TEACH_BACK` tenían antes de T132/T133.

**Nota:** A diferencia de T135/T136/T137 (ambigüedad real que requirió `AskUserQuestion`), el paralelismo estructural con T132 era lo bastante fuerte como para proceder sin preguntar: mismo contrato (`TutorResponse`), misma ruta (`POST /sessions/{session_id}/tutor`), mismo mecanismo de sesgo de estilo vía `constraints` en vez de un contrato nuevo -- la única decisión de producto real era qué instrucción de estilo distingue una entrevista simulada de un diálogo socrático (entrevista: preguntas de seguimiento que sondean el razonamiento, tono neutral, sin dar pistas salvo que el candidato esté totalmente bloqueado; socrático: una pregunta enfocada que guía al propio aprendiz hacia la respuesta, con ayuda progresiva).

`app/services/tutor_service.py`: `TUTOR_STYLE_INSTRUCTIONS: dict[SessionMode, str]` reemplaza el `if session.mode != SOCRATIC` de T132 por un mapa `{SOCRATIC: ..., INTERVIEW: ...}` -- una tercera modalidad tipo-tutor futura solo necesita una entrada nueva en el mapa, no una ruta/contrato/excepción nueva. `SessionNotSocraticError` se renombra a `SessionNotTutorableError` (nombrada por la capacidad, no por un modo concreto) -- único cambio de nombre público de esta tarea, propagado a `sessions.py` y a los tests existentes. El `constraints["style"]` enviado a la IA ahora es `session.mode.value` (`"socratic"` o `"interview"`) en vez de la cadena `"socratic"` fija que T132 había dejado hardcodeada.

Alcance deliberadamente igual de acotado que T132: sin UI de chat nueva (ni para socrático ni para entrevista) -- `docs/AI_CONTRACTS.md` #6 ya documentaba esto como "a distinct, larger task than wiring the contract itself, left for later" desde T132, y ninguna de las ocho tareas siguientes de Fase 11 lo retomó; esta tarea no cambia esa decisión de alcance, solo la hace explícita para los dos modos en vez de uno. Ningún archivo de `frontend/` se toca.

7 tests nuevos backend (1 renombrado + 4 nuevos en `test_tutor_service.py` -- respuesta de entrevista, constraints de estilo de entrevista --, 2 nuevos en `test_sessions.py` -- ruta de entrevista, rechazo renombrado) + 992/992 suite backend completa (992 = 989 previos + 3 nuevos -- el resto son renombrados, no nuevos), ruff/mypy limpios. Sin cambios ni tests nuevos en frontend (alcance explícitamente fuera, ver nota).

Con esto, Fase 11 — Advanced learning queda completa: los diez ítems de `docs/ROADMAP.md` (FSRS, knowledge graph UI, interview mode, Socratic mode, teach-back mode, voice, browser extension, Obsidian plugin, code execution sandbox, Git integration) tienen ahora tarea y estado DONE (T130-T141, sin T137→T141 estrictamente correlativo con el orden del bullet list, ya que dos de ellos -- T139, T140 -- fueron peticiones directas del usuario intercaladas fuera del backlog de Fase 13).

---

# Vertical slice mínimo recomendado

Para obtener rápidamente un producto real, priorizar:

```text
T001–T012
→ T013–T026
→ T027–T036
→ T037–T047
→ T048–T059
→ T060–T079
→ T080–T085
```

Ese punto ya demuestra el núcleo diferencial del producto: una sesión adaptativa que genera evidencia, modifica el estado de conocimiento y propone una actualización segura del vault.

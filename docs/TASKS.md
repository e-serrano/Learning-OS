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
**Estado:** BLOCKED — GitHub API devuelve 403: "Upgrade to GitHub Pro or make this repository public to enable this feature." El repositorio es privado en un plan Free; branch protection clásica no está disponible. Requiere que el usuario decida: pasar a GitHub Pro, o hacer el repositorio público. Ninguna de las dos se ha aplicado (cambio de facturación/visibilidad fuera de autonomía del agente).
**Dep:** T005  
PR requerido, checks de CI requeridos y sin force-push cuando la configuración de GitHub lo permita.

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
**Dep:** T066  
High leverage concepts, deferred topics y foco diagnóstico.

### T068 — Roadmap service
**Dep:** T067  
Nodos/dependencias; validar IDs, self-relations y ciclos.

---

# Fase 6 — Vertical slice de aprendizaje

### T069 — Session creation
**Dep:** T065, T068  
Crear sesión, modo y duración.

### T070 — Next activity
**Dep:** T064, T069  
Seleccionar objetivo/actividad y persistirla.

### T071 — Exercise generator
**Dep:** T048, T070  
Exercise con type, difficulty, concepts, success criteria, hints, solution, mistakes y transfer.

### T072 — Answer submission
**Dep:** T071  
Persistir attempt y confidence.

### T073 — Evaluator
**Dep:** T048, T072  
Evaluar correctness, reasoning, completeness, independence y transfer.

### T074 — Evidence creation
**Dep:** T073  
Convertir evaluación válida en evidence inmutable.

### T075 — Derived mastery update
**Dep:** T074, T061  
Recalcular mastery.

### T076 — Mistake update
**Dep:** T074, T062  
Crear/incrementar misconception.

### T077 — Review creation
**Dep:** T075, T063  
Programar review futura.

### T078 — Adaptive next activity
**Dep:** T075–T077  
Seleccionar siguiente actividad con razón explicable.

### T079 — Core session E2E
**Dep:** T069–T078  
MockProvider ejecuta goal → diagnostic → roadmap → session → exercise → answer → evaluation → evidence → mastery → mistake → review.

---

# Fase 7 — Consolidación Obsidian

### T080 — Curator service
**Dep:** T074, T046, T058  
Generar propuesta de conocimiento.

### T081 — Proposal validator
**Dep:** T080  
Validar operation, path, section, concept ID y límites.

### T082 — Diff approval API
**Dep:** T081  
Aprobar/rechazar propuestas.

### T083 — Apply approved change
**Dep:** T082, T044  
Escribir solo tras aprobación.

### T084 — Verify write
**Dep:** T083  
Releer, verificar contenido y actualizar índice.

### T085 — Knowledge E2E
**Dep:** T080–T084  
Session → proposal → diff → approval → Markdown actualizado sin perder texto.

---

# Fase 8 — Reviews y transferencia

### T086 — Today's reviews
**Dep:** T063, T077  
Query de reviews vencidas.

### T087 — Review completion
**Dep:** T086  
Responder, evaluar y reprogramar.

### T088 — Retention update
**Dep:** T087  
Usar evidencia de review para retention.

### T089 — Transfer assessment
**Dep:** T068, T073  
Generar situaciones nuevas, no copias del ejercicio.

### T090 — Assessment completion
**Dep:** T089  
Evaluar transferencia e independencia.

### T091 — Review/transfer E2E
**Dep:** T086–T090  
Concepto débil genera review y una transferencia posterior medible.

---

# Fase 9 — Projects

### T092 — Project generation
**Dep:** T089  
Proyecto práctico vinculado a conceptos.

### T093 — Project tasks
**Dep:** T092  
Tareas y criterios de éxito.

### T094 — Project submission
**Dep:** T093  
Registrar entregables/evidence.

### T095 — Project evaluation
**Dep:** T094  
Evaluar independencia y transferencia.

---

# Fase 10 — API completa

### T096 — Goal routes
**Dep:** T065  
Implementar endpoints de goals.

### T097 — Vault routes
**Dep:** T046  
Configure/scan/changes/apply/reject.

### T098 — Onboarding routes
**Dep:** T025  
Implementar contratos de onboarding.

### T099 — Provider configuration routes
**Dep:** T015–T018  
Leer configuración sin secretos y validar provider/model.

### T100 — Knowledge routes
**Dep:** T061  
Knowledge explorer y filtros.

### T101 — Roadmap routes
**Dep:** T068  
Generate/get/recalculate.

### T102 — Diagnostic routes
**Dep:** T066  
Start diagnostic.

### T103 — Session routes
**Dep:** T069–T078  
Start/get/next/answer/complete.

### T104 — Review routes
**Dep:** T086–T088  
Today/complete.

### T105 — Assessment routes
**Dep:** T089–T090  
Create/get/answer/complete.

### T106 — Project routes
**Dep:** T092–T095  
Create/list/get/task submit.

### T107 — Progress route
**Dep:** T061–T088  
Resumen de mastery, concepts, weak, reviews y sesiones.

### T108 — API error handling
**Dep:** T096–T107  
Códigos normativos: `VALIDATION_ERROR`, `NOT_FOUND`, `CONFLICT`, `VAULT_CONFLICT`, `VAULT_UNAVAILABLE`, `AI_UNAVAILABLE`, `AI_INVALID_OUTPUT`, `SESSION_STATE_ERROR`, `PERMISSION_DENIED`.

---

# Fase 11 — Frontend

### T109 — App shell
**Dep:** T011, T098  
Routing y navegación.

### T110 — Onboarding UI
**Dep:** T020–T024, T098  
Completar onboarding de vault/provider/model.

### T111 — Dashboard
**Dep:** T107  
Estado general y siguiente acción.

### T112 — Goal view
**Dep:** T096, T107  
Mastery, weak concepts, reviews y roadmap.

### T113 — Roadmap view
**Dep:** T101  
Dependencias y progreso.

### T114 — Knowledge explorer
**Dep:** T100  
Conceptos, evidence y weaknesses.

### T115 — Session UI
**Dep:** T103  
Actividad, respuesta, confidence, hints, feedback y next.

### T116 — Reviews UI
**Dep:** T104  
Completar reviews.

### T117 — Assessment UI
**Dep:** T105  
Transfer/final assessment.

### T118 — Projects UI
**Dep:** T106  
Proyecto y tareas.

### T119 — Vault diff UI
**Dep:** T097  
Before/after + approve/reject.

---

# Fase 12 — Release MVP

### T120 — Fresh-install E2E
**Dep:** T110  
Install → onboarding → vault → provider → goal.

### T121 — Full canonical-loop E2E
**Dep:** T079, T085, T091, T095, T119  
GOAL → DIAGNOSE → 80/20 → ROADMAP → LEARN → PRACTICE → FEEDBACK → ADAPT → CONSOLIDATE → REVIEW → TRANSFER → PROJECT → EVALUATE.

### T122 — Provider smoke matrix
**Dep:** T051–T056  
Mock en CI; Ollama/OpenAI/Anthropic/OpenRouter/NVIDIA/compatible en tests de entorno separado cuando haya credenciales.

### T123 — Vault security audit
**Dep:** T047, T085  
Path traversal, arbitrary writes, `.obsidian`, deletion, conflicts, atomic writes y preservación de texto.

### T124 — Secrets/security audit
**Dep:** T014, T108  
No secrets en Git/DB/log/frontend; loopback; prompt injection.

### T125 — Documentation audit
**Dep:** T120–T124  
README, instalación, onboarding, providers, troubleshooting, arquitectura y testing.

### T126 — Release candidate v0.1.0
**Dep:** T125  
CI green, tests green, build green, working tree limpio y tag `v0.1.0`.

---

# Fase 13 — Post-MVP

No comenzar hasta T126:

### T127 — SQLite FTS
### T128 — Embeddings
### T129 — Semantic retrieval
### T130 — FSRS
### T131 — Knowledge graph UI
### T132 — Socratic mode
### T133 — Teach-back mode
### T134 — Voice
### T135 — Browser extension
### T136 — Obsidian plugin
### T137 — Code execution sandbox
### T138 — Git integration

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

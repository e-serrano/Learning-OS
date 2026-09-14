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
**Estado:** DONE (almacenado en JSON local vía `ConfigStore`; se migrará a SQLite `app_settings` en T034, ver Dep de T027)
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
**Dep:** T015, T016  
Implementar adapters separados; Anthropic no se trata como OpenAI-compatible; NVIDIA permite endpoint configurable.

### T018 — Health/capability check
**Dep:** T017  
Validar endpoint, credencial, modelo y capacidad mínima de structured output sin enviar contenido del vault.

### T019 — Máquina de estados de onboarding
**Dep:** T013  
`WELCOME → VAULT → VAULT_SCAN → AI_PROVIDER → CREDENTIAL → MODEL → VALIDATE → FIRST_GOAL → COMPLETE`.

### T020 — UI selección de vault
**Dep:** T019  
Seleccionar directorio, validar existencia/lectura y mostrar resultado del scan read-only.

### T021 — UI selección de IA
**Dep:** T019, T015  
Cards para Ollama, OpenAI, Anthropic/Claude, OpenRouter, NVIDIA y OpenAI-compatible; explicar local/remoto y credenciales.

### T022 — UI credenciales/modelo
**Dep:** T014, T021  
Introducir credencial de forma segura, elegir modelo y no conservar el secreto en estado persistente del frontend.

### T023 — Validación de provider en onboarding
**Dep:** T018, T022  
`select → credential → model → test → result → continue`.

### T024 — Onboarding resumible
**Dep:** T019  
Reabrir aplicación y continuar desde el último paso válido.

### T025 — API onboarding
**Dep:** T013, T019  
`GET /onboarding/status`; `POST /onboarding/vault`; `POST /onboarding/ai-provider`; `POST /onboarding/ai-provider/validate`; `POST /onboarding/complete`.

### T026 — E2E onboarding
**Dep:** T020–T025  
Probar instalación limpia con Mock/Ollama y provider remoto simulado.

---

# Fase 2 — Dominio y SQLite

### T027 — SQLite engine
**Dep:** T010, T013  
Foreign keys ON, WAL, busy timeout, timestamps UTC.

### T028 — Alembic
**Dep:** T027  
Migración desde DB vacía y esquema versionado.

### T029 — Domain enums
**Dep:** T010  
Todos los enums de `DOMAIN_MODEL.md` como valores string canónicos.

### T030 — Domain entities
**Dep:** T029  
Goal, Concept, Skill, Evidence, Exercise, Attempt, Evaluation, Mistake, Review, Session, Activity, Project, Assessment.

### T031 — Value objects
**Dep:** T030  
Mastery 0..5, confidence/retention 0..100, importance/difficulty 1..5.

### T032 — Repository ports
**Dep:** T030  
Interfaces para goals, concepts, evidence, sessions, exercises, reviews, mistakes, vault, AI, clock e IDs.

### T033 — SQLAlchemy models
**Dep:** T028, T030  
Implementar tablas de `DATABASE_SCHEMA.md` sin usar ORM models como domain entities.

### T034 — Config tables migration
**Dep:** T033  
Crear `app_settings` y `ai_provider_configs`; credential_ref nunca contiene el secreto.

### T035 — Repositories
**Dep:** T032, T033  
CRUD y métodos de consulta necesarios; evidence append-only.

### T036 — Persistence tests
**Dep:** T035  
CRUD, FK, transacciones, rollback, append-only y migraciones.

---

# Fase 3 — Obsidian

### T037 — Vault resolver
**Dep:** T013  
Validar root y bloquear path traversal fuera del vault.

### T038 — Markdown scanner
**Dep:** T037  
Scan recursivo read-only; ignorar `.obsidian/`.

### T039 — Frontmatter parser
**Dep:** T038  
Parseo YAML tolerante a errores sin abortar todo el scan.

### T040 — Managed sections parser
**Dep:** T038  
`get_section`/`replace_section` para marcadores Learning OS.

### T041 — Hashing
**Dep:** T038  
SHA-256 por archivo.

### T042 — Vault index
**Dep:** T034, T041  
Persistir path, hash, tipo, managed ID, metadata, indexed_at y missing.

### T043 — Conflict detection
**Dep:** T042  
Si hash actual != hash indexado, no escribir y devolver `VAULT_CONFLICT`.

### T044 — Atomic writer
**Dep:** T040, T043  
Temp file mismo directorio → flush → atomic replace → reread → verify.

### T045 — Diff engine
**Dep:** T044  
Diff before/after legible para UI.

### T046 — Change proposals
**Dep:** T045  
Estados `pending/approved/rejected/applied/conflicted/failed`; operaciones limitadas.

### T047 — Obsidian tests
**Dep:** T037–T046  
Vault vacío/existente, malformed frontmatter, cambios externos, conflictos y preservación de texto del usuario.

---

# Fase 4 — AI

### T048 — Pydantic AI contracts
**Dep:** T010  
Implementar Planner, Diagnostic, Tutor, Exercise, Evaluator, Curator y Progress responses.

### T049 — AI orchestrator
**Dep:** T048, T017  
Punto único para provider calls y `ai_runs`.

### T050 — MockProvider
**Dep:** T048  
Respuestas deterministas para éxito, error, parcialidad, misconceptions y confidence.

### T051 — OllamaProvider
**Dep:** T017  
Endpoint configurable, default local `http://localhost:11434`.

### T052 — OpenAIProvider
**Dep:** T017  
API key segura, model configurable y structured output.

### T053 — AnthropicProvider
**Dep:** T017  
Protocolo Anthropic nativo para Claude.

### T054 — OpenRouterProvider
**Dep:** T017  
Endpoint y model configurables.

### T055 — NvidiaNimProvider
**Dep:** T017  
API key, endpoint y model configurables.

### T056 — OpenAICompatibleProvider
**Dep:** T017  
`base_url`, model y API key opcional.

### T057 — Retry policy
**Dep:** T049  
`validate → retry once → fallback → surface failure`; invalid output nunca muta estado.

### T058 — Prompt versioning
**Dep:** T049  
Crear `planner.v1`, `diagnostician.v1`, `tutor.v1`, `exercise_generator.v1`, `evaluator.v1`, `curator.v1`.

### T059 — AI security tests
**Dep:** T050, T057  
Prompt injection desde vault se trata como datos; probar output inválido y provider unavailable.

---

# Fase 5 — Learning engine

### T060 — Context builder
**Dep:** T035, T038  
Seleccionar contexto por goal, concept, prerequisites, mistakes y práctica; nunca vault completo por defecto.

### T061 — Mastery engine
**Dep:** T035, T048  
Aplicar fórmula configurable de `DOMAIN_MODEL.md`; AI no asigna mastery directamente.

### T062 — Mistake tracker
**Dep:** T035  
Agrupar misconceptions normalizadas y contar recurrencia.

### T063 — Review scheduler
**Dep:** T061  
Scheduler MVP determinista; dejar interfaz preparada para FSRS.

### T064 — Activity selector
**Dep:** T061–T063  
Priorizar importance, weakness, prerequisite, review, mistakes y transfer; exponer breakdown.

### T065 — Goal application service
**Dep:** T035, T060  
Crear goal y contexto inicial sin modificar vault automáticamente.

### T066 — Diagnostic service
**Dep:** T048, T060, T065  
Recall + application + transfer; generar evidence.

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

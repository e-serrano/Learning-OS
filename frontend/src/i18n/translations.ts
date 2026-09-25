/** UI copy dictionary (docs/TASKS.md T147, user request, 2026-09-24):
 * flat `"namespace.key"` strings rather than nested objects -- simplest
 * to grep/extend across ~20 components, avoids deep-object TS typing.
 *
 * Scope boundary, deliberate: this covers the app's OWN static copy
 * (nav, buttons, labels, headings, messages) -- never backend-controlled
 * enum/status values (goal/concept/proposal status, provider ids,
 * concept domains, relation kinds). Those come from the API as data, are
 * shown as-is regardless of UI language, and would need their own
 * separate enum-to-copy map to translate -- out of scope here, not an
 * oversight. AI-generated content (exercise prompts, tutor turns,
 * feedback) is a different, already-solved concern: `constraints.language`
 * (docs/TASKS.md T140, docs/AI_CONTRACTS.md #2) steers the model itself,
 * completely independent of this dictionary.
 *
 * Missing key falls back to the key itself (`useTranslation`'s `t()`) --
 * never throws, never shows blank text.
 */

export type Language = 'en' | 'es'

export const translations: Record<string, Record<Language, string>> = {
  // --- common (shared across many components) --------------------------
  'common.loading': { en: 'Loading…', es: 'Cargando…' },
  'common.couldNotReachBackend': {
    en: 'Could not reach the backend',
    es: 'No se pudo contactar con el backend',
  },
  'common.backToGoal': { en: '← Goal', es: '← Objetivo' },
  'common.backToDashboard': { en: '← Dashboard', es: '← Panel' },

  // --- nav (AppShell) ----------------------------------------------------
  'nav.dashboard': { en: 'Dashboard', es: 'Panel' },
  'nav.reviews': { en: 'Reviews', es: 'Repasos' },
  'nav.vault': { en: 'Vault', es: 'Vault' },
  'nav.settings': { en: 'Settings', es: 'Ajustes' },

  // --- dashboard -----------------------------------------------------
  'dashboard.title': { en: 'Dashboard', es: 'Panel' },
  'dashboard.allCaughtUp': {
    en: "You're all caught up -- no reviews due.",
    es: 'Estás al día -- no hay repasos pendientes.',
  },
  'dashboard.youHave': { en: 'You have', es: 'Tienes' },
  'dashboard.reviewsDue': { en: 'review due.', es: 'repaso pendiente.' },
  'dashboard.reviewsDuePlural': { en: 'reviews due.', es: 'repasos pendientes.' },
  'dashboard.reviewNow': { en: 'Review now', es: 'Repasar ahora' },
  'dashboard.concepts': { en: 'concepts', es: 'conceptos' },
  'dashboard.mastered': { en: 'mastered', es: 'dominados' },
  'dashboard.weak': { en: 'weak', es: 'débiles' },
  'dashboard.due': { en: 'due', es: 'pendientes' },
  'dashboard.newGoal': { en: '+ New goal', es: '+ Nuevo objetivo' },
  'dashboard.newGoalTitle': { en: 'New goal', es: 'Nuevo objetivo' },
  'dashboard.whatToLearn': {
    en: 'What do you want to learn?',
    es: '¿Qué quieres aprender?',
  },
  'dashboard.goalPlaceholder': {
    en: 'e.g. Advanced SQL for analytics',
    es: 'p. ej. SQL avanzado para análisis de datos',
  },
  'dashboard.targetLevel': { en: 'Target level', es: 'Nivel objetivo' },
  'dashboard.creating': { en: 'Creating…', es: 'Creando…' },
  'dashboard.createGoal': { en: 'Create goal', es: 'Crear objetivo' },

  // --- goal view -------------------------------------------------------
  'goalView.roadmap': { en: 'Roadmap', es: 'Hoja de ruta' },
  'goalView.knowledgeExplorer': { en: 'Knowledge explorer', es: 'Explorador de conocimiento' },
  'goalView.recentSessions': { en: 'recent sessions', es: 'sesiones recientes' },
  'goalView.reviewsDue': { en: 'reviews due', es: 'repasos pendientes' },
  'goalView.sessionMode': { en: 'Session mode', es: 'Modo de sesión' },
  'goalView.modeGuided': { en: 'Guided', es: 'Guiado' },
  'goalView.modeSocratic': { en: 'Socratic', es: 'Socrático' },
  'goalView.modeInterview': { en: 'Interview', es: 'Entrevista' },
  'goalView.startSession': { en: 'Start session', es: 'Iniciar sesión' },
  'goalView.startProject': { en: 'Start project', es: 'Iniciar proyecto' },
  'goalView.projects': { en: 'Projects', es: 'Proyectos' },
  'goalView.pauseGoal': { en: 'Pause goal', es: 'Pausar objetivo' },
  'goalView.markComplete': { en: 'Mark complete', es: 'Marcar completado' },
  'goalView.noConceptsGenerateRoadmap': {
    en: 'This goal has no concepts yet -- generate a roadmap first.',
    es: 'Este objetivo todavía no tiene conceptos -- genera antes una hoja de ruta.',
  },

  // --- roadmap ---------------------------------------------------------
  'roadmap.title': { en: 'Roadmap', es: 'Hoja de ruta' },
  'roadmap.notGenerated': {
    en: 'No roadmap has been generated for this goal yet.',
    es: 'Todavía no se ha generado una hoja de ruta para este objetivo.',
  },
  'roadmap.generate': { en: 'Generate roadmap', es: 'Generar hoja de ruta' },
  'roadmap.generating': { en: 'Generating…', es: 'Generando…' },
  'roadmap.recalculate': { en: 'Recalculate', es: 'Recalcular' },
  'roadmap.recalculating': { en: 'Recalculating…', es: 'Recalculando…' },
  'roadmap.requires': { en: 'Requires: ', es: 'Requiere: ' },

  // --- knowledge explorer ------------------------------------------------
  'knowledge.title': { en: 'Knowledge Explorer', es: 'Explorador de Conocimiento' },
  'knowledge.status': { en: 'Status', es: 'Estado' },
  'knowledge.all': { en: 'All', es: 'Todos' },
  'knowledge.view': { en: 'View', es: 'Vista' },
  'knowledge.list': { en: 'List', es: 'Lista' },
  'knowledge.graph': { en: 'Graph', es: 'Grafo' },
  'knowledge.noMatch': { en: 'No concepts match.', es: 'Ningún concepto coincide.' },
  'knowledge.loadingRelations': { en: 'Loading relations…', es: 'Cargando relaciones…' },
  'knowledge.noRelated': { en: 'No related concepts.', es: 'Sin conceptos relacionados.' },
  'knowledge.confidence': { en: 'confidence', es: 'confianza' },
  'knowledge.retention': { en: 'retention', es: 'retención' },
  'knowledge.nextReview': { en: 'Next review', es: 'Próximo repaso' },
  'knowledge.lastPracticed': { en: 'Last practiced', es: 'Última práctica' },
  'knowledge.startTransferAssessment': {
    en: 'Start transfer assessment',
    es: 'Iniciar evaluación de transferencia',
  },
  'knowledge.starting': { en: 'Starting…', es: 'Iniciando…' },

  // --- session ui --------------------------------------------------------
  'session.nothingToWorkOn': { en: 'Nothing to work on yet', es: 'Todavía no hay nada que hacer' },
  'session.noCandidates': {
    en: 'This goal has no activity candidates right now -- generate a roadmap and a diagnostic first.',
    es: 'Este objetivo no tiene actividades disponibles ahora mismo -- genera antes una hoja de ruta y un diagnóstico.',
  },
  'session.complete': { en: 'Session complete', es: 'Sesión completada' },
  'session.showHints': { en: 'Show hints', es: 'Mostrar pistas' },
  'session.hideHints': { en: 'Hide hints', es: 'Ocultar pistas' },
  'session.yourAnswer': { en: 'Your answer', es: 'Tu respuesta' },
  'session.confidence': { en: 'Confidence', es: 'Confianza' },
  'session.submitAnswer': { en: 'Submit answer', es: 'Enviar respuesta' },
  'session.submitting': { en: 'Submitting…', es: 'Enviando…' },
  'session.endSession': { en: 'End session', es: 'Terminar sesión' },
  'session.continue': { en: 'Continue', es: 'Continuar' },
  'session.finishSession': { en: 'Finish session', es: 'Finalizar sesión' },
  'session.finishing': { en: 'Finishing…', es: 'Finalizando…' },
  'session.scoreCorrectness': { en: 'Correctness', es: 'Corrección' },
  'session.scoreReasoning': { en: 'Reasoning', es: 'Razonamiento' },
  'session.scoreCompleteness': { en: 'Completeness', es: 'Completitud' },
  'session.scoreIndependence': { en: 'Independence', es: 'Independencia' },
  'session.scoreTransfer': { en: 'Transfer', es: 'Transferencia' },

  // --- tutor chat --------------------------------------------------------
  'tutorChat.concept': { en: 'Concept', es: 'Concepto' },
  'tutorChat.speakerTutor': { en: 'Tutor', es: 'Tutor' },
  'tutorChat.speakerYou': { en: 'You', es: 'Tú' },
  'tutorChat.typeResponse': { en: 'Type your response…', es: 'Escribe tu respuesta…' },
  'tutorChat.send': { en: 'Send', es: 'Enviar' },
  'tutorChat.sending': { en: 'Sending…', es: 'Enviando…' },
  'tutorChat.thinking': { en: 'Thinking…', es: 'Pensando…' },
  'tutorChat.noConcepts': {
    en: 'This goal has no concepts yet -- generate a roadmap first.',
    es: 'Este objetivo todavía no tiene conceptos -- genera antes una hoja de ruta.',
  },

  // --- reviews -----------------------------------------------------------
  'reviews.title': { en: 'Reviews', es: 'Repasos' },
  'reviews.allCaughtUp': {
    en: "You're all caught up -- no reviews due.",
    es: 'Estás al día -- no hay repasos pendientes.',
  },
  'reviews.of': { en: 'of', es: 'de' },
  'reviews.whatDoYouRecall': { en: 'What do you recall?', es: '¿Qué recuerdas?' },
  'reviews.confidence': { en: 'Confidence', es: 'Confianza' },
  'reviews.submit': { en: 'Submit', es: 'Enviar' },
  'reviews.submitting': { en: 'Submitting…', es: 'Enviando…' },
  'reviews.nextReviewIn': { en: 'Next review in', es: 'Próximo repaso en' },
  'reviews.day': { en: 'day', es: 'día' },
  'reviews.days': { en: 'days', es: 'días' },
  'reviews.retention': { en: 'retention', es: 'retención' },
  'reviews.nextReview': { en: 'Next review', es: 'Siguiente repaso' },
  'reviews.done': { en: 'Done', es: 'Hecho' },

  // --- assessment ----------------------------------------------------
  'assessment.transferAssessment': { en: 'Transfer assessment:', es: 'Evaluación de transferencia:' },
  'assessment.showHints': { en: 'Show hints', es: 'Mostrar pistas' },
  'assessment.hideHints': { en: 'Hide hints', es: 'Ocultar pistas' },
  'assessment.yourAnswer': { en: 'Your answer', es: 'Tu respuesta' },
  'assessment.confidence': { en: 'Confidence', es: 'Confianza' },
  'assessment.submitAnswer': { en: 'Submit answer', es: 'Enviar respuesta' },
  'assessment.submitting': { en: 'Submitting…', es: 'Enviando…' },
  'assessment.transfer': { en: 'Transfer', es: 'Transferencia' },
  'assessment.independence': { en: 'Independence', es: 'Independencia' },
  'assessment.demonstrated': { en: 'demonstrated', es: 'demostrada' },
  'assessment.notDemonstrated': { en: 'not demonstrated', es: 'no demostrada' },
  'assessment.scoreCorrectness': { en: 'Correctness', es: 'Corrección' },
  'assessment.scoreReasoning': { en: 'Reasoning', es: 'Razonamiento' },
  'assessment.scoreIndependence': { en: 'Independence', es: 'Independencia' },
  'assessment.scoreTransfer': { en: 'Transfer', es: 'Transferencia' },
  'assessment.completeAssessment': { en: 'Complete assessment', es: 'Completar evaluación' },
  'assessment.finishing': { en: 'Finishing…', es: 'Finalizando…' },
  'assessment.complete': { en: 'Assessment complete', es: 'Evaluación completada' },

  // --- project -------------------------------------------------------
  'project.tasksUnavailable': {
    en: "Tasks aren't available after leaving this page -- reopen it right after starting the project to submit deliverables.",
    es: 'Las tareas no están disponibles después de salir de esta página -- vuelve a abrirla justo después de iniciar el proyecto para enviar entregables.',
  },
  'project.deliverable': { en: 'Deliverable', es: 'Entregable' },
  'project.submit': { en: 'Submit', es: 'Enviar' },
  'project.submitting': { en: 'Submitting…', es: 'Enviando…' },
  'project.correctness': { en: 'correctness', es: 'corrección' },
  'project.independence': { en: 'independence', es: 'independencia' },
  'project.transfer': { en: 'transfer', es: 'transferencia' },

  // --- vault diff ui -------------------------------------------------
  'vault.title': { en: 'Vault Changes', es: 'Cambios en el Vault' },
  'vault.rescan': { en: 'Rescan vault', es: 'Re-escanear vault' },
  'vault.scanning': { en: 'Scanning…', es: 'Escaneando…' },
  'vault.noPending': { en: 'No pending changes.', es: 'No hay cambios pendientes.' },
  'vault.section': { en: 'Section:', es: 'Sección:' },
  'vault.before': { en: 'Before', es: 'Antes' },
  'vault.after': { en: 'After', es: 'Después' },
  'vault.newFile': { en: '(new file)', es: '(archivo nuevo)' },
  'vault.beforeUnavailable': {
    en: '(current content not available via this API)',
    es: '(contenido actual no disponible a través de esta API)',
  },
  'vault.approve': { en: 'Approve', es: 'Aprobar' },
  'vault.working': { en: 'Working…', es: 'Procesando…' },
  'vault.reject': { en: 'Reject', es: 'Rechazar' },

  // --- SQL sandbox -----------------------------------------------------
  'sandbox.tryIt': { en: 'Try it: run SQL', es: 'Pruébalo: ejecutar SQL' },
  'sandbox.hide': { en: 'Hide SQL sandbox', es: 'Ocultar sandbox de SQL' },
  'sandbox.sql': { en: 'SQL', es: 'SQL' },
  'sandbox.run': { en: 'Run', es: 'Ejecutar' },
  'sandbox.running': { en: 'Running…', es: 'Ejecutando…' },
  'sandbox.noResultSet': { en: 'Ran with no result set.', es: 'Ejecutado sin conjunto de resultados.' },
  'sandbox.showingFirst': { en: 'Showing first', es: 'Mostrando las primeras' },
  'sandbox.rows': { en: 'rows.', es: 'filas.' },

  // --- settings --------------------------------------------------------
  'settings.title': { en: 'Settings', es: 'Ajustes' },
  'settings.language': { en: 'Language', es: 'Idioma' },
  'settings.languageHint': {
    en: 'Applies to the app and to notes the AI writes into your Obsidian vault.',
    es: 'Se aplica a la app y a las notas que la IA escribe en tu vault de Obsidian.',
  },
  'settings.gitAutoCommit': { en: 'Git auto-commit', es: 'Auto-commit de Git' },
  'settings.gitAutoCommitHintAvailable': {
    en: 'Automatically commits each vault change the app applies, one commit per file.',
    es: 'Hace commit automáticamente de cada cambio que la app aplica al vault, un commit por archivo.',
  },
  'settings.gitAutoCommitHintUnavailable': {
    en: 'Your configured vault is not a git repository, so this is unavailable.',
    es: 'Tu vault configurado no es un repositorio git, así que esto no está disponible.',
  },
  'settings.saving': { en: 'Saving…', es: 'Guardando…' },
  'settings.saved': { en: 'Saved.', es: 'Guardado.' },
  'settings.aiProvider': { en: 'AI provider', es: 'Proveedor de IA' },

  // --- AI provider settings ---------------------------------------------
  'aiProvider.label': { en: 'AI provider', es: 'Proveedor de IA' },
  'aiProvider.endpointUrl': { en: 'Endpoint URL', es: 'URL del endpoint' },
  'aiProvider.model': { en: 'Model', es: 'Modelo' },
  'aiProvider.modelPlaceholder': {
    en: 'e.g. gpt-5, claude-sonnet-5, llama3',
    es: 'p. ej. gpt-5, claude-sonnet-5, llama3',
  },
  'aiProvider.apiKey': { en: 'API key', es: 'Clave de API' },
  'aiProvider.apiKeyHint': {
    en: 'Re-enter your key every time you save here, even just to change the model -- it is never stored in the browser or database, only sent once to the OS keyring (or the encrypted equivalent in Docker).',
    es: 'Vuelve a escribir tu clave cada vez que guardes aquí, aunque solo cambies el modelo -- nunca se guarda en el navegador ni en la base de datos, solo se envía una vez al keyring del sistema (o su equivalente cifrado en Docker).',
  },
  'aiProvider.saveAndTest': { en: 'Save & test connection', es: 'Guardar y probar conexión' },
  'aiProvider.testing': { en: 'Testing…', es: 'Probando…' },
  'aiProvider.connectionFailed': { en: 'Connection failed:', es: 'Conexión fallida:' },
  'aiProvider.connectedSuccessfully': { en: 'Connected successfully.', es: 'Conectado correctamente.' },

  // --- onboarding ------------------------------------------------------
  'onboarding.welcome': { en: 'Welcome to Learning OS', es: 'Bienvenido a Learning OS' },
  'onboarding.vaultIntro': {
    en: 'Point Learning OS at your Obsidian vault. It only reads it to count Markdown files -- nothing is modified during this scan.',
    es: 'Indica a Learning OS dónde está tu vault de Obsidian. Solo lo lee para contar archivos Markdown -- nada se modifica durante este escaneo.',
  },
  'onboarding.vaultPathLabel': { en: 'Vault folder path', es: 'Ruta de la carpeta del vault' },
  'onboarding.scanVault': { en: 'Scan vault', es: 'Escanear vault' },
  'onboarding.scanning': { en: 'Scanning…', es: 'Escaneando…' },
  'onboarding.foundMarkdownFile': { en: 'Found', es: 'Se encontró' },
  'onboarding.foundMarkdownFilePlural': { en: 'Found', es: 'Se encontraron' },
  'onboarding.markdownFile': { en: 'Markdown file', es: 'archivo Markdown' },
  'onboarding.markdownFiles': { en: 'Markdown files', es: 'archivos Markdown' },
  'onboarding.readErrors': { en: 'read error(s)', es: 'error(es) de lectura' },
  'onboarding.continue': { en: 'Continue', es: 'Continuar' },
  'onboarding.chooseDifferentFolder': {
    en: 'Choose a different folder',
    es: 'Elegir otra carpeta',
  },
  'onboarding.chooseProvider': { en: 'Choose an AI provider', es: 'Elige un proveedor de IA' },
  'onboarding.providerIntro': {
    en: 'Learning OS never has direct database or filesystem access -- it only proposes content through this provider. Local providers keep your data on this machine.',
    es: 'Learning OS nunca tiene acceso directo a la base de datos ni al sistema de archivos -- solo propone contenido a través de este proveedor. Los proveedores locales mantienen tus datos en esta máquina.',
  },
  'onboarding.runsLocally': { en: 'Runs locally', es: 'Corre localmente' },
  'onboarding.remoteApi': { en: 'Remote API', es: 'API remota' },
  'onboarding.requiresApiKey': { en: 'requires API key', es: 'requiere clave de API' },
  'onboarding.noApiKeyRequired': { en: 'no API key required', es: 'no requiere clave de API' },
  'onboarding.endpointUrl': { en: 'Endpoint URL', es: 'URL del endpoint' },
  'onboarding.connectProvider': { en: 'Connect', es: 'Conectar con' },
  'onboarding.apiKeyIntro': {
    en: 'The API key is sent once to store it in your OS keyring, then discarded -- it is never saved in this browser or in Learning OS’s database.',
    es: 'La clave de API se envía una vez para guardarla en el keyring del sistema y luego se descarta -- nunca se guarda en este navegador ni en la base de datos de Learning OS.',
  },
  'onboarding.model': { en: 'Model', es: 'Modelo' },
  'onboarding.modelPlaceholder': {
    en: 'e.g. gpt-5, claude-opus-5, llama3',
    es: 'p. ej. gpt-5, claude-opus-5, llama3',
  },
  'onboarding.apiKey': { en: 'API key', es: 'Clave de API' },
  'onboarding.testConnection': { en: 'Test connection', es: 'Probar conexión' },
  'onboarding.testing': { en: 'Testing…', es: 'Probando…' },
  'onboarding.back': { en: 'Back', es: 'Atrás' },
  'onboarding.connectionFailed': { en: 'Connection failed:', es: 'Conexión fallida:' },
  'onboarding.connectedSuccessfully': { en: 'Connected successfully.', es: 'Conectado correctamente.' },
  'onboarding.allSet': { en: "You're all set", es: 'Todo listo' },
  'onboarding.allSetSubtitle': {
    en: 'Vault and AI provider are configured. Learning OS is ready for your first goal.',
    es: 'El vault y el proveedor de IA están configurados. Learning OS está listo para tu primer objetivo.',
  },
  'onboarding.readyToGo': { en: 'Ready to go', es: 'Todo preparado' },
  'onboarding.readySubtitle': {
    en: 'Vault and AI provider are configured and validated.',
    es: 'El vault y el proveedor de IA están configurados y validados.',
  },
  'onboarding.finishSetup': { en: 'Finish setup', es: 'Finalizar configuración' },
  'onboarding.finishing': { en: 'Finishing…', es: 'Finalizando…' },

  // --- voice -------------------------------------------------------------
  'voice.speakAnswer': { en: 'Speak answer', es: 'Responder por voz' },
  'voice.stopListening': { en: 'Stop listening', es: 'Dejar de escuchar' },
  'voice.readAloud': { en: 'Read aloud', es: 'Leer en voz alta' },
  'voice.stopReading': { en: 'Stop reading', es: 'Dejar de leer' },

  // --- mastery bar ---------------------------------------------------------
  'masteryBar.mastery': { en: 'mastery', es: 'dominio' },
}

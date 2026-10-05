# Workspace Instructions for Autonomous AI Agents

## Mandatory System Startup Protocols (Permanent until user notice)

0. **Mandatory Antigravity Startup Daily Cron Activation**:
   - AT EVERY STARTUP of Antigravity or upon receiving any interaction when Antigravity initializes, the AI Agent MUST check running tasks (`manage_task list`).
   - If NO task with cron `0 8 * * *` and `isDaemon: true` is active, the agent MUST IMMEDIATELY invoke the `schedule` tool:
     - `CronExpression`: `0 8 * * *`
     - `IsDaemon`: `true`
     - `Prompt`: `Ejecutar la Auditoría y Optimización Diaria de Canales de Afiliados (08:00 AM). Pasos: 1) Ejecutar daily_affiliate_audit.py 24. 2) Auto-responder comentarios YouTube con Ollama. 3) Inspeccionar visualmente miniaturas con view_file. 4) Auditar concordancia de nicho. 5) Auto-healing de workflows fallidos. 6) Suite unitaria test_metadata_scripts.py. 7) Emitir informe diario en 7 bloques Caveman.`
   - In parallel, an OS-level systemd user timer (`affiliate-daily-audit.timer`) runs persistently at system boot.

## Mandatory Protocols for n8n Workflow Tasks

1. **Strict Single Execution Enforcement Rule**:
   - BEFORE launching any new execution (via Webhook, REST API, or script), you **MUST ALWAYS check and stop/cancel any existing running executions** of that workflow.
   - Use `tools/n8n_helper.py stop_all <workflow_id>` or kill lingering local processes. There MUST NEVER be more than 1 active execution running at the same time.

2. **Mandatory Reactive Notification Architecture**:
   - ALL created or modified n8n workflows MUST be built with reactive notification endpoints (HTTP Request nodes calling local notifier service or Error Triggers).
   - Workflows must automatically report completion (SUCCESS) or failures (ERROR) to the agent notifier, allowing autonomous error handling and reporting.

3. **Automatic Watch Mode Rule & Autonomous Self-Healing Loop**:
   - Every time you modify or edit an n8n workflow or fix a bug in this workspace, you **MUST IMMEDIATELY test your changes by running the test Webhook**.
   - Use `tools/webhook_tester.py <webhook_url> [workflow_id]` to trigger and automatically monitor the execution to completion.
   - You MUST remain in Watch Mode while the execution is running.
   - **Autonomous Diagnosis Protocol (Zero Guesswork)**: If an execution fails (`status: ERROR` or `CANCELED`), you MUST IMMEDIATELY query `execution_data` in SQLite (`/home/node/.n8n/database.sqlite`) to fetch the exact `lastNodeExecuted`, error `message`, line number, and `stack` trace before making any diagnosis.
   - **Autonomous Self-Correction**: Apply the surgical fix directly (fix Python backend scripts, update node `jsCode` in SQLite using single quotes `$('Node Name')`, or adjust container environment variables like `NODE_FUNCTION_ALLOW_BUILTIN=*` and `N8N_RESTRICT_FILE_ACCESS_TO=""`).
   - **Re-run & Verification Loop**: After applying a patch or container restart, IMMEDIATELY re-run `webhook_tester.py` and resume Watch Mode.
   - **Exit Criteria**: You may ONLY exit Watch Mode when the last execution launched finishes with **clean SUCCESS**. If it fails, repeat the self-healing loop autonomously.
   - Never leave an idle watch loop with no active work.

4. **No Trigger Modifications**:
   - NEVER alter, add, or delete Schedule/Cron triggers in n8n workflows or in SQLite. Always test via test Webhooks or the official n8n REST API (`tools/n8n_helper.py`).

5. **Workspace Tools**:
   - `n8n_helper.py`: Official REST API manager.
   - `webhook_tester.py`: Automated Webhook trigger & execution watcher.
   - `ffprobe_helper.py`: Video/audio stream metadata inspector.
   - `system_watchdog.py`: CPU/RAM and process watchdog.
   - `n8n_agent_notifier.py`: Agent local HTTP notification listener service.

6. **Strict Empirical Verification Rule (NEVER CLAIM WORKING BEFORE EMPIRICAL PROOF)**:
   - NEVER state or claim to the user that a fix or feature is "working" or "solucionado" without executing a full real test invocation first.
   - You MUST verify the exact output from the target external service/API (e.g. YouTube Data API HTTP response) confirming successful execution before reporting success.

7. **Mandatory YouTube Upload Node Parameter Verification Rule**:
   - ALWAYS verify the input payload of the `YT Upload YouTube` node directly (in execution run output/node data or n8n API) to ensure `Title` contains product name, `Description` is non-empty, and `Tags` match the exact product niche. Never rely solely on files on disk.

8. **Mandatory Generic Tool Impact Verification Rule**:
   - If you modify or edit a shared or generic tool/script located in `tools/` (e.g. `save_vs_youtube_metadata.py`, `generate_vs_short_metadata.py`, `generate_youtube_metadata.py`, `generate_youtube_tags.py`, `vs_script_enricher.py`), you **MUST ALWAYS execute a comprehensive test suite (such as `test_metadata_scripts.py`) across all active channel niches (Cocina, Limpieza, Calzado, Librería, etc.) BEFORE claiming completion or running production workflows**.
   - Verify that the modified tool produces valid, non-empty, category-neutral, and niche-accurate output for every workflow that imports or executes it.

9. **Mandatory 2-Phase Completion Protocol (Multi-Niche Tests + Real n8n Workflow SUCCESS)**:
   - **Phase 1 (Multi-Niche Unit Tests)**: Run the full test suite (`test_metadata_scripts.py` or niche unit tests) across all 4 active channel niches: **Cocina, Limpieza, Calzado, Librería**. MUST achieve 100% PASS across all 4 niches before proceeding.
   - **Phase 2 (Empirical n8n Workflow Run)**: Trigger an end-to-end execution of a real n8n workflow and monitor until completion in n8n's execution table (`/api/v1/executions/<id>`).
   - **Strict Loop Exit Condition**: The orchestrator and agents may ONLY claim completion and exit the self-healing loop when the real n8n workflow execution finishes with official status **`SUCCESS`** (`finished: true, status: 'success'`).
   - **Strict Prohibitions**:
     - NEVER report "ready" or exit the loop while an n8n execution is still `running`, failed with `error`, or waiting.
     - NEVER declare a modification complete based solely on isolated local bash test commands without full n8n engine verification.

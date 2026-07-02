# One-command Dev Start Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use nbl.subagent-driven-development (recommended) or nbl.executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-command Windows development launcher for the backend and frontend.

**Architecture:** Provide a PowerShell script under `scripts/` that starts backend and frontend dev servers in separate visible PowerShell windows from the repository root. Keep existing manual commands documented as fallback and avoid changing runtime app behavior.

**Tech Stack:** PowerShell, Uvicorn, Vite.

---

### Task 1: Add launcher script

**状态**
- [ ] 任务完成

**Dependencies:** None
**Parallelizable:** No (single script)

**Files:**
- Create: `scripts/start_dev.ps1`

- [ ] Create a PowerShell script with parameters for backend port, frontend port, and optional browser launch.
- [ ] Validate required paths: `backend/.venv/Scripts/python.exe` and `frontend/package.json`.
- [ ] Check whether backend/frontend ports are already listening and warn before opening duplicate windows.
- [ ] Start backend and frontend in separate visible PowerShell windows.

### Task 2: Document usage

**状态**
- [ ] 任务完成

**Dependencies:** Task 1
**Parallelizable:** No (depends on script name and flags)

**Files:**
- Modify: `README.md`

- [ ] Add the one-command path to Quick Start.
- [ ] Keep manual backend/frontend commands as fallback.

### Task 3: Verify

**状态**
- [ ] 任务完成

**Dependencies:** Task 1, Task 2
**Parallelizable:** No (final verification)

**Files:**
- Test: `scripts/start_dev.ps1`
- Test: `README.md`

- [ ] Run PowerShell parser validation on `scripts/start_dev.ps1`.
- [ ] Run script in dry-run mode.
- [ ] Run `git diff --check`.

---

**Execution Mode:** inline

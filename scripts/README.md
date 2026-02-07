# Project Management Scripts

This directory contains shell scripts for managing the GitHub Project (v2) board for the HVAC Occupancy Forecasting project. All scripts use the GitHub CLI (`gh`) and GraphQL API.

## Prerequisites

All scripts require:

- **GitHub CLI** (`gh`) - Install from https://cli.github.com/
- **jq** - JSON processor (`brew install jq` on macOS)
- **Authentication** - Run `gh auth login` with `project` scope

Verify prerequisites:
```bash
gh auth status
jq --version
```

---

## Scripts Overview

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `project_discover.sh` | Discover project fields and IDs | First, to understand project structure |
| `project_setup.sh` | Create/configure project fields | Once, during initial setup |
| `init_project_issues.sh` | Seed all project issues | Once, to populate the backlog |
| `project_update_item.sh` | Update individual issue fields | Ongoing, for manual field updates |
| `project_assign_sprints_and_dues.sh` | Bulk assign sprints and due dates | Weekly, for sprint planning |

---

## Script Details

### 1. `project_discover.sh`

**Purpose:** Discover all GitHub Project fields, their IDs, and available options.

**Usage:**
```bash
./scripts/project_discover.sh
```

**Environment Variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_ID` | auto-detect | Override the project ID |
| `ORG_NAME` | `DataWhisk` | GitHub organization name |
| `REPO_NAME` | `hvac-occupancy-forecasting` | Repository name |

**Output:**
- Structured summary of all project fields
- Field IDs for Status, Sprint, Phase, Due Date
- Option IDs for single-select fields
- Iteration IDs for Sprint field
- Export-ready environment variables

**Example Output:**
```
========================================
PROJECT FIELDS SUMMARY
========================================

Project: Task Manager
Project ID: PVT_kwDOD38Ugs4BOiS9

[SINGLE_SELECT] Status
  ID: PVTSSF_lADOD38Ugs4BOiS9zg9NcQA
  Options:
    - Todo (f75ad846)
    - In progress (47fc9ee4)
    - Done (98236657)

[ITERATION] Sprint
  ID: PVTIF_lADOD38Ugs4BOiS9zg9QVMo
  Iterations:
    - Sprint 1 (start: 2026-02-02, 7 days) [c3b1e79d]
    ...
```

---

### 2. `project_setup.sh`

**Purpose:** Create and configure required project fields (idempotent - safe to re-run).

**Usage:**
```bash
./scripts/project_setup.sh
```

**What it configures:**

| Field | Type | Values |
|-------|------|--------|
| Status | Single-select | Backlog, This Week, In Progress, Review, Done |
| Sprint | Iteration | Sprint 1-8 (7-day sprints starting from current week) |
| Phase | Single-select | Phase 1, Phase 2, Phase 3, Phase 4, Phase 5 |
| Due Date | Date | Uses existing "Target date" or creates "Due Date" |

**Environment Variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_ID` | auto-detect | Override the project ID |
| `ORG_NAME` | `DataWhisk` | GitHub organization name |
| `REPO_NAME` | `hvac-occupancy-forecasting` | Repository name |

**Notes:**
- Skips fields/options that already exist
- Sprint dates are calculated from the Monday of the current week
- Uses built-in "Assignees" field for ownership (custom user fields not supported in Projects v2)

---

### 3. `init_project_issues.sh`

**Purpose:** Create all project issues and add them to the GitHub Project board.

**Usage:**
```bash
./scripts/init_project_issues.sh
```

**What it creates:**

| Phase | Issues |
|-------|--------|
| Phase 1 - Setup | Repository structure, Project board, Initial data drop, Data dictionary, Exploration notebook |
| Phase 2 - Savings | Define savings rule, Implement on sample data, Document definition |
| Phase 3 - Pipeline | Data loading helpers, Merge/align data, Refactor notebooks |
| Phase 4 - Scale Up | Multi-month analysis, Presentation visualizations |
| Phase 5 - Forecasting | Baseline forecasting, Forecasting notebook, Control simulation |

**Configuration (hardcoded):**
```bash
OWNER="DataWhisk"
REPO="hvac-occupancy-forecasting"
PROJECT_ID="PVT_kwDOD38Ugs4BOiS9"
```

**Notes:**
- Creates issues with structured task lists and acceptance criteria
- Attempts to apply labels (falls back gracefully if labels don't exist)
- Automatically adds each issue to the project board

---

### 4. `project_update_item.sh`

**Purpose:** Add issues to the project and/or update their field values.

**Usage:**
```bash
# Full update with all fields
./scripts/project_update_item.sh \
  --issue 25 \
  --status "This Week" \
  --sprint 1 \
  --due-date 2026-02-14 \
  --phase "Phase 1"

# Just update status
./scripts/project_update_item.sh --issue 25 --status "In Progress"

# Just add to project without setting fields
./scripts/project_update_item.sh --issue 25 --add-only

# Assign an owner
./scripts/project_update_item.sh --issue 25 --owner "username"
```

**Options:**

| Option | Required | Description |
|--------|----------|-------------|
| `--issue NUM` | Yes | Issue number to update |
| `--status VALUE` | No | Set Status (Backlog, This Week, In Progress, Review, Done) |
| `--sprint NUM` | No | Set Sprint number (1, 2, 3, etc.) |
| `--due-date DATE` | No | Set Due Date (YYYY-MM-DD format) |
| `--phase VALUE` | No | Set Phase (Phase 1, Phase 2, Phase 3, Phase 4, Phase 5) |
| `--owner USER` | No | Assign owner (GitHub username) |
| `--add-only` | No | Only add to project, don't update fields |
| `-h, --help` | No | Show help message |

**Environment Variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_ID` | auto-detect | Override the project ID |
| `ORG_NAME` | `DataWhisk` | GitHub organization name |
| `REPO_NAME` | `hvac-occupancy-forecasting` | Repository name |

**Notes:**
- Idempotent: safe to re-run (won't duplicate project items)
- Validates field values before applying
- Shows helpful error messages with available options if invalid value provided

---

### 5. `project_assign_sprints_and_dues.sh`

**Purpose:** Bulk assign sprint iterations and due dates to all project items based on issue titles.

**Usage:**
```bash
# Auto-detect project and use configured sprints
./scripts/project_assign_sprints_and_dues.sh

# Specify project number explicitly
./scripts/project_assign_sprints_and_dues.sh 1
```

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `PROJECT_NUMBER` | auto-detect | GitHub Project number |
| `START_DATE` | from project config | Sprint start date (YYYY-MM-DD) |

**Sprint Mapping Logic:**

The script infers sprint assignment from issue titles using keyword matching:

| Sprint | Weeks | Keywords / Themes |
|--------|-------|-------------------|
| Sprint 1-2 | 1-2 | repository, setup, infrastructure, database schema, AWS storage, initial data, data dictionary, exploration notebook |
| Sprint 3-4 | 3-4 | research, model, opportunity for savings, savings rule, implement savings, multi-month, scaling |
| Sprint 5-6 | 5-6 | system design, data pipeline, loading helpers, merge/align, TOU, weather |
| Sprint 7-8 | 7-8 | baseline forecast, forecasting notebook, control simulation |

**Features:**
- **Discovery-first:** Fetches all project metadata before making changes
- **Idempotent:** Safe to re-run; skips items already correctly assigned
- **Preserves existing data:** Only sets due dates if missing
- **Cross-platform:** Works with both GNU and BSD date commands
- **Clear logging:** Shows every assignment decision

**Output:**
```
===========================================
           ASSIGNMENT SUMMARY              
===========================================
Issue  | Title                               | Sprint     | Due Date    
-------+-----------------------------------------+------------+--------------
#1     | Design the Database Schema              | Sprint 1   | 2026-02-08  
#12    | Initial data drop (sample dataset)      | Sprint 2   | 2026-02-15  
...
===========================================

=== Issues Assigned by Default (Ambiguous) ===
  ⚠️  #99: Some unclear issue title

[WARN] Review the above items and adjust if needed.
```

---

## Typical Workflow

### Initial Project Setup

```bash
# 1. Set up project fields (run once)
./scripts/project_setup.sh

# 2. Verify fields are configured correctly
./scripts/project_discover.sh

# 3. Seed all project issues (run once)
./scripts/init_project_issues.sh

# 4. Assign sprints and due dates
./scripts/project_assign_sprints_and_dues.sh
```

### Ongoing Sprint Management

```bash
# Weekly: Re-run sprint assignment after adding new issues
./scripts/project_assign_sprints_and_dues.sh

# Manual: Update individual issue
./scripts/project_update_item.sh --issue 25 --status "In Progress"

# Manual: Move to next sprint
./scripts/project_update_item.sh --issue 25 --sprint 3 --due-date 2026-02-22
```

### Adding a New Issue Mid-Sprint

```bash
# Create issue via gh CLI
gh issue create --title "New feature" --body "Description"

# Add to project and set fields
./scripts/project_update_item.sh \
  --issue 30 \
  --status "This Week" \
  --sprint 2 \
  --phase "Phase 2"
```

---

## Troubleshooting

### "Not authenticated with GitHub CLI"
```bash
gh auth login
# Select: GitHub.com → HTTPS → Authenticate with browser
# Ensure you grant 'project' scope
```

### "jq is not installed"
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt install jq
```

### "Sprint field not found"
Run `project_setup.sh` first to create required fields:
```bash
./scripts/project_setup.sh
```

### "Option 'X' not found"
Check available options:
```bash
./scripts/project_discover.sh | grep -A10 "Status\|Phase"
```

### Date calculation errors on macOS with Homebrew
If you have GNU coreutils installed via Homebrew, the scripts auto-detect and use GNU date syntax. If issues persist:
```bash
# Check which date command is in use
which date
date --version
```

---

## Environment Variables Reference

All scripts support these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_ID` | GitHub Project node ID | `PVT_kwDOD38Ugs4BOiS9` |
| `ORG_NAME` | GitHub organization | `DataWhisk` |
| `REPO_NAME` | Repository name | `hvac-occupancy-forecasting` |

Usage:
```bash
PROJECT_ID="PVT_xxx" ./scripts/project_discover.sh
ORG_NAME="MyOrg" REPO_NAME="my-repo" ./scripts/project_setup.sh
```

---

## File Structure

```
scripts/
├── README.md                           # This documentation
├── init_project_issues.sh              # Seeds all project issues
├── project_assign_sprints_and_dues.sh  # Bulk sprint/due date assignment
├── project_discover.sh                 # Discover project field IDs
├── project_setup.sh                    # Create/configure project fields
└── project_update_item.sh              # Update individual issue fields
```

---

## Attribution

Scripts generated with assistance from:
```
Co-Authored-By: Warp <agent@warp.dev>
```

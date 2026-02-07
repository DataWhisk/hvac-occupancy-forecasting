#!/usr/bin/env bash
#
# project_assign_sprints_and_dues.sh
# 
# Assigns sprint iterations and due dates to GitHub Project (v2) items.
# Uses GraphQL API to discover project structure and update items.
#
# The script maps issues to sprints based on their titles using keyword matching:
#   Sprint 1-2 (Week 1-2):  Repo/infra setup, initial data, exploration, data dictionary
#   Sprint 3-4 (Week 3-4):  Opportunity-for-savings, savings computation, scaling
#   Sprint 5-6 (Week 5-6):  System design, data pipeline, TOU/weather integration  
#   Sprint 7-8 (Week 7-8):  Baseline forecasting, control simulation
#   Sprint 9+  (Week 9+):   Polished visuals, final presentation
#
# Usage:
#   ./project_assign_sprints_and_dues.sh [PROJECT_NUMBER] [START_DATE]
#
# Arguments:
#   PROJECT_NUMBER - GitHub Project number (default: auto-detect first project)
#   START_DATE     - Sprint start date in YYYY-MM-DD format (default: use project's sprint config)
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated with project scopes
#   - jq installed for JSON processing
#
# Author: Generated for weekly demo milestone tracking
# Co-Authored-By: Warp <agent@warp.dev>

set -o pipefail

# ==============================================================================
# Configuration
# ==============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Arguments with defaults
PROJECT_NUMBER="${1:-}"
START_DATE="${2:-}"

# ==============================================================================
# Utility Functions
# ==============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Fail fast on errors
die() {
    log_error "$1"
    exit 1
}

# Calculate end date: start_date + duration_days - 1
# Usage: calculate_end_date "2026-02-02" 7 → "2026-02-08"
calculate_end_date() {
    local start_date="$1"
    local duration="$2"
    # End date is start + duration - 1 (e.g., 7-day sprint starting Feb 2 ends Feb 8)
    # Check for GNU date (works on Linux and macOS with coreutils)
    if date --version &>/dev/null; then
        # GNU date
        date -d "$start_date + $((duration - 1)) days" "+%Y-%m-%d"
    else
        # BSD date (native macOS)
        date -j -v+"$((duration - 1))"d -f "%Y-%m-%d" "$start_date" "+%Y-%m-%d"
    fi
}

# ==============================================================================
# Prerequisites Check
# ==============================================================================

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v gh &> /dev/null; then
        die "GitHub CLI (gh) is not installed. Install from https://cli.github.com/"
    fi
    
    if ! command -v jq &> /dev/null; then
        die "jq is not installed. Install with: brew install jq (macOS) or apt install jq (Linux)"
    fi
    
    # Check gh authentication
    if ! gh auth status &> /dev/null; then
        die "GitHub CLI is not authenticated. Run: gh auth login"
    fi
    
    log_success "Prerequisites OK"
}

# ==============================================================================
# Project Discovery
# ==============================================================================

discover_project() {
    log_info "Discovering GitHub Project..."
    
    # Get repo owner
    OWNER=$(gh repo view --json owner -q '.owner.login' 2>/dev/null) || die "Failed to get repo owner"
    
    # List projects
    local projects_json
    projects_json=$(gh project list --owner "$OWNER" --format json 2>/dev/null) || die "Failed to list projects"
    
    local project_count
    project_count=$(echo "$projects_json" | jq '.totalCount')
    
    if [[ "$project_count" -eq 0 ]]; then
        die "No projects found for owner: $OWNER"
    fi
    
    # If PROJECT_NUMBER not specified, use the first project
    if [[ -z "$PROJECT_NUMBER" ]]; then
        PROJECT_NUMBER=$(echo "$projects_json" | jq -r '.projects[0].number')
        log_warn "No project number specified, using first project: #$PROJECT_NUMBER"
    fi
    
    # Get project details
    PROJECT_ID=$(echo "$projects_json" | jq -r --argjson num "$PROJECT_NUMBER" '.projects[] | select(.number == $num) | .id')
    PROJECT_TITLE=$(echo "$projects_json" | jq -r --argjson num "$PROJECT_NUMBER" '.projects[] | select(.number == $num) | .title')
    
    if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "null" ]]; then
        die "Project #$PROJECT_NUMBER not found"
    fi
    
    log_success "Found project: \"$PROJECT_TITLE\" (ID: $PROJECT_ID)"
}

# ==============================================================================
# Field Discovery
# ==============================================================================

discover_fields() {
    log_info "Discovering project fields..."
    
    local fields_query='
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 30) {
            nodes {
              ... on ProjectV2Field {
                id
                name
                dataType
              }
              ... on ProjectV2IterationField {
                id
                name
                dataType
                configuration {
                  iterations {
                    id
                    title
                    startDate
                    duration
                  }
                }
              }
              ... on ProjectV2SingleSelectField {
                id
                name
                dataType
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }'
    
    FIELDS_JSON=$(gh api graphql -f query="$fields_query" -f projectId="$PROJECT_ID") || die "Failed to fetch fields"
    
    # Extract Sprint field (iteration type named "Sprint")
    SPRINT_FIELD_ID=$(echo "$FIELDS_JSON" | jq -r '.data.node.fields.nodes[] | select(.name == "Sprint" and .dataType == "ITERATION") | .id')
    
    if [[ -z "$SPRINT_FIELD_ID" || "$SPRINT_FIELD_ID" == "null" ]]; then
        die "Sprint field not found! Please create an Iteration field named 'Sprint' in your project."
    fi
    
    # Extract Due Date field (date type - look for "Target date" or "Due Date" or "Due date")
    DUE_DATE_FIELD_ID=$(echo "$FIELDS_JSON" | jq -r '.data.node.fields.nodes[] | select((.name == "Target date" or .name == "Due Date" or .name == "Due date") and .dataType == "DATE") | .id' | head -1)
    
    if [[ -z "$DUE_DATE_FIELD_ID" || "$DUE_DATE_FIELD_ID" == "null" ]]; then
        die "Due Date field not found! Please create a Date field named 'Target date' or 'Due Date' in your project."
    fi
    
    # Extract sprint iterations
    SPRINTS_JSON=$(echo "$FIELDS_JSON" | jq '.data.node.fields.nodes[] | select(.name == "Sprint") | .configuration.iterations')
    SPRINT_COUNT=$(echo "$SPRINTS_JSON" | jq 'length')
    
    if [[ "$SPRINT_COUNT" -eq 0 ]]; then
        die "No sprint iterations configured! Please add iterations to the Sprint field."
    fi
    
    log_success "Found Sprint field: $SPRINT_FIELD_ID ($SPRINT_COUNT iterations)"
    log_success "Found Due Date field: $DUE_DATE_FIELD_ID"
    
    # Print sprint summary
    echo ""
    echo "=== Sprint Configuration ==="
    echo "$SPRINTS_JSON" | jq -r '.[] | "  \(.title): \(.startDate) (\(.duration) days)"'
    echo ""
}

# ==============================================================================
# Item Discovery  
# ==============================================================================

discover_items() {
    log_info "Discovering project items..."
    
    local items_query='
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100) {
            nodes {
              id
              content {
                ... on Issue {
                  number
                  title
                  labels(first: 10) {
                    nodes { name }
                  }
                }
              }
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldDateValue {
                    date
                    field { ... on ProjectV2FieldCommon { name } }
                  }
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field { ... on ProjectV2FieldCommon { name } }
                  }
                  ... on ProjectV2ItemFieldIterationValue {
                    title
                    field { ... on ProjectV2FieldCommon { name } }
                  }
                }
              }
            }
          }
        }
      }
    }'
    
    ITEMS_JSON=$(gh api graphql -f query="$items_query" -f projectId="$PROJECT_ID") || die "Failed to fetch items"
    
    ITEM_COUNT=$(echo "$ITEMS_JSON" | jq '.data.node.items.nodes | length')
    log_success "Found $ITEM_COUNT project items"
}

# ==============================================================================
# Sprint Mapping Logic
# ==============================================================================

# Determine which sprint an issue belongs to based on title keywords
# Returns sprint number (1-8+) or 0 if ambiguous
determine_sprint() {
    local title="$1"
    local title_lower
    title_lower=$(echo "$title" | tr '[:upper:]' '[:lower:]')
    
    # Sprint 1-2 (Week 1-2): Repo/infra setup, initial data, exploration, data dictionary
    if echo "$title_lower" | grep -qE "(repository|repo|structure|filesystem|github project|setup|infrastructure|infra)"; then
        echo "1"
        return
    fi
    if echo "$title_lower" | grep -qE "(initial data|sample data|data drop|data dictionary|draft data)"; then
        echo "2"
        return
    fi
    if echo "$title_lower" | grep -qE "(exploration notebook|first exploration|occupancy vs hvac)"; then
        echo "2"
        return
    fi
    if echo "$title_lower" | grep -qE "(database schema|design.*database)"; then
        echo "1"
        return
    fi
    if echo "$title_lower" | grep -qE "(aws.*storage|storage method)"; then
        echo "1"
        return
    fi
    
    # Sprint 3-4 (Week 3-4): Opportunity for savings, savings computation, scaling
    if echo "$title_lower" | grep -qE "(opportunity.*saving|savings.*rule|define.*saving|savings definition)"; then
        echo "3"
        return
    fi
    if echo "$title_lower" | grep -qE "(implement savings|savings.*sample|savings.*computation|document savings)"; then
        echo "4"
        return
    fi
    if echo "$title_lower" | grep -qE "(multi-month|scaling|scale.*data)"; then
        echo "4"
        return
    fi
    
    # Sprint 5-6 (Week 5-6): System design, data pipeline, TOU/weather
    if echo "$title_lower" | grep -qE "(system design|design doc|architecture)"; then
        echo "5"
        return
    fi
    if echo "$title_lower" | grep -qE "(data pipeline|pipeline cleanup|loading helper|standardize.*data|data loading)"; then
        echo "5"
        return
    fi
    if echo "$title_lower" | grep -qE "(merge.*align|refactor.*notebook.*pipeline)"; then
        echo "6"
        return
    fi
    if echo "$title_lower" | grep -qE "(tou|weather|time.of.use)"; then
        echo "6"
        return
    fi
    
    # Sprint 7-8 (Week 7-8): Baseline forecasting, control simulation
    if echo "$title_lower" | grep -qE "(research.*model|transformer|lstm|profit model)"; then
        echo "3"  # Research tasks should come earlier
        return
    fi
    if echo "$title_lower" | grep -qE "(baseline forecast|forecasting code|revive.*forecast)"; then
        echo "7"
        return
    fi
    if echo "$title_lower" | grep -qE "(forecasting notebook)"; then
        echo "7"
        return
    fi
    if echo "$title_lower" | grep -qE "(control simulation|simulation notebook)"; then
        echo "8"
        return
    fi
    
    # Sprint 9+ (Week 9+): Visuals, presentation
    if echo "$title_lower" | grep -qE "(visualization|plot.*occupancy|presentation.*visual|polished.*visual)"; then
        echo "5"  # Visualization can come earlier
        return
    fi
    if echo "$title_lower" | grep -qE "(presentation|final.*present|demo)"; then
        echo "8"
        return
    fi
    
    # Default: return 0 to indicate ambiguous
    echo "0"
}

# Get sprint ID and end date for a given sprint number
get_sprint_info() {
    local sprint_num="$1"
    local sprint_title="Sprint $sprint_num"
    
    # Find sprint by title
    local sprint_info
    sprint_info=$(echo "$SPRINTS_JSON" | jq -r --arg title "$sprint_title" '.[] | select(.title == $title)')
    
    if [[ -z "$sprint_info" || "$sprint_info" == "null" ]]; then
        # Sprint doesn't exist, use the last available sprint
        log_warn "Sprint $sprint_num not found, using last available sprint"
        sprint_info=$(echo "$SPRINTS_JSON" | jq -r '.[-1]')
    fi
    
    local sprint_id start_date duration
    sprint_id=$(echo "$sprint_info" | jq -r '.id')
    start_date=$(echo "$sprint_info" | jq -r '.startDate')
    duration=$(echo "$sprint_info" | jq -r '.duration')
    
    local end_date
    end_date=$(calculate_end_date "$start_date" "$duration")
    
    echo "$sprint_id|$end_date|$(echo "$sprint_info" | jq -r '.title')"
}

# ==============================================================================
# Update Functions
# ==============================================================================

update_item_sprint() {
    local item_id="$1"
    local sprint_id="$2"
    
    local mutation='
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $iterationId: String!) {
      updateProjectV2ItemFieldValue(
        input: {
          projectId: $projectId
          itemId: $itemId
          fieldId: $fieldId
          value: { iterationId: $iterationId }
        }
      ) {
        projectV2Item { id }
      }
    }'
    
    gh api graphql -f query="$mutation" \
        -f projectId="$PROJECT_ID" \
        -f itemId="$item_id" \
        -f fieldId="$SPRINT_FIELD_ID" \
        -f iterationId="$sprint_id" > /dev/null 2>&1
}

update_item_due_date() {
    local item_id="$1"
    local due_date="$2"
    
    local mutation='
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $date: Date!) {
      updateProjectV2ItemFieldValue(
        input: {
          projectId: $projectId
          itemId: $itemId
          fieldId: $fieldId
          value: { date: $date }
        }
      ) {
        projectV2Item { id }
      }
    }'
    
    gh api graphql -f query="$mutation" \
        -f projectId="$PROJECT_ID" \
        -f itemId="$item_id" \
        -f fieldId="$DUE_DATE_FIELD_ID" \
        -f date="$due_date" > /dev/null 2>&1
}

# ==============================================================================
# Main Assignment Logic
# ==============================================================================

assign_sprints_and_dues() {
    log_info "Assigning sprints and due dates..."
    echo ""
    
    # Arrays to track assignments
    declare -a assignments=()
    declare -a ambiguous=()
    
    # Process each item
    local items_array
    items_array=$(echo "$ITEMS_JSON" | jq -c '.data.node.items.nodes[]')
    
    while IFS= read -r item; do
        local item_id issue_number issue_title current_sprint current_due
        
        item_id=$(echo "$item" | jq -r '.id')
        issue_number=$(echo "$item" | jq -r '.content.number // "N/A"')
        issue_title=$(echo "$item" | jq -r '.content.title // "Draft Item"')
        
        # Get current values
        current_sprint=$(echo "$item" | jq -r '.fieldValues.nodes[] | select(.field.name == "Sprint") | .title // empty' | head -1)
        current_due=$(echo "$item" | jq -r '.fieldValues.nodes[] | select(.field.name == "Target date") | .date // empty' | head -1)
        
        # Determine sprint assignment based on title
        local target_sprint_num
        target_sprint_num=$(determine_sprint "$issue_title")
        
        if [[ "$target_sprint_num" -eq 0 ]]; then
            # Ambiguous - assign to Sprint 1 and log warning
            target_sprint_num=1
            ambiguous+=("#$issue_number: $issue_title")
            log_warn "Ambiguous: #$issue_number \"$issue_title\" → defaulting to Sprint 1"
        fi
        
        # Get sprint info (ID and end date)
        local sprint_info sprint_id due_date sprint_title
        sprint_info=$(get_sprint_info "$target_sprint_num")
        sprint_id=$(echo "$sprint_info" | cut -d'|' -f1)
        due_date=$(echo "$sprint_info" | cut -d'|' -f2)
        sprint_title=$(echo "$sprint_info" | cut -d'|' -f3)
        
        # Check if update is needed (idempotent)
        local needs_sprint_update=false
        local needs_due_update=false
        
        if [[ "$current_sprint" != "$sprint_title" ]]; then
            needs_sprint_update=true
        fi
        
        # Only set due date if missing
        if [[ -z "$current_due" ]]; then
            needs_due_update=true
        fi
        
        # Perform updates
        if [[ "$needs_sprint_update" == "true" ]] || [[ "$needs_due_update" == "true" ]]; then
            local update_msg="Assigning issue #$issue_number → $sprint_title"
            
            if [[ "$needs_sprint_update" == "true" ]]; then
                update_item_sprint "$item_id" "$sprint_id" || {
                    log_error "Failed to update sprint for #$issue_number"
                    continue
                }
            fi
            
            if [[ "$needs_due_update" == "true" ]]; then
                update_item_due_date "$item_id" "$due_date" || {
                    log_error "Failed to update due date for #$issue_number"
                    continue
                }
                update_msg+=", Due $due_date"
            else
                update_msg+=" (due date already set: $current_due)"
            fi
            
            log_success "$update_msg"
        else
            log_info "No changes needed for #$issue_number (already: $sprint_title, $current_due)"
        fi
        
        # Track assignment for summary
        assignments+=("$issue_number|$issue_title|$sprint_title|${current_due:-$due_date}")
        
    done <<< "$items_array"
    
    # Print summary
    echo ""
    echo "==========================================="
    echo "           ASSIGNMENT SUMMARY              "
    echo "==========================================="
    printf "%-6s | %-45s | %-10s | %-12s\n" "Issue" "Title" "Sprint" "Due Date"
    echo "-------+-----------------------------------------------+------------+--------------"
    
    for assignment in "${assignments[@]}"; do
        local num title sprint due
        num=$(echo "$assignment" | cut -d'|' -f1)
        title=$(echo "$assignment" | cut -d'|' -f2)
        sprint=$(echo "$assignment" | cut -d'|' -f3)
        due=$(echo "$assignment" | cut -d'|' -f4)
        
        # Truncate title if too long
        if [[ ${#title} -gt 43 ]]; then
            title="${title:0:40}..."
        fi
        
        printf "#%-5s | %-45s | %-10s | %-12s\n" "$num" "$title" "$sprint" "$due"
    done
    
    echo "==========================================="
    
    # Warn about ambiguous items
    if [[ ${#ambiguous[@]} -gt 0 ]]; then
        echo ""
        echo -e "${YELLOW}=== Issues Assigned by Default (Ambiguous) ===${NC}"
        for item in "${ambiguous[@]}"; do
            echo "  ⚠️  $item"
        done
        echo ""
        log_warn "Review the above items and adjust if needed."
    fi
    
    echo ""
    log_success "Sprint and due date assignment complete!"
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    echo ""
    echo "============================================"
    echo "  GitHub Project Sprint & Due Date Assigner"
    echo "============================================"
    echo ""
    
    check_prerequisites
    discover_project
    discover_fields
    discover_items
    assign_sprints_and_dues
}

# Run main
main "$@"

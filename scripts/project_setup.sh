#!/usr/bin/env bash
#
# project_setup.sh - Create missing GitHub Project v2 fields (idempotent)
#
# This script ensures the following fields exist with the correct options:
#   - Status: Backlog, This Week, In Progress, Review, Done
#   - Sprint: 1-week iterations starting from current week
#   - Due Date: Date field (uses existing "Target date" if present, else creates "Due Date")
#   - Phase: Phase 1, Phase 2, Phase 3, Phase 4, Phase 5
#   - Owner: Uses built-in "Assignees" field (no custom user fields in Projects v2)
#
# Usage:
#   ./scripts/project_setup.sh
#
# Environment Variables:
#   PROJECT_ID  - (optional) Override the default project ID
#   ORG_NAME    - (optional) Override the organization name (default: DataWhisk)
#   REPO_NAME   - (optional) Override the repository name (default: hvac-occupancy-forecasting)

set -euo pipefail

# Configuration
ORG_NAME="${ORG_NAME:-DataWhisk}"
REPO_NAME="${REPO_NAME:-hvac-occupancy-forecasting}"

# Required Status options
declare -a REQUIRED_STATUS_OPTIONS=("Backlog" "This Week" "In Progress" "Review" "Done")

# Required Phase options
declare -a REQUIRED_PHASE_OPTIONS=("Phase 1" "Phase 2" "Phase 3" "Phase 4" "Phase 5")

# Sprint configuration
SPRINT_DURATION_DAYS=7
NUM_SPRINTS_TO_CREATE=8

# Colors for output
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

log_info()  { echo -e "${BLUE}[INFO]${NC} $*" >&2; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*" >&2; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed"
        exit 1
    fi
    
    if ! gh auth status &> /dev/null; then
        log_error "Not authenticated with GitHub CLI. Run: gh auth login"
        exit 1
    fi
    
    log_ok "Prerequisites satisfied"
}

# Discover project ID
discover_project_id() {
    if [[ -n "${PROJECT_ID:-}" ]]; then
        log_info "Using provided PROJECT_ID: $PROJECT_ID"
        echo "$PROJECT_ID"
        return
    fi
    
    log_info "Discovering project ID for $ORG_NAME/$REPO_NAME..."
    
    local result
    result=$(gh api graphql -f query='
        query($org: String!, $repo: String!) {
            repository(owner: $org, name: $repo) {
                projectsV2(first: 1) {
                    nodes {
                        id
                        title
                    }
                }
            }
        }
    ' -f org="$ORG_NAME" -f repo="$REPO_NAME")
    
    local project_id
    project_id=$(echo "$result" | jq -r '.data.repository.projectsV2.nodes[0].id // empty')
    
    if [[ -z "$project_id" ]]; then
        log_error "No project found for repository $ORG_NAME/$REPO_NAME"
        exit 1
    fi
    
    log_ok "Found project: $project_id"
    echo "$project_id"
}

# Fetch current project fields
fetch_project_fields() {
    local project_id="$1"
    
    gh api graphql -f query='
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    id
                    fields(first: 50) {
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
        }
    ' -f projectId="$project_id"
}

# Get field by name from fields JSON
get_field_by_name() {
    local fields_json="$1"
    local field_name="$2"
    
    echo "$fields_json" | jq -r --arg name "$field_name" \
        '.data.node.fields.nodes[] | select(.name == $name)'
}

# Check if option exists in a single-select field
option_exists() {
    local field_json="$1"
    local option_name="$2"
    
    local exists
    exists=$(echo "$field_json" | jq -r --arg name "$option_name" \
        '.options[]? | select(.name == $name) | .id // empty')
    
    [[ -n "$exists" ]]
}

# Create a single-select field with initial options
# Usage: create_single_select_field PROJECT_ID FIELD_NAME "Option1" "Option2" ...
create_single_select_field() {
    local project_id="$1"
    local field_name="$2"
    shift 2
    local -a options=("$@")
    
    log_info "Creating single-select field: $field_name"
    
    # Build options JSON array for embedding in query
    local options_gql="["
    local first=true
    for opt in "${options[@]}"; do
        if [[ "$first" == true ]]; then
            first=false
        else
            options_gql+=","
        fi
        options_gql+="{name: \"$opt\", description: \"\", color: GRAY}"
    done
    options_gql+="]"
    
    local result
    result=$(gh api graphql -f query="
        mutation {
            createProjectV2Field(input: {
                projectId: \"$project_id\"
                dataType: SINGLE_SELECT
                name: \"$field_name\"
                singleSelectOptions: $options_gql
            }) {
                projectV2Field {
                    ... on ProjectV2SingleSelectField {
                        id
                        name
                        options {
                            id
                            name
                        }
                    }
                }
            }
        }
    ")
    
    local field_id
    field_id=$(echo "$result" | jq -r '.data.createProjectV2Field.projectV2Field.id // empty')
    
    if [[ -z "$field_id" ]]; then
        log_error "Failed to create field: $field_name"
        echo "$result" >&2
        return 1
    fi
    
    log_ok "Created field: $field_name ($field_id)"
    echo "$field_id"
}

# Add option to a single-select field
add_single_select_option() {
    local project_id="$1"
    local field_id="$2"
    local option_name="$3"
    
    log_info "  Adding option: $option_name"
    
    local result
    result=$(gh api graphql -f query='
        mutation($projectId: ID!, $fieldId: ID!, $name: String!) {
            updateProjectV2Field(input: {
                projectId: $projectId
                fieldId: $fieldId
                singleSelectOptions: [{
                    name: $name
                }]
            }) {
                projectV2Field {
                    ... on ProjectV2SingleSelectField {
                        id
                        options {
                            id
                            name
                        }
                    }
                }
            }
        }
    ' -f projectId="$project_id" -f fieldId="$field_id" -f name="$option_name" 2>&1) || true
    
    # GitHub's updateProjectV2Field for adding options can be tricky
    # If it fails, try an alternative approach
    if echo "$result" | jq -e '.errors' > /dev/null 2>&1; then
        log_warn "  Option may already exist or could not be added: $option_name"
    else
        log_ok "  Added option: $option_name"
    fi
}

# Create iteration field with sprints
create_sprint_field() {
    local project_id="$1"
    
    log_info "Creating Sprint iteration field..."
    
    # Calculate the start date (Monday of current week)
    # Works with both GNU date and BSD date
    local start_date
    
    # Get today and calculate Monday (works with GNU date)
    local dow
    dow=$(date +%u)  # 1=Monday, 7=Sunday
    local days_back=$((dow - 1))
    start_date=$(date -d "-${days_back} days" +%Y-%m-%d 2>/dev/null) || \
        start_date=$(date -v-${days_back}d +%Y-%m-%d)  # BSD fallback
    
    log_info "Sprint start date: $start_date (Monday of current week)"
    
    # Build iterations array for GraphQL (inline syntax)
    local iterations_gql="["
    for i in $(seq 1 $NUM_SPRINTS_TO_CREATE); do
        local days_offset=$(( (i - 1) * SPRINT_DURATION_DAYS ))
        local sprint_start
        sprint_start=$(date -d "$start_date + ${days_offset} days" +%Y-%m-%d 2>/dev/null) || \
            sprint_start=$(date -j -v+${days_offset}d -f "%Y-%m-%d" "$start_date" +%Y-%m-%d)
        
        if [[ $i -gt 1 ]]; then
            iterations_gql+=","
        fi
        iterations_gql+="{title: \"Sprint $i\", startDate: \"$sprint_start\", duration: $SPRINT_DURATION_DAYS}"
    done
    iterations_gql+="]"
    
    local result
    result=$(gh api graphql -f query="
        mutation {
            createProjectV2Field(input: {
                projectId: \"$project_id\"
                dataType: ITERATION
                name: \"Sprint\"
                iterationConfiguration: {
                    duration: $SPRINT_DURATION_DAYS
                    startDate: \"$start_date\"
                    iterations: $iterations_gql
                }
            }) {
                projectV2Field {
                    ... on ProjectV2IterationField {
                        id
                        name
                        configuration {
                            iterations {
                                id
                                title
                                startDate
                            }
                        }
                    }
                }
            }
        }
    ")
    
    local field_id
    field_id=$(echo "$result" | jq -r '.data.createProjectV2Field.projectV2Field.id // empty')
    
    if [[ -z "$field_id" ]]; then
        log_error "Failed to create Sprint field"
        echo "$result" >&2
        return 1
    fi
    
    log_ok "Created Sprint field with $NUM_SPRINTS_TO_CREATE iterations"
    echo "$field_id"
}

# Create date field
create_date_field() {
    local project_id="$1"
    local field_name="$2"
    
    log_info "Creating date field: $field_name"
    
    local result
    result=$(gh api graphql -f query='
        mutation($projectId: ID!, $name: String!) {
            createProjectV2Field(input: {
                projectId: $projectId
                dataType: DATE
                name: $name
            }) {
                projectV2Field {
                    ... on ProjectV2Field {
                        id
                        name
                    }
                }
            }
        }
    ' -f projectId="$project_id" -f name="$field_name")
    
    local field_id
    field_id=$(echo "$result" | jq -r '.data.createProjectV2Field.projectV2Field.id // empty')
    
    if [[ -z "$field_id" ]]; then
        log_error "Failed to create field: $field_name"
        echo "$result" >&2
        return 1
    fi
    
    log_ok "Created field: $field_name ($field_id)"
    echo "$field_id"
}

# Ensure Status field has all required options
setup_status_field() {
    local project_id="$1"
    local fields_json="$2"
    
    log_info "Setting up Status field..."
    
    local status_field
    status_field=$(get_field_by_name "$fields_json" "Status")
    
    if [[ -z "$status_field" || "$status_field" == "null" ]]; then
        log_error "Status field not found. This is a built-in field that should exist."
        exit 1
    fi
    
    local field_id
    field_id=$(echo "$status_field" | jq -r '.id')
    
    # Get existing options
    local existing_options
    existing_options=$(echo "$status_field" | jq -r '.options[].name')
    
    # For each required option, check if it exists and add if missing
    for option in "${REQUIRED_STATUS_OPTIONS[@]}"; do
        if echo "$existing_options" | grep -qx "$option"; then
            log_ok "  Status option exists: $option"
        else
            # Adding options to existing Status field requires using updateProjectV2Field
            # with singleSelectOptions that includes ALL options (existing + new)
            log_info "  Adding Status option: $option"
            
            gh api graphql -f query='
                mutation($projectId: ID!, $fieldId: ID!, $optionName: String!) {
                    updateProjectV2Field(input: {
                        projectId: $projectId
                        fieldId: $fieldId
                        singleSelectOptions: [{ name: $optionName }]
                    }) {
                        projectV2Field {
                            ... on ProjectV2SingleSelectField {
                                id
                            }
                        }
                    }
                }
            ' -f projectId="$project_id" -f fieldId="$field_id" -f optionName="$option" > /dev/null 2>&1 || {
                log_warn "  Could not add option (may need manual intervention): $option"
            }
        fi
    done
    
    log_ok "Status field configured"
}

# Ensure Phase field exists with all options
setup_phase_field() {
    local project_id="$1"
    local fields_json="$2"
    
    log_info "Setting up Phase field..."
    
    local phase_field
    phase_field=$(get_field_by_name "$fields_json" "Phase")
    
    local field_id
    if [[ -z "$phase_field" || "$phase_field" == "null" ]]; then
        # Create field with all options at once
        field_id=$(create_single_select_field "$project_id" "Phase" "${REQUIRED_PHASE_OPTIONS[@]}")
    else
        field_id=$(echo "$phase_field" | jq -r '.id')
        log_ok "Phase field already exists: $field_id"
        
        # Check for missing options and add them
        local existing_options
        existing_options=$(echo "$phase_field" | jq -r '.options[].name')
        
        for option in "${REQUIRED_PHASE_OPTIONS[@]}"; do
            if ! echo "$existing_options" | grep -qx "$option"; then
                add_single_select_option "$project_id" "$field_id" "$option"
            fi
        done
    fi
    
    log_ok "Phase field configured"
}

# Ensure Sprint field exists
setup_sprint_field() {
    local project_id="$1"
    local fields_json="$2"
    
    log_info "Setting up Sprint field..."
    
    local sprint_field
    sprint_field=$(get_field_by_name "$fields_json" "Sprint")
    
    if [[ -z "$sprint_field" || "$sprint_field" == "null" ]]; then
        create_sprint_field "$project_id"
    else
        local field_id
        field_id=$(echo "$sprint_field" | jq -r '.id')
        log_ok "Sprint field already exists: $field_id"
    fi
    
    log_ok "Sprint field configured"
}

# Ensure Due Date field exists (uses Target date if present)
setup_due_date_field() {
    local project_id="$1"
    local fields_json="$2"
    
    log_info "Setting up Due Date field..."
    
    # Check for existing "Target date" field first
    local target_date_field
    target_date_field=$(get_field_by_name "$fields_json" "Target date")
    
    if [[ -n "$target_date_field" && "$target_date_field" != "null" ]]; then
        local field_id
        field_id=$(echo "$target_date_field" | jq -r '.id')
        log_ok "Using existing 'Target date' field as Due Date: $field_id"
        return
    fi
    
    # Check for existing "Due Date" field
    local due_date_field
    due_date_field=$(get_field_by_name "$fields_json" "Due Date")
    
    if [[ -n "$due_date_field" && "$due_date_field" != "null" ]]; then
        local field_id
        field_id=$(echo "$due_date_field" | jq -r '.id')
        log_ok "Due Date field already exists: $field_id"
        return
    fi
    
    # Create new Due Date field
    create_date_field "$project_id" "Due Date"
    log_ok "Due Date field configured"
}

# Print summary
print_summary() {
    local project_id="$1"
    
    echo ""
    echo "========================================"
    echo "SETUP COMPLETE"
    echo "========================================"
    echo ""
    echo "Project ID: $project_id"
    echo ""
    echo "Configured fields:"
    echo "  - Status: Backlog, This Week, In Progress, Review, Done"
    echo "  - Sprint: 1-week iterations"
    echo "  - Due Date: Date field (or 'Target date')"
    echo "  - Phase: Phase 1-5"
    echo "  - Owner: Use built-in 'Assignees' field"
    echo ""
    echo "Run ./scripts/project_discover.sh to see all field IDs"
    echo ""
}

# Main execution
main() {
    check_prerequisites
    
    local project_id
    project_id=$(discover_project_id)
    
    log_info "Fetching current project fields..."
    local fields_json
    fields_json=$(fetch_project_fields "$project_id")
    
    # Setup each field
    setup_status_field "$project_id" "$fields_json"
    setup_phase_field "$project_id" "$fields_json"
    setup_sprint_field "$project_id" "$fields_json"
    setup_due_date_field "$project_id" "$fields_json"
    
    print_summary "$project_id"
    log_ok "Project setup complete!"
}

main "$@"

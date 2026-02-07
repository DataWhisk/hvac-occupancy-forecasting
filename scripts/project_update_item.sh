#!/usr/bin/env bash
#
# project_update_item.sh - Add issues to GitHub Project v2 and update their fields
#
# Usage:
#   ./scripts/project_update_item.sh --issue 25 --status "This Week" --sprint 1 --due-date 2026-02-14 --phase "Phase 1"
#   ./scripts/project_update_item.sh --issue 25 --status "In Progress"
#   ./scripts/project_update_item.sh --issue 25 --add-only  # Just add to project without setting fields
#
# Options:
#   --issue NUM       Issue number (required)
#   --status VALUE    Set Status field (Backlog, This Week, In Progress, Review, Done)
#   --sprint NUM      Set Sprint number (1, 2, 3, etc.)
#   --due-date DATE   Set Due Date (YYYY-MM-DD format)
#   --phase VALUE     Set Phase (Phase 1, Phase 2, Phase 3, Phase 4, Phase 5)
#   --owner USER      Set owner/assignee (GitHub username)
#   --add-only        Only add to project, don't update any fields
#
# Environment Variables:
#   PROJECT_ID  - (optional) Override the default project ID
#   ORG_NAME    - (optional) Override the organization name (default: DataWhisk)
#   REPO_NAME   - (optional) Override the repository name (default: hvac-occupancy-forecasting)

set -euo pipefail

# Configuration
ORG_NAME="${ORG_NAME:-DataWhisk}"
REPO_NAME="${REPO_NAME:-hvac-occupancy-forecasting}"

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

# Command line arguments
ISSUE_NUMBER=""
STATUS_VALUE=""
SPRINT_NUMBER=""
DUE_DATE=""
PHASE_VALUE=""
OWNER_VALUE=""
ADD_ONLY=false

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --issue)
                ISSUE_NUMBER="$2"
                shift 2
                ;;
            --status)
                STATUS_VALUE="$2"
                shift 2
                ;;
            --sprint)
                SPRINT_NUMBER="$2"
                shift 2
                ;;
            --due-date)
                DUE_DATE="$2"
                shift 2
                ;;
            --phase)
                PHASE_VALUE="$2"
                shift 2
                ;;
            --owner)
                OWNER_VALUE="$2"
                shift 2
                ;;
            --add-only)
                ADD_ONLY=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    if [[ -z "$ISSUE_NUMBER" ]]; then
        log_error "Issue number is required (--issue NUM)"
        show_usage
        exit 1
    fi
}

show_usage() {
    cat << EOF
Usage: $0 --issue NUM [OPTIONS]

Options:
  --issue NUM       Issue number (required)
  --status VALUE    Set Status (Backlog, This Week, In Progress, Review, Done)
  --sprint NUM      Set Sprint number (1, 2, 3, etc.)
  --due-date DATE   Set Due Date (YYYY-MM-DD)
  --phase VALUE     Set Phase (Phase 1, Phase 2, Phase 3, Phase 4, Phase 5)
  --owner USER      Set owner/assignee (GitHub username)
  --add-only        Only add to project without setting fields
  -h, --help        Show this help message

Examples:
  $0 --issue 25 --status "This Week" --sprint 1 --phase "Phase 1"
  $0 --issue 25 --due-date 2026-02-14
  $0 --issue 25 --add-only
EOF
}

# Check prerequisites
check_prerequisites() {
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
}

# Discover project ID
discover_project_id() {
    if [[ -n "${PROJECT_ID:-}" ]]; then
        echo "$PROJECT_ID"
        return
    fi
    
    local result
    result=$(gh api graphql -f query='
        query($org: String!, $repo: String!) {
            repository(owner: $org, name: $repo) {
                projectsV2(first: 1) {
                    nodes {
                        id
                    }
                }
            }
        }
    ' -f org="$ORG_NAME" -f repo="$REPO_NAME")
    
    echo "$result" | jq -r '.data.repository.projectsV2.nodes[0].id // empty'
}

# Get issue node ID from issue number
get_issue_node_id() {
    local issue_number="$1"
    
    local result
    result=$(gh api graphql -f query='
        query($org: String!, $repo: String!, $number: Int!) {
            repository(owner: $org, name: $repo) {
                issue(number: $number) {
                    id
                    title
                }
            }
        }
    ' -f org="$ORG_NAME" -f repo="$REPO_NAME" -F number="$issue_number")
    
    local issue_id
    issue_id=$(echo "$result" | jq -r '.data.repository.issue.id // empty')
    
    if [[ -z "$issue_id" ]]; then
        log_error "Issue #$issue_number not found in $ORG_NAME/$REPO_NAME"
        exit 1
    fi
    
    local issue_title
    issue_title=$(echo "$result" | jq -r '.data.repository.issue.title')
    log_info "Found issue: #$issue_number - $issue_title"
    
    echo "$issue_id"
}

# Add issue to project (returns project item ID)
add_issue_to_project() {
    local project_id="$1"
    local issue_id="$2"
    
    log_info "Adding issue to project..."
    
    # First check if issue is already in project
    local existing_item_id
    existing_item_id=$(get_project_item_id "$project_id" "$issue_id")
    
    if [[ -n "$existing_item_id" ]]; then
        log_ok "Issue already in project (item ID: $existing_item_id)"
        echo "$existing_item_id"
        return
    fi
    
    local result
    result=$(gh api graphql -f query='
        mutation($projectId: ID!, $contentId: ID!) {
            addProjectV2ItemById(input: {
                projectId: $projectId
                contentId: $contentId
            }) {
                item {
                    id
                }
            }
        }
    ' -f projectId="$project_id" -f contentId="$issue_id")
    
    local item_id
    item_id=$(echo "$result" | jq -r '.data.addProjectV2ItemById.item.id // empty')
    
    if [[ -z "$item_id" ]]; then
        log_error "Failed to add issue to project"
        echo "$result" >&2
        exit 1
    fi
    
    log_ok "Added issue to project (item ID: $item_id)"
    echo "$item_id"
}

# Get project item ID for an issue already in the project
get_project_item_id() {
    local project_id="$1"
    local issue_id="$2"
    
    local result
    result=$(gh api graphql -f query='
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    items(first: 100) {
                        nodes {
                            id
                            content {
                                ... on Issue {
                                    id
                                }
                                ... on PullRequest {
                                    id
                                }
                            }
                        }
                    }
                }
            }
        }
    ' -f projectId="$project_id")
    
    echo "$result" | jq -r --arg issueId "$issue_id" \
        '.data.node.items.nodes[] | select(.content.id == $issueId) | .id // empty'
}

# Fetch project fields
fetch_project_fields() {
    local project_id="$1"
    
    gh api graphql -f query='
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
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

# Get field ID by name
get_field_id() {
    local fields_json="$1"
    local field_name="$2"
    
    echo "$fields_json" | jq -r --arg name "$field_name" \
        '.data.node.fields.nodes[] | select(.name == $name) | .id // empty'
}

# Get single-select option ID by name
get_option_id() {
    local fields_json="$1"
    local field_name="$2"
    local option_name="$3"
    
    echo "$fields_json" | jq -r --arg fname "$field_name" --arg oname "$option_name" \
        '.data.node.fields.nodes[] | select(.name == $fname) | .options[]? | select(.name == $oname) | .id // empty'
}

# Get iteration ID by sprint number
get_sprint_id() {
    local fields_json="$1"
    local sprint_number="$2"
    
    local sprint_title="Sprint $sprint_number"
    
    echo "$fields_json" | jq -r --arg title "$sprint_title" \
        '.data.node.fields.nodes[] | select(.name == "Sprint") | .configuration.iterations[]? | select(.title == $title) | .id // empty'
}

# Set single-select field value
set_single_select_field() {
    local project_id="$1"
    local item_id="$2"
    local field_id="$3"
    local option_id="$4"
    local field_name="$5"
    local value="$6"
    
    log_info "Setting $field_name = $value"
    
    local result
    result=$(gh api graphql -f query='
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
            updateProjectV2ItemFieldValue(input: {
                projectId: $projectId
                itemId: $itemId
                fieldId: $fieldId
                value: { singleSelectOptionId: $optionId }
            }) {
                projectV2Item {
                    id
                }
            }
        }
    ' -f projectId="$project_id" -f itemId="$item_id" -f fieldId="$field_id" -f optionId="$option_id" 2>&1)
    
    if echo "$result" | jq -e '.errors' > /dev/null 2>&1; then
        log_error "Failed to set $field_name"
        echo "$result" | jq '.errors' >&2
        return 1
    fi
    
    log_ok "Set $field_name = $value"
}

# Set iteration field value
set_iteration_field() {
    local project_id="$1"
    local item_id="$2"
    local field_id="$3"
    local iteration_id="$4"
    local sprint_number="$5"
    
    log_info "Setting Sprint = Sprint $sprint_number"
    
    local result
    result=$(gh api graphql -f query='
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $iterationId: String!) {
            updateProjectV2ItemFieldValue(input: {
                projectId: $projectId
                itemId: $itemId
                fieldId: $fieldId
                value: { iterationId: $iterationId }
            }) {
                projectV2Item {
                    id
                }
            }
        }
    ' -f projectId="$project_id" -f itemId="$item_id" -f fieldId="$field_id" -f iterationId="$iteration_id" 2>&1)
    
    if echo "$result" | jq -e '.errors' > /dev/null 2>&1; then
        log_error "Failed to set Sprint"
        echo "$result" | jq '.errors' >&2
        return 1
    fi
    
    log_ok "Set Sprint = Sprint $sprint_number"
}

# Set date field value
set_date_field() {
    local project_id="$1"
    local item_id="$2"
    local field_id="$3"
    local date_value="$4"
    local field_name="$5"
    
    log_info "Setting $field_name = $date_value"
    
    local result
    result=$(gh api graphql -f query='
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $date: Date!) {
            updateProjectV2ItemFieldValue(input: {
                projectId: $projectId
                itemId: $itemId
                fieldId: $fieldId
                value: { date: $date }
            }) {
                projectV2Item {
                    id
                }
            }
        }
    ' -f projectId="$project_id" -f itemId="$item_id" -f fieldId="$field_id" -f date="$date_value" 2>&1)
    
    if echo "$result" | jq -e '.errors' > /dev/null 2>&1; then
        log_error "Failed to set $field_name"
        echo "$result" | jq '.errors' >&2
        return 1
    fi
    
    log_ok "Set $field_name = $date_value"
}

# Assign owner to issue (using GitHub issue assignees)
assign_owner() {
    local owner="$1"
    
    log_info "Assigning owner: $owner"
    
    gh issue edit "$ISSUE_NUMBER" --repo "$ORG_NAME/$REPO_NAME" --add-assignee "$owner" > /dev/null 2>&1 || {
        log_error "Failed to assign owner: $owner"
        return 1
    }
    
    log_ok "Assigned owner: $owner"
}

# Main execution
main() {
    parse_args "$@"
    check_prerequisites
    
    log_info "Processing issue #$ISSUE_NUMBER"
    
    # Discover project
    local project_id
    project_id=$(discover_project_id)
    
    if [[ -z "$project_id" ]]; then
        log_error "Could not find project"
        exit 1
    fi
    
    log_info "Using project: $project_id"
    
    # Get issue node ID
    local issue_id
    issue_id=$(get_issue_node_id "$ISSUE_NUMBER")
    
    # Add issue to project
    local item_id
    item_id=$(add_issue_to_project "$project_id" "$issue_id")
    
    if [[ "$ADD_ONLY" == true ]]; then
        log_ok "Issue added to project (add-only mode)"
        exit 0
    fi
    
    # Fetch project fields for lookups
    local fields_json
    fields_json=$(fetch_project_fields "$project_id")
    
    # Set Status if provided
    if [[ -n "$STATUS_VALUE" ]]; then
        local status_field_id option_id
        status_field_id=$(get_field_id "$fields_json" "Status")
        option_id=$(get_option_id "$fields_json" "Status" "$STATUS_VALUE")
        
        if [[ -z "$status_field_id" || -z "$option_id" ]]; then
            log_error "Status field or option '$STATUS_VALUE' not found"
            log_warn "Available options: $(echo "$fields_json" | jq -r '.data.node.fields.nodes[] | select(.name == "Status") | .options[].name' | tr '\n' ', ')"
        else
            set_single_select_field "$project_id" "$item_id" "$status_field_id" "$option_id" "Status" "$STATUS_VALUE"
        fi
    fi
    
    # Set Sprint if provided
    if [[ -n "$SPRINT_NUMBER" ]]; then
        local sprint_field_id sprint_id
        sprint_field_id=$(get_field_id "$fields_json" "Sprint")
        sprint_id=$(get_sprint_id "$fields_json" "$SPRINT_NUMBER")
        
        if [[ -z "$sprint_field_id" ]]; then
            log_error "Sprint field not found"
        elif [[ -z "$sprint_id" ]]; then
            log_error "Sprint $SPRINT_NUMBER not found"
            log_warn "Available sprints: $(echo "$fields_json" | jq -r '.data.node.fields.nodes[] | select(.name == "Sprint") | .configuration.iterations[].title' | tr '\n' ', ')"
        else
            set_iteration_field "$project_id" "$item_id" "$sprint_field_id" "$sprint_id" "$SPRINT_NUMBER"
        fi
    fi
    
    # Set Due Date if provided
    if [[ -n "$DUE_DATE" ]]; then
        # Try "Target date" first, then "Due Date"
        local date_field_id
        date_field_id=$(get_field_id "$fields_json" "Target date")
        local field_name="Target date"
        
        if [[ -z "$date_field_id" ]]; then
            date_field_id=$(get_field_id "$fields_json" "Due Date")
            field_name="Due Date"
        fi
        
        if [[ -z "$date_field_id" ]]; then
            log_error "No date field found (tried 'Target date' and 'Due Date')"
        else
            set_date_field "$project_id" "$item_id" "$date_field_id" "$DUE_DATE" "$field_name"
        fi
    fi
    
    # Set Phase if provided
    if [[ -n "$PHASE_VALUE" ]]; then
        local phase_field_id phase_option_id
        phase_field_id=$(get_field_id "$fields_json" "Phase")
        phase_option_id=$(get_option_id "$fields_json" "Phase" "$PHASE_VALUE")
        
        if [[ -z "$phase_field_id" ]]; then
            log_error "Phase field not found. Run project_setup.sh first."
        elif [[ -z "$phase_option_id" ]]; then
            log_error "Phase option '$PHASE_VALUE' not found"
            log_warn "Available options: $(echo "$fields_json" | jq -r '.data.node.fields.nodes[] | select(.name == "Phase") | .options[].name' | tr '\n' ', ')"
        else
            set_single_select_field "$project_id" "$item_id" "$phase_field_id" "$phase_option_id" "Phase" "$PHASE_VALUE"
        fi
    fi
    
    # Assign owner if provided
    if [[ -n "$OWNER_VALUE" ]]; then
        assign_owner "$OWNER_VALUE"
    fi
    
    echo ""
    log_ok "Issue #$ISSUE_NUMBER updated successfully!"
}

main "$@"

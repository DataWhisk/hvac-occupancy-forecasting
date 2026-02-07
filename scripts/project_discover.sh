#!/usr/bin/env bash
#
# project_discover.sh - Discover GitHub Project v2 fields and their IDs
#
# Usage:
#   ./scripts/project_discover.sh
#
# Environment Variables:
#   PROJECT_ID  - (optional) Override the default project ID
#   ORG_NAME    - (optional) Override the organization name (default: DataWhisk)
#   REPO_NAME   - (optional) Override the repository name (default: hvac-occupancy-forecasting)
#
# Output:
#   Prints project field information in a structured format suitable for scripting.

set -euo pipefail

# Configuration - Override these via environment variables if needed
ORG_NAME="${ORG_NAME:-DataWhisk}"
REPO_NAME="${REPO_NAME:-hvac-occupancy-forecasting}"

# Colors for output (disabled if not a terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
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

# Discover project ID if not provided
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
    
    local project_title
    project_title=$(echo "$result" | jq -r '.data.repository.projectsV2.nodes[0].title')
    log_ok "Found project: $project_title ($project_id)"
    
    echo "$project_id"
}

# Fetch all project fields with full details
fetch_project_fields() {
    local project_id="$1"
    
    log_info "Fetching project fields..."
    
    gh api graphql -f query='
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    id
                    title
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
                                    completedIterations {
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

# Parse and display fields in a readable format
display_fields() {
    local fields_json="$1"
    
    echo ""
    echo "========================================"
    echo "PROJECT FIELDS SUMMARY"
    echo "========================================"
    echo ""
    
    # Extract project info
    local project_title project_id
    project_title=$(echo "$fields_json" | jq -r '.data.node.title')
    project_id=$(echo "$fields_json" | jq -r '.data.node.id')
    
    echo "Project: $project_title"
    echo "Project ID: $project_id"
    echo ""
    echo "----------------------------------------"
    echo "FIELDS:"
    echo "----------------------------------------"
    
    # Process each field
    echo "$fields_json" | jq -r '
        .data.node.fields.nodes[] |
        "[\(.dataType)] \(.name)\n  ID: \(.id)" +
        (if .options then
            "\n  Options:\n" + ([.options[] | "    - \(.name) (\(.id))"] | join("\n"))
        else "" end) +
        (if .configuration.iterations then
            "\n  Iterations:\n" + ([.configuration.iterations[] | "    - \(.title) (start: \(.startDate), \(.duration) days) [\(.id)]"] | join("\n"))
        else "" end) +
        "\n"
    '
    
    echo "========================================"
    echo "EXPORT FORMAT (for use in other scripts)"
    echo "========================================"
    echo ""
    echo "# Copy these environment variables:"
    echo "export PROJECT_ID=\"$project_id\""
    
    # Export field IDs
    echo "$fields_json" | jq -r '
        .data.node.fields.nodes[] |
        "export FIELD_" + (.name | gsub(" "; "_") | gsub("-"; "_") | ascii_upcase) + "_ID=\"" + .id + "\""
    '
    
    # Export Status options if available
    local status_field
    status_field=$(echo "$fields_json" | jq -r '.data.node.fields.nodes[] | select(.name == "Status")')
    if [[ -n "$status_field" ]]; then
        echo ""
        echo "# Status options:"
        echo "$status_field" | jq -r '
            .options[] |
            "export STATUS_" + (.name | gsub(" "; "_") | ascii_upcase) + "_ID=\"" + .id + "\""
        '
    fi
    
    # Export Phase options if available
    local phase_field
    phase_field=$(echo "$fields_json" | jq -r '.data.node.fields.nodes[] | select(.name == "Phase")')
    if [[ -n "$phase_field" && "$phase_field" != "null" ]]; then
        echo ""
        echo "# Phase options:"
        echo "$phase_field" | jq -r '
            .options[] |
            "export PHASE_" + (.name | gsub(" "; "_") | ascii_upcase) + "_ID=\"" + .id + "\""
        '
    fi
    
    # Export Sprint iterations if available
    local sprint_field
    sprint_field=$(echo "$fields_json" | jq -r '.data.node.fields.nodes[] | select(.name == "Sprint")')
    if [[ -n "$sprint_field" && "$sprint_field" != "null" ]]; then
        echo ""
        echo "# Sprint iterations:"
        echo "$sprint_field" | jq -r '
            .configuration.iterations[] |
            "export SPRINT_" + (.title | gsub(" "; "_") | ascii_upcase) + "_ID=\"" + .id + "\""
        '
    fi
}

# Main execution
main() {
    check_prerequisites
    
    local project_id
    project_id=$(discover_project_id)
    
    local fields_json
    fields_json=$(fetch_project_fields "$project_id")
    
    display_fields "$fields_json"
    
    log_ok "Discovery complete"
}

main "$@"

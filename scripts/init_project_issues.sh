#!/bin/bash
# =============================================================================
# HVAC Occupancy Forecasting - GitHub Project Issue Seeder
# Creates all project issues and adds them to the GitHub Project board
# =============================================================================

set -e

# === CONFIG ===
OWNER="DataWhisk"
REPO="hvac-occupancy-forecasting"
PROJECT_ID="PVT_kwDOD38Ugs4BOiS9"

echo "🚀 Starting issue creation for $OWNER/$REPO"
echo "📋 Project ID: $PROJECT_ID"
echo ""

# === HELPER FUNCTION ===
create_issue_and_add_to_project() {
  local TITLE="$1"
  local BODY="$2"
  local LABELS="$3"

  echo "📝 Creating issue: $TITLE"

  # Create the issue
  ISSUE_URL=$(gh issue create \
    --repo "$OWNER/$REPO" \
    --title "$TITLE" \
    --body "$BODY" \
    --label "$LABELS" 2>&1) || {
    echo "   ⚠️  Failed to create issue (labels may not exist, trying without labels)"
    ISSUE_URL=$(gh issue create \
      --repo "$OWNER/$REPO" \
      --title "$TITLE" \
      --body "$BODY" 2>&1)
  }

  # Extract issue number from URL
  ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE '[0-9]+$')
  
  if [ -n "$ISSUE_NUM" ]; then
    # Get the node ID for the issue
    ISSUE_NODE_ID=$(gh api "repos/$OWNER/$REPO/issues/$ISSUE_NUM" --jq '.node_id')
    
    # Add to project
    gh api graphql -f query="
    mutation {
      addProjectV2ItemById(
        input: {
          projectId: \"$PROJECT_ID\"
          contentId: \"$ISSUE_NODE_ID\"
        }
      ) {
        item { id }
      }
    }" >/dev/null 2>&1 && echo "   ✅ Added to project" || echo "   ⚠️  Could not add to project"
  else
    echo "   ⚠️  Could not extract issue number"
  fi
  
  echo ""
}

# =============================================================================
# PHASE 1 - This Week (Setup)
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 PHASE 1: Repository & Data Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

create_issue_and_add_to_project \
"Finalize repository structure" \
"## Tasks
- [x] Create folders: \`data/\`, \`notebooks/\`, \`src/\`, \`docs/\`
- [x] Add \`README.md\` with project overview
- [x] Add \`.gitignore\` for Python/Jupyter/data files
- [x] Add \`requirements.txt\` with dependencies

## Acceptance Criteria
- Repository has complete skeleton structure
- README documents project goals and setup instructions" \
"phase-1"

create_issue_and_add_to_project \
"Set up GitHub Project board" \
"## Tasks
- [ ] Create project board with columns
- [ ] Seed Phase 1 issues
- [ ] Configure automation rules (optional)

## Columns
- Backlog
- This Week
- In Progress
- Review
- Done" \
"phase-1"

create_issue_and_add_to_project \
"Initial data drop (sample dataset)" \
"## Tasks
- [ ] Receive 1 week (or a few days) of sample data
- [ ] Occupancy data (Wi-Fi derived or direct)
- [ ] HVAC data (setpoints, states, energy)
- [ ] Place in \`data/raw/occupancy/\` and \`data/raw/hvac/\`

## Data Requirements
- Timestamp column with timezone info
- Zone/room identifiers
- At least 15-minute resolution

## Contact
Obtain from Kevin/Nada/Ashwin" \
"phase-1"

create_issue_and_add_to_project \
"Draft data dictionary" \
"## Tasks
- [ ] Document all columns for each dataset
- [ ] Record units (°F vs °C, kWh, etc.)
- [ ] Note timezone and frequency
- [ ] Document known quirks or missing data
- [ ] Save to \`docs/data_dictionary.md\`

## Datasets to Document
- Occupancy data
- HVAC data
- Weather data (when available)
- TOU pricing (when available)
- Space metadata" \
"phase-1"

create_issue_and_add_to_project \
"Exploration notebook: occupancy vs HVAC" \
"## Tasks
- [x] Create \`notebooks/01_exploration_opportunity_savings.ipynb\`
- [ ] Plot occupancy over time
- [ ] Plot HVAC state/power over time
- [ ] Align datasets by timestamp
- [ ] Identify data quality issues

## Notes
- No modeling yet - pure exploration
- Focus on understanding the data shape and patterns" \
"phase-1"

# =============================================================================
# PHASE 2 - Savings Definition
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💰 PHASE 2: Savings Definition & Analysis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

create_issue_and_add_to_project \
"Define initial 'opportunity for savings' rule" \
"## Tasks
- [ ] Propose simple rule for identifying savings opportunities
- [ ] Discuss and agree as a team
- [ ] Record assumptions and limitations

## Proposed Rule (Draft)
\`\`\`
opportunity = (occupancy == 0 for >= 30 min) AND (HVAC is ON)
\`\`\`

## Questions to Resolve
- What occupancy threshold? (0 vs <5?)
- Minimum duration? (15 min? 30 min?)
- How to handle pre-conditioning time?
- How to define 'HVAC ON'?" \
"phase-2"

create_issue_and_add_to_project \
"Implement savings rule on sample data" \
"## Tasks
- [ ] Identify zero-occupancy intervals in data
- [ ] Check HVAC state during these intervals
- [ ] Compute minutes/day of \"opportunity\"
- [ ] Compute estimated energy during opportunity periods

## Outputs
- [ ] Bar chart: daily opportunity (minutes or kWh)
- [ ] Example timeline: one \"interesting\" day
- [ ] Summary statistics (mean, median, total)" \
"phase-2"

create_issue_and_add_to_project \
"Document savings definition" \
"## Tasks
- [ ] Create \`docs/savings_definition.md\`
- [ ] Document current rule with pseudocode
- [ ] List all assumptions
- [ ] Note planned refinements

## Sections
1. Current Definition
2. Assumptions
3. Limitations
4. Future Refinements" \
"phase-2"

# =============================================================================
# PHASE 3 - Data Pipeline
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 PHASE 3: Data Pipeline Engineering"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

create_issue_and_add_to_project \
"Standardize data loading helpers" \
"## Tasks
- [x] Create \`src/data/load.py\`
- [ ] Implement \`load_occupancy(path)\` function
- [ ] Implement \`load_hvac(path)\` function
- [ ] Enforce datetime parsing + timezone
- [ ] Standardize column names

## Requirements
- All loaders return pandas DataFrame
- Consistent timestamp column name
- Handle common file formats (CSV, parquet)" \
"phase-3"

create_issue_and_add_to_project \
"Merge & align occupancy + HVAC data" \
"## Tasks
- [x] Create \`src/data/preprocess.py\`
- [ ] Implement \`merge_occupancy_hvac()\` function
- [ ] Resample to common interval (15 min)
- [ ] Join by zone/building ID
- [ ] Handle missing data

## Output
- Single DataFrame with aligned occupancy + HVAC columns
- Data quality flags for interpolated/missing values" \
"phase-3"

create_issue_and_add_to_project \
"Refactor exploration notebook to use pipeline" \
"## Tasks
- [ ] Replace inline loading with \`load_*\` helpers
- [ ] Use \`merge_occupancy_hvac()\` function
- [ ] Verify outputs match original analysis
- [ ] Clean up notebook

## Benefits
- Reproducible analysis
- Reusable code for future notebooks" \
"phase-3"

# =============================================================================
# PHASE 4 - Scale Up Analysis
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📈 PHASE 4: Scale Up & Visualization"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

create_issue_and_add_to_project \
"Apply savings analysis to multi-month dataset" \
"## Tasks
- [ ] Obtain 3-4 months of synchronized data
- [ ] Run savings analysis pipeline
- [ ] Compute daily opportunity time series
- [ ] Identify patterns and anomalies

## Analysis Questions
- How does opportunity vary by day of week?
- Seasonal patterns?
- Which zones have most opportunity?" \
"phase-4"

create_issue_and_add_to_project \
"Prepare presentation-quality visualizations" \
"## Tasks
- [ ] Daily potential savings plot (time series)
- [ ] Distribution by hour of day (heatmap)
- [ ] One \"interesting day\" detailed timeline
- [ ] Summary metrics dashboard

## Requirements
- Publication quality
- Clear labels and legends
- Consistent color scheme
- Export as PNG/PDF" \
"phase-4"

# =============================================================================
# PHASE 5 - Forecasting
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔮 PHASE 5: Forecasting Models"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

create_issue_and_add_to_project \
"Revive baseline forecasting code" \
"## Tasks
- [ ] Retrieve Prophet/Transformer code from previous work
- [ ] Review and understand existing implementation
- [ ] Run on aggregated occupancy data
- [ ] Record baseline metrics (MAE, MAPE, RMSE)

## Notes
- Code from previous student may need adaptation
- Start with Prophet (simpler) before Transformer" \
"phase-5"

create_issue_and_add_to_project \
"Baseline forecasting notebook" \
"## Tasks
- [x] Create \`notebooks/02_forecasting_baselines.ipynb\`
- [ ] Prepare data for Prophet (ds, y format)
- [ ] Fit baseline Prophet model
- [ ] Generate forecasts
- [ ] Plot actual vs predicted occupancy
- [ ] Compute error metrics

## Evaluation
- MAE (Mean Absolute Error)
- MAPE (Mean Absolute Percentage Error)
- Visual inspection of forecasts" \
"phase-5"

create_issue_and_add_to_project \
"Control simulation notebook" \
"## Tasks
- [x] Create \`notebooks/03_control_simulation.ipynb\`
- [ ] Define control policies (baseline, reactive, predictive)
- [ ] Simulate policies on historical data
- [ ] Compare energy consumption
- [ ] Estimate cost savings with TOU rates

## Policies to Compare
1. Baseline (current operation)
2. Reactive (setback when occupancy=0)
3. Predictive (setback based on forecast)" \
"phase-5"

# =============================================================================
# DONE
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All issues created!"
echo ""
echo "View your project board:"
echo "  gh project view --owner $OWNER"
echo ""
echo "View issues:"
echo "  gh issue list --repo $OWNER/$REPO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

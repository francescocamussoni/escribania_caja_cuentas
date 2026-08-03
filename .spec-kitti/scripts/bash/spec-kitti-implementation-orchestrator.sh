#!/usr/bin/env bash

# ============================================================================
# spec-kitti-implementation-orchestrator.sh
#
# PURPOSE: CI/headless orchestrator for non-Cursor environments.
#   - Use this when running Spec-Kitti from a pipeline, CLI or GitHub Actions.
#   - In Cursor: the AI agent handles the executor/reviewer loop natively
#     via .cursor/skills/spec-kitti-implement/SKILL.md — this script is NOT
#     invoked by the /spec-kitti.implement command.
#
# USAGE (outside Cursor):
#   ./spec-kitti-implementation-orchestrator.sh \
#     --work-unit .spec-kitti/plan/WU-005.md \
#     --parity-contract .spec-kitti/discovery/graph.json \
#     --plan .spec-kitti/plan/plan.md \
#     --output-dir src/
# ============================================================================

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAX_ITERATIONS=5  # Maximum correction attempts
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log() {
  echo -e "${GREEN}[ORCHESTRATOR]${NC} $1"
}

warn() {
  echo -e "${YELLOW}[ORCHESTRATOR]${NC} $1"
}

error() {
  echo -e "${RED}[ORCHESTRATOR]${NC} $1"
}

info() {
  echo -e "${BLUE}[ORCHESTRATOR]${NC} $1"
}

# --- Help ---
usage() {
  cat << EOF
Usage: $(basename "$0") [OPTIONS]

Autonomous code generation and review orchestration for a single Work Unit.

PROCESS:
  1. Executor Agent generates code from Work Unit
  2. Reviewer Agent validates code quality
  3. If REJECTED/NEEDS_REVISION → feedback to Executor (loop)
  4. If APPROVED → Create Pull Request
  5. Human reviews only the final PR

OPTIONS:
  --work-unit FILE        Path to Work Unit JSON file (required)
  --parity-contract FILE  Path to endpoint_mapping_schema.json (required)
  --plan FILE             Path to architectural plan.md (required)
  --output-dir DIR        Base directory for generated files (required)
  --work-dir DIR          Working directory for orchestration files (default: .spec-kitti/implementation)
  --max-iterations NUM    Maximum correction attempts (default: 5)
  --help                  Show this help message

EXAMPLE:
  $(basename "$0") \\
    --work-unit .spec-kitti/work-units/WU-005.json \\
    --parity-contract .spec-kitti/discovery/endpoint_mapping_schema.json \\
    --plan .spec-kitti/plan.md \\
    --output-dir src/

OUTPUT:
  - Generated code in output-dir/{file_path}
  - Review reports in work-dir/WU-XXX-review-N.md
  - Execution log in work-dir/WU-XXX-execution.log

EOF
  exit 1
}

# --- Parse Arguments ---
WORK_UNIT_FILE=""
PARITY_CONTRACT_FILE=""
PLAN_FILE=""
OUTPUT_DIR=""
WORK_DIR=".spec-kitti/implementation"

while [[ $# -gt 0 ]]; do
  case $1 in
    --work-unit)
      WORK_UNIT_FILE="$2"
      shift 2
      ;;
    --parity-contract)
      PARITY_CONTRACT_FILE="$2"
      shift 2
      ;;
    --plan)
      PLAN_FILE="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --work-dir)
      WORK_DIR="$2"
      shift 2
      ;;
    --max-iterations)
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --help)
      usage
      ;;
    *)
      error "Unknown option: $1"
      usage
      ;;
  esac
done

# --- Validate Required Arguments ---
if [[ -z "$WORK_UNIT_FILE" || -z "$PARITY_CONTRACT_FILE" || -z "$PLAN_FILE" || -z "$OUTPUT_DIR" ]]; then
  error "Missing required arguments"
  usage
fi

# --- Validate Input Files ---
for file in "$WORK_UNIT_FILE" "$PARITY_CONTRACT_FILE" "$PLAN_FILE"; do
  if [[ ! -f "$file" ]]; then
    error "File not found: $file"
    exit 1
  fi
done

# --- Create Working Directory ---
mkdir -p "$WORK_DIR"
mkdir -p "$OUTPUT_DIR"

# --- Extract Work Unit Metadata ---
WORK_UNIT_CONTENT=$(cat "$WORK_UNIT_FILE")
WORK_UNIT_ID=$(echo "$WORK_UNIT_CONTENT" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
FILE_PATH=$(echo "$WORK_UNIT_CONTENT" | grep -o '"file_path":"[^"]*"' | head -1 | cut -d'"' -f4)
ACTION=$(echo "$WORK_UNIT_CONTENT" | grep -o '"action":"[^"]*"' | head -1 | cut -d'"' -f4)

if [[ -z "$WORK_UNIT_ID" || -z "$FILE_PATH" ]]; then
  error "Could not extract Work Unit metadata"
  exit 1
fi

# --- Setup Logging ---
LOG_FILE="${WORK_DIR}/${WORK_UNIT_ID}-execution.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# --- Banner ---
clear
echo ""
echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                  SPEC-KITTI IMPLEMENTATION ORCHESTRATOR                ║${NC}"
echo -e "${BOLD}${CYAN}║                      Autonomous Code Generation                        ║${NC}"
echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Work Unit:${NC}        $WORK_UNIT_ID"
echo -e "${BOLD}File:${NC}             $FILE_PATH"
echo -e "${BOLD}Action:${NC}           $ACTION"
echo -e "${BOLD}Max Iterations:${NC}   $MAX_ITERATIONS"
echo ""
echo "─────────────────────────────────────────────────────────────────────────"
echo ""

# --- Agent Paths ---
EXECUTOR_AGENT="${SCRIPT_DIR}/spec-kitti-executor-agent.sh"
CODE_REVIEWER_AGENT="${SCRIPT_DIR}/spec-kitti-code-reviewer-agent.sh"

# Validate agent scripts exist
for agent in "$EXECUTOR_AGENT" "$CODE_REVIEWER_AGENT"; do
  if [[ ! -f "$agent" ]]; then
    error "Agent script not found: $agent"
    exit 1
  fi
  if [[ ! -x "$agent" ]]; then
    error "Agent script not executable: $agent"
    exit 1
  fi
done

# --- Orchestration Loop ---
ITERATION=1
STATUS="PENDING"
FEEDBACK_FILE=""
GENERATED_FILE="${OUTPUT_DIR}/${FILE_PATH}"

while [[ $ITERATION -le $MAX_ITERATIONS ]]; do
  echo ""
  echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}${CYAN}  ITERATION $ITERATION of $MAX_ITERATIONS${NC}"
  echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════════════${NC}"
  echo ""
  
  # --- STEP 1: EXECUTOR AGENT ---
  log "STEP 1: Executor Agent - Generating code..."
  echo ""
  
  EXECUTOR_CMD="$EXECUTOR_AGENT \
    --work-unit \"$WORK_UNIT_FILE\" \
    --parity-contract \"$PARITY_CONTRACT_FILE\" \
    --plan \"$PLAN_FILE\" \
    --output-dir \"$OUTPUT_DIR\""
  
  # Add feedback if correction mode
  if [[ -n "$FEEDBACK_FILE" ]]; then
    EXECUTOR_CMD="$EXECUTOR_CMD --feedback \"$FEEDBACK_FILE\""
  fi
  
  if eval "$EXECUTOR_CMD"; then
    log "Executor Agent completed successfully"
  else
    error "Executor Agent failed"
    exit 1
  fi
  
  # Verify file was generated
  if [[ ! -f "$GENERATED_FILE" ]]; then
    error "Expected file not generated: $GENERATED_FILE"
    exit 1
  fi
  
  echo ""
  echo "─────────────────────────────────────────────────────────────────────────"
  echo ""
  
  # --- STEP 2: CODE REVIEWER AGENT ---
  log "STEP 2: Code Reviewer Agent - Validating code..."
  echo ""
  
  REVIEW_FILE="${WORK_DIR}/${WORK_UNIT_ID}-review-${ITERATION}.md"
  
  CODE_REVIEWER_CMD="$CODE_REVIEWER_AGENT \
    --code-file \"$GENERATED_FILE\" \
    --work-unit \"$WORK_UNIT_FILE\" \
    --parity-contract \"$PARITY_CONTRACT_FILE\" \
    --output \"$REVIEW_FILE\""
  
  # Capture exit code (0=APPROVED, 1=NEEDS_REVISION, 2=REJECTED)
  set +e
  eval "$CODE_REVIEWER_CMD"
  REVIEW_EXIT_CODE=$?
  set -e
  
  echo ""
  echo "─────────────────────────────────────────────────────────────────────────"
  echo ""
  
  # --- STEP 3: DECISION ---
  case $REVIEW_EXIT_CODE in
    0)
      # APPROVED
      STATUS="APPROVED"
      log "STATUS: ${GREEN}APPROVED${NC}"
      log "Code passed all quality checks!"
      echo ""
      break
      ;;
    1)
      # NEEDS_REVISION
      STATUS="NEEDS_REVISION"
      warn "STATUS: ${YELLOW}NEEDS_REVISION${NC}"
      warn "Minor issues found - attempting automatic correction..."
      FEEDBACK_FILE="$REVIEW_FILE"
      ;;
    2)
      # REJECTED
      STATUS="REJECTED"
      error "STATUS: ${RED}REJECTED${NC}"
      error "Significant issues found - attempting correction..."
      FEEDBACK_FILE="$REVIEW_FILE"
      ;;
    *)
      error "Reviewer Agent returned unexpected exit code: $REVIEW_EXIT_CODE"
      exit 1
      ;;
  esac
  
  # Check if we've reached max iterations
  if [[ $ITERATION -eq $MAX_ITERATIONS ]]; then
    error "Maximum iterations ($MAX_ITERATIONS) reached without approval"
    error "Last review: $REVIEW_FILE"
    error "Manual intervention required"
    exit 1
  fi
  
  warn "Sending feedback to Executor Agent for correction..."
  echo ""
  
  ((ITERATION++))
done

# --- SUCCESS ---
echo ""
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║                          CODE APPROVED                                 ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
log "Code generation completed successfully!"
log "Iterations: $ITERATION"
log "Generated file: $GENERATED_FILE"
log "Final review: ${WORK_DIR}/${WORK_UNIT_ID}-review-${ITERATION}.md"
echo ""
log "The developer can now review the code and commit manually."

# --- Final Summary ---
echo ""
echo "─────────────────────────────────────────────────────────────────────────"
echo ""
echo -e "${BOLD}ORCHESTRATION SUMMARY:${NC}"
echo ""
echo "  Work Unit:         $WORK_UNIT_ID"
echo "  File:              $FILE_PATH"
echo "  Action:            $ACTION"
echo "  Total Iterations:  $ITERATION"
echo "  Final Status:      ${GREEN}${STATUS}${NC}"
echo "  Generated File:    $GENERATED_FILE"
echo "  Review Report:     ${WORK_DIR}/${WORK_UNIT_ID}-review-${ITERATION}.md"
echo "  Execution Log:     $LOG_FILE"
echo ""
echo "─────────────────────────────────────────────────────────────────────────"
echo ""

log "Orchestration completed successfully!"
echo ""

exit 0


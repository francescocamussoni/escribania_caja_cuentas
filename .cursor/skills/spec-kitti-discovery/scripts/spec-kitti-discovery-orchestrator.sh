#!/usr/bin/env bash
set -euo pipefail

# spec-kitti-discovery-orchestrator.sh
# Runs the two zero-AI shell phases of the discovery pipeline:
#   Phase 1 — Indexer    → .spec-kitti/discovery/raw_index.json
#   Phase 2 — Graph      → .spec-kitti/discovery/graph.json
#
# After this script finishes, the AI agent takes over to produce:
#   modules.md  architecture.md  bounded-contexts.md  diagram.md

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect context: user project (.spec-kitti/scripts/bash/) vs dev repo (scripts/bash/)
# In user project: grandparent of SCRIPT_DIR is ".spec-kitti" → go 3 levels up
# In dev repo:     grandparent of SCRIPT_DIR is the repo root  → go 2 levels up
_GRANDPARENT="$(basename "$(dirname "$(dirname "$SCRIPT_DIR")")")"
if [[ "$_GRANDPARENT" == ".spec-kitti" ]]; then
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
else
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

# Python scripts are co-located with the bash scripts in the same directory
PYTHON_DIR="$SCRIPT_DIR"

# ── Colors ────────────────────────────────────────────────────────────────────
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# ── Output paths ──────────────────────────────────────────────────────────────
readonly DISCOVERY_DIR="$PROJECT_ROOT/.spec-kitti/discovery"
readonly LOGS_DIR="$DISCOVERY_DIR/logs"
readonly RAW_INDEX="$DISCOVERY_DIR/raw_index.json"
readonly GRAPH="$DISCOVERY_DIR/graph.json"

# ── Argument parsing ──────────────────────────────────────────────────────────
LEGACY_PATH=""
FORCE=false
STEP=""       # index | graph | "" (both)
VERBOSE=false

usage() {
    cat << EOF
Usage: $(basename "$0") --legacy PATH [OPTIONS]

Required:
  --legacy PATH     Path to the legacy codebase root

Optional:
  --force           Re-run even if output artifacts already exist
  --step NAME       Run only one step: index | graph
  --verbose         Verbose output
  -h, --help        Show this help

Examples:
  $(basename "$0") --legacy /path/to/legacy
  $(basename "$0") --legacy /path/to/legacy --force
  $(basename "$0") --legacy /path/to/legacy --step index
EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --legacy)   LEGACY_PATH="$2"; shift 2 ;;
        --force)    FORCE=true;        shift   ;;
        --step)     STEP="$2";         shift 2 ;;
        --verbose)  VERBOSE=true;      shift   ;;
        -h|--help)  usage; exit 0 ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}" >&2
            usage; exit 1
            ;;
    esac
done

# ── Validation ────────────────────────────────────────────────────────────────
if [[ -z "$LEGACY_PATH" ]]; then
    echo -e "${RED}Error: --legacy is required${NC}" >&2
    usage; exit 1
fi

if [[ ! -d "$LEGACY_PATH" ]]; then
    echo -e "${RED}Error: legacy path not found: $LEGACY_PATH${NC}" >&2
    exit 1
fi

# Resolve to absolute path
LEGACY_PATH="$(cd "$LEGACY_PATH" && pwd)"

# Validate --step if provided
if [[ -n "$STEP" ]]; then
    case "$STEP" in
        index|graph) ;;
        *)
            echo -e "${RED}Error: --step must be 'index' or 'graph'${NC}" >&2
            exit 1
            ;;
    esac
fi

mkdir -p "$DISCOVERY_DIR" "$LOGS_DIR"

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🔍 SPEC-KITTI DISCOVERY — Shell Phases              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Legacy:${NC}  $LEGACY_PATH"
echo -e "${GREEN}Output:${NC}  $DISCOVERY_DIR"
[[ "$FORCE"   == true ]] && echo -e "${YELLOW}Mode:${NC}    Force re-execution"
[[ -n "$STEP"         ]] && echo -e "${CYAN}Step:${NC}    $STEP only"
echo ""

# ── Python check ─────────────────────────────────────────────────────────────
PYTHON_BIN=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON_BIN="$candidate"
        break
    fi
done

if [[ -z "$PYTHON_BIN" ]]; then
    echo -e "${RED}Error: python3 is required but not found in PATH${NC}" >&2
    exit 1
fi

# ── Phase helpers ─────────────────────────────────────────────────────────────
VERBOSE_FLAG=""
[[ "$VERBOSE" == true ]] && VERBOSE_FLAG="--verbose"

run_indexer() {
    echo -e "${CYAN}━━ Phase 1/2 — Indexer (zero-AI scan) ━━━━━━━━━━━━━━━━━━━━${NC}"

    if [[ -f "$RAW_INDEX" ]] && [[ "$FORCE" != true ]]; then
        echo -e "${YELLOW}  Skipping: raw_index.json exists (--force to re-run)${NC}"
        echo ""
        return 0
    fi

    local log="$LOGS_DIR/indexer.log"
    echo "  Script: discovery_indexer.py"
    echo ""

    if "$PYTHON_BIN" "$PYTHON_DIR/discovery_indexer.py" \
        --legacy "$LEGACY_PATH" \
        --output "$RAW_INDEX" \
        $VERBOSE_FLAG 2>&1 | tee "$log"; then
        echo ""
        echo -e "  ${GREEN}✅ raw_index.json generated${NC}  ($(du -h "$RAW_INDEX" | cut -f1))"
    else
        echo ""
        echo -e "  ${RED}❌ Indexer failed — see log: $log${NC}" >&2
        exit 1
    fi
    echo ""
}

run_graph_builder() {
    echo -e "${CYAN}━━ Phase 2/2 — Graph Builder (zero-AI) ━━━━━━━━━━━━━━━━━━━${NC}"

    if [[ -f "$GRAPH" ]] && [[ "$FORCE" != true ]]; then
        echo -e "${YELLOW}  Skipping: graph.json exists (--force to re-run)${NC}"
        echo ""
        return 0
    fi

    if [[ ! -f "$RAW_INDEX" ]]; then
        echo -e "${RED}  Error: raw_index.json not found — run indexer first${NC}" >&2
        exit 1
    fi

    local log="$LOGS_DIR/graph-builder.log"
    echo "  Script: discovery_graph_builder.py"
    echo ""

    if "$PYTHON_BIN" "$PYTHON_DIR/discovery_graph_builder.py" \
        --input  "$RAW_INDEX" \
        --output "$GRAPH" \
        $VERBOSE_FLAG 2>&1 | tee "$log"; then
        echo ""
        echo -e "  ${GREEN}✅ graph.json generated${NC}  ($(du -h "$GRAPH" | cut -f1))"
    else
        echo ""
        echo -e "  ${RED}❌ Graph builder failed — see log: $log${NC}" >&2
        exit 1
    fi
    echo ""
}

# ── Execute ───────────────────────────────────────────────────────────────────
case "$STEP" in
    index) run_indexer ;;
    graph) run_graph_builder ;;
    "")
        run_indexer
        run_graph_builder
        ;;
esac

# ── Summary ───────────────────────────────────────────────────────────────────
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Shell phases complete — AI analysis ready            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Artifacts:${NC}"
[[ -f "$RAW_INDEX" ]] && echo "  raw_index.json   $(du -h "$RAW_INDEX" | cut -f1)"
[[ -f "$GRAPH"     ]] && echo "  graph.json       $(du -h "$GRAPH"     | cut -f1)"
echo ""
echo -e "${BLUE}Next:${NC} AI agent reads these and generates:"
echo "  modules.md · architecture.md · bounded-contexts.md · diagram.md"
echo ""
exit 0

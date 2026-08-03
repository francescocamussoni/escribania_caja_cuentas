#!/bin/bash
# ============================================================================
# Test de conexión a Jira y Confluence
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# scripts/bash → scripts → .spec-kitti → project root
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Ejecutar script de Python
python3 "$SCRIPT_DIR/../python/test_connection.py"


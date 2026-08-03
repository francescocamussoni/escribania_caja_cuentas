#!/bin/bash
# ============================================================================
# Spec-Kitti Sync - Sincroniza épica de Jira + documentación de Confluence
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_KITTI_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO_ROOT="$(cd "$SPEC_KITTI_DIR/.." && pwd)"

# Cargar funciones comunes
source "$SCRIPT_DIR/common.sh" 2>/dev/null || true

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Funciones
# ============================================================================

show_usage() {
    cat << EOF
Uso: $0 [OPCIONES]

Sincroniza épicas/historias de Jira y/o documentación de Confluence.

OPCIONES:
    --mode MODE             Qué fuentes sincronizar: jira | confluence | both (default: both)
    --epic-key KEY          Key de la épica (ej: PROJ-123) [requerido con --mode jira|both]
    --confluence-parent     Título de página padre en Confluence [OPCIONAL]
    --output DIR            Directorio de salida (default: .spec-kitti/)
    --log-level LEVEL       Nivel de logging: DEBUG | INFO | WARNING | ERROR (default: INFO)
    --json                  Salida en formato JSON
    --help                  Muestra esta ayuda

VARIABLES DE ENTORNO REQUERIDAS:
    JIRA_EMAIL              Email de Atlassian
    JIRA_API_TOKEN          Token de API de Atlassian
    JIRA_BASE_URL           URL base de Jira (ej: https://ueno-bank.atlassian.net)
    CONFLUENCE_BASE_URL     URL base de Confluence si está en otro dominio (opcional)
                            Si no se define, se usa JIRA_BASE_URL para Confluence también
    CONFLUENCE_SPACE_KEY    Space de Confluence (requerido para modo confluence/both)

EJEMPLOS:
    # Solo Jira (épica + historias)
    $0 --mode jira --epic-key PROJ-123

    # Solo Confluence (sin Jira)
    $0 --mode confluence --confluence-parent "API Documentation"

    # Jira + Confluence en dominios distintos (configurar CONFLUENCE_BASE_URL en .env)
    $0 --mode both --epic-key PROJ-123 --confluence-parent "API Documentation"

    # Con salida JSON
    $0 --mode jira --epic-key PROJ-123 --json

CONFIGURACIÓN:
    Puedes crear un archivo .env en la raíz del proyecto con:
        JIRA_EMAIL="tu@email.com"
        JIRA_API_TOKEN="ATATxxxxxxxxxx"
        JIRA_BASE_URL="https://ueno-bank.atlassian.net"
        CONFLUENCE_BASE_URL="https://itti-digital.atlassian.net"  # opcional
        CONFLUENCE_SPACE_KEY="TECH"

EOF
}

# ============================================================================
# Parsear argumentos
# ============================================================================

SYNC_MODE="both"
EPIC_KEY=""
CONFLUENCE_PARENT=""
OUTPUT_DIR=".spec-kitti"
JSON_OUTPUT=false
ISSUE_KEYS=""
LOG_LEVEL="INFO"

while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            SYNC_MODE="$2"
            shift 2
            ;;
        --epic-key)
            EPIC_KEY="$2"
            shift 2
            ;;
        --confluence-parent)
            CONFLUENCE_PARENT="$2"
            shift 2
            ;;
        --issue-keys)
            ISSUE_KEYS="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Argumento desconocido: $1${NC}" >&2
            show_usage
            exit 1
            ;;
    esac
done

# ============================================================================
# Validaciones
# ============================================================================

# Validar modo
if [[ ! "$SYNC_MODE" =~ ^(jira|confluence|both)$ ]]; then
    echo -e "${RED}Error: --mode debe ser 'jira', 'confluence' o 'both'${NC}" >&2
    show_usage
    exit 1
fi

# epic-key es requerido en modos jira y both
if [[ "$SYNC_MODE" != "confluence" && -z "$EPIC_KEY" ]]; then
    echo -e "${RED}Error: --epic-key es requerido cuando --mode es '${SYNC_MODE}'${NC}" >&2
    show_usage
    exit 1
fi

# Cargar .env si existe
if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    source "$REPO_ROOT/.env"
    set +a
    [ "$JSON_OUTPUT" = false ] && echo -e "${GREEN}✓${NC} Configuración cargada desde .env"
fi

# Validar credenciales
if [ -z "${JIRA_EMAIL:-}" ]; then
    echo -e "${RED}Error: JIRA_EMAIL no está configurado${NC}" >&2
    echo "Configura la variable de entorno o crea un archivo .env" >&2
    exit 1
fi

if [ -z "${JIRA_API_TOKEN:-}" ]; then
    echo -e "${RED}Error: JIRA_API_TOKEN no está configurado${NC}" >&2
    echo "Genera un token en: https://id.atlassian.com/manage-profile/security/api-tokens" >&2
    exit 1
fi

if [ -z "${JIRA_BASE_URL:-}" ]; then
    echo -e "${RED}Error: JIRA_BASE_URL no está configurado${NC}" >&2
    exit 1
fi

# ============================================================================
# Verificar Python 3.11+
# ============================================================================

find_python() {
    for cmd in python3.13 python3.12 python3.11 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local ver major minor
            ver=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [[ "$major" -gt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -ge 11 ]]; }; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_CMD=""
if ! PYTHON_CMD=$(find_python); then
    echo -e "${RED}Error: Python 3.11+ no está instalado.${NC}" >&2
    echo "" >&2
    echo -e "Ejecutá el script de setup para instalarlo automáticamente:" >&2
    echo -e "  ${YELLOW}bash $SPEC_KITTI_DIR/scripts/bash/setup-python.sh${NC}" >&2
    echo "" >&2
    echo -e "O instalalo manualmente:" >&2
    echo -e "  macOS:  ${GREEN}brew install python@3.11${NC}" >&2
    echo -e "  Ubuntu: ${GREEN}sudo apt install python3.11${NC}" >&2
    exit 1
fi

[ "$JSON_OUTPUT" = false ] && echo -e "${GREEN}✓${NC} Python: $($PYTHON_CMD --version 2>&1)"

# ============================================================================
# Ejecutar sync
# ============================================================================

PYTHON_SCRIPT="$SPEC_KITTI_DIR/scripts/python/sync_atlassian.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}Error: Script de Python no encontrado: $PYTHON_SCRIPT${NC}" >&2
    exit 1
fi

# Construir argumentos
ARGS=(
    "--mode" "$SYNC_MODE"
    "--output" "$OUTPUT_DIR"
)

if [ -n "$EPIC_KEY" ]; then
    ARGS+=("--epic-key" "$EPIC_KEY")
fi

if [ -n "$CONFLUENCE_PARENT" ]; then
    ARGS+=("--confluence-parent" "$CONFLUENCE_PARENT")
fi

if [ -n "$ISSUE_KEYS" ]; then
    ARGS+=("--issue-keys" "$ISSUE_KEYS")
fi

if [ "$JSON_OUTPUT" = true ]; then
    ARGS+=("--json")
fi

ARGS+=("--log-level" "$LOG_LEVEL")

# Ejecutar
if [ "$JSON_OUTPUT" = false ]; then
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Spec-Kitti Sync - Atlassian Integration${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
fi

"$PYTHON_CMD" "$PYTHON_SCRIPT" "${ARGS[@]}"
EXIT_CODE=$?

exit $EXIT_CODE


#!/usr/bin/env bash
# ============================================================================
# Spec-Kitti Setup - Instala Python 3.11+ y dependencias necesarias
# ============================================================================
#
# Uso: bash .spec-kitti/scripts/bash/setup-python.sh
#
# Qué hace:
#   1. Detecta el sistema operativo (macOS / Linux)
#   2. Instala Homebrew si no está (macOS)
#   3. Instala Python 3.11 si no está disponible
#   4. Instala las dependencias Python del proyecto (requests, python-dotenv)
#   5. Verifica que todo esté OK
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_KITTI_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

PYTHON_MIN_VERSION="3.11"

log_info()    { echo -e "${BLUE}ℹ${NC}  $*"; }
log_ok()      { echo -e "${GREEN}✓${NC}  $*"; }
log_warn()    { echo -e "${YELLOW}⚠${NC}  $*"; }
log_error()   { echo -e "${RED}✗${NC}  $*" >&2; }
log_section() { echo -e "\n${BOLD}${BLUE}▸ $*${NC}"; }

# ── Detectar OS ──────────────────────────────────────────────────────────────
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/redhat-release ]]; then
        echo "redhat"
    else
        echo "unknown"
    fi
}

# ── Verificar versión de Python ───────────────────────────────────────────────
python_version_ok() {
    local cmd="$1"
    if ! command -v "$cmd" &>/dev/null; then
        return 1
    fi
    local ver
    ver=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    local major minor
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    [[ "$major" -gt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -ge 11 ]]; }
}

# ── Encontrar el Python 3.11+ disponible ─────────────────────────────────────
find_python() {
    for cmd in python3.13 python3.12 python3.11 python3 python; do
        if python_version_ok "$cmd"; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

# ── Instalar Homebrew (macOS) ─────────────────────────────────────────────────
install_homebrew() {
    if command -v brew &>/dev/null; then
        log_ok "Homebrew ya está instalado ($(brew --version | head -1))"
        return 0
    fi

    log_info "Instalando Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Agregar brew al PATH para el resto del script
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi

    log_ok "Homebrew instalado"
}

# ── Instalar Python en macOS ──────────────────────────────────────────────────
install_python_macos() {
    install_homebrew

    log_info "Instalando Python ${PYTHON_MIN_VERSION} via Homebrew..."
    brew install python@3.11

    # Asegurar que el python recién instalado esté en el PATH
    if [[ -f /opt/homebrew/bin/python3.11 ]]; then
        export PATH="/opt/homebrew/bin:$PATH"
    elif [[ -f /usr/local/bin/python3.11 ]]; then
        export PATH="/usr/local/bin:$PATH"
    fi

    log_ok "Python ${PYTHON_MIN_VERSION} instalado"
}

# ── Instalar Python en Debian/Ubuntu ─────────────────────────────────────────
install_python_debian() {
    log_info "Instalando Python ${PYTHON_MIN_VERSION} via apt..."
    sudo apt-get update -qq
    sudo apt-get install -y python3.11 python3.11-venv python3-pip
    log_ok "Python ${PYTHON_MIN_VERSION} instalado"
}

# ── Instalar Python en RedHat/CentOS/Fedora ──────────────────────────────────
install_python_redhat() {
    log_info "Instalando Python ${PYTHON_MIN_VERSION} via dnf/yum..."
    if command -v dnf &>/dev/null; then
        sudo dnf install -y python3.11 python3-pip
    else
        sudo yum install -y python3.11 python3-pip
    fi
    log_ok "Python ${PYTHON_MIN_VERSION} instalado"
}

# ── Instalar dependencias Python del proyecto ─────────────────────────────────
install_python_deps() {
    local python_cmd="$1"

    log_section "Instalando dependencias Python"

    local requirements_file="$SPEC_KITTI_DIR/src/requirements.txt"

    if [[ -f "$requirements_file" ]]; then
        log_info "Instalando desde requirements.txt..."
        "$python_cmd" -m pip install --quiet -r "$requirements_file"
    else
        log_info "Instalando dependencias mínimas..."
        "$python_cmd" -m pip install --quiet requests python-dotenv
    fi

    log_ok "Dependencias instaladas"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║       Spec-Kitti · Setup de Python           ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
    echo ""

    local os
    os=$(detect_os)
    log_info "Sistema operativo: $os"

    # ── Paso 1: verificar si Python ya está disponible ──────────────────────
    log_section "Verificando Python ${PYTHON_MIN_VERSION}+"

    local python_cmd
    if python_cmd=$(find_python); then
        local ver
        ver=$("$python_cmd" --version 2>&1)
        log_ok "Python disponible: $ver (usando '$python_cmd')"
    else
        log_warn "Python ${PYTHON_MIN_VERSION}+ no encontrado — instalando..."

        case "$os" in
            macos)   install_python_macos ;;
            debian)  install_python_debian ;;
            redhat)  install_python_redhat ;;
            *)
                log_error "Sistema operativo no soportado para instalación automática."
                echo ""
                echo "Por favor instalá Python ${PYTHON_MIN_VERSION}+ manualmente:"
                echo "  macOS:  brew install python@3.11"
                echo "  Ubuntu: sudo apt install python3.11"
                echo "  Docs:   https://www.python.org/downloads/"
                exit 1
                ;;
        esac

        # Re-detectar después de la instalación
        if python_cmd=$(find_python); then
            log_ok "Python instalado correctamente: $("$python_cmd" --version 2>&1)"
        else
            log_error "La instalación falló. Por favor instalá Python ${PYTHON_MIN_VERSION}+ manualmente."
            exit 1
        fi
    fi

    # ── Paso 2: instalar dependencias ───────────────────────────────────────
    install_python_deps "$python_cmd"

    # ── Paso 3: verificación final ──────────────────────────────────────────
    log_section "Verificación final"

    if "$python_cmd" -c "import requests, dotenv; print('OK')" 2>/dev/null | grep -q "OK"; then
        log_ok "requests y python-dotenv disponibles"
    else
        log_warn "Algunas dependencias pueden faltar. Intentá correr:"
        echo "    $python_cmd -m pip install requests python-dotenv"
    fi

    echo ""
    echo -e "${GREEN}${BOLD}✅ Setup completado. Ya podés usar spec-kitti sync:${NC}"
    echo ""
    echo "    bash .spec-kitti/scripts/bash/spec-kitti-sync.sh --mode jira --epic-key PROJ-123"
    echo ""
}

main "$@"

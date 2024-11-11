#!/bin/bash

# Gamdl Project Setup Script
# Supports multiple operating systems and Python environments

# Color Output Formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check Prerequisites
check_prerequisites() {
    log_step "Checking System Prerequisites"

    # Check Operating System
    OS=$(uname -s)
    case "$OS" in
        Darwin)
            log_info "macOS detected"
            ;;
        Linux)
            log_info "Linux detected"
            ;;
        MINGW* | MSYS* | CYGWIN*)
            log_info "Windows detected"
            ;;
        *)
            log_error "Unsupported operating system"
            exit 1
            ;;
    esac

    # Check Python Installation
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi

    # Check Python Version
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [[ "$(printf '%s\n' "3.8" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.8" ]]; then
        log_error "Python 3.8+ is required. Current version: $PYTHON_VERSION"
        exit 1
    fi

    # Check pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is not installed"
        exit 1
    fi
}

# Create Virtual Environment
create_virtual_environment() {
    log_step "Setting Up Virtual Environment"

    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment"
        python3 -m venv .venv
    else
        log_warning "Virtual environment already exists"
    fi

    # Activate virtual environment
    source .venv/bin/activate
}

# Install System Dependencies
install_system_dependencies() {
    log_step "Installing System Dependencies"

    case "$OS" in
        Darwin)
            # macOS dependencies
            if ! command -v brew &> /dev/null; then
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install ffmpeg wget curl
            ;;
        Linux)
            # Linux dependencies (Ubuntu/Debian)
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y ffmpeg wget curl
            elif command -v yum &> /dev/null; then
                sudo yum install -y ffmpeg wget curl
            fi
            ;;
        MINGW* | MSYS* | CYGWIN*)
            # Windows dependencies via Chocolatey
            if ! command -v choco &> /dev/null; then
                log_error "Chocolatey not installed. Please install manually."
                exit 1
            fi
            choco install ffmpeg wget curl
            ;;
    esac
}

# Install Python Dependencies
install_python_dependencies() {
    log_step "Installing Python Dependencies"

    # Upgrade pip and setuptools
    pip3 install --upgrade pip setuptools wheel

    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        log_info "Python dependencies installed successfully"
    else
        log_error "requirements.txt not found"
        exit 1
    fi
}

# Configure Environment
configure_environment() {
    log_step "Configuring Environment"

    # Create necessary directories
    mkdir -p logs config downloads

    # Copy sample configuration files if not exists
    if [ ! -f "config/config.yaml" ]; then
        cp config/config.yaml.sample config/config.yaml
    fi

    # Set executable permissions
    chmod +x scripts/*.sh
    chmod +x scripts/*.py
}

# Run Initial Setup
main() {
    clear
    echo "Gamdl Project Setup Script"
    echo "========================="

    # Validate and setup
    check_prerequisites
    create_virtual_environment
    install_system_dependencies
    install_python_dependencies
    configure_environment

    log_info "Setup completed successfully!"
    log_warning "Please review and customize config files as needed."

    # Optionally activate virtual environment
    echo -e "\n${GREEN}Virtual environment activated. You can now run your project.${NC}"
}

# Allow script to be sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

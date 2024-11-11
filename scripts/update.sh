#!/bin/bash

# Gamdl Project Update Script
# Supports automated project updates and maintenance

# Color Output Formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

# Global Variables
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BACKUP_DIR="${PROJECT_DIR}/backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Pre-Update Checks
pre_update_checks() {
    log_step "Running Pre-Update Checks"

    # Check Git Installation
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed"
        exit 1
    fi

    # Check Internet Connectivity
    if ! ping -c 1 github.com &> /dev/null; then
        log_error "No internet connection"
        exit 1
    }

    # Check Git Repository
    if [ ! -d "${PROJECT_DIR}/.git" ]; then
        log_error "Not a git repository"
        exit 1
    }
}

# Backup Current Project
backup_project() {
    log_step "Creating Project Backup"

    # Create backup directory
    mkdir -p "${BACKUP_DIR}"

    # Backup project files
    local backup_file="${BACKUP_DIR}/gamdl_backup_${TIMESTAMP}.tar.gz"
    tar -czvf "${backup_file}" \
        --exclude='.venv' \
        --exclude='downloads' \
        --exclude='logs' \
        --exclude='.git' \
        "${PROJECT_DIR}"

    log_info "Backup created: ${backup_file}"
}

# Update Project Dependencies
update_dependencies() {
    log_step "Updating Project Dependencies"

    # Activate virtual environment
    source .venv/bin/activate

    # Update pip and setuptools
    pip install --upgrade pip setuptools wheel

    # Update Python dependencies
    pip list --outdated

    log_warning "Do you want to upgrade all Python packages? (y/n)"
    read -r upgrade_choice

    if [[ "$upgrade_choice" =~ ^[Yy]$ ]]; then
        pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip install -U
        pip freeze > requirements.txt
        log_info "Python dependencies updated"
    fi
}

# Git Update Process
git_update() {
    log_step "Updating Project via Git"

    # Fetch latest changes
    git fetch origin

    # Check current branch
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    log_info "Current Branch: ${CURRENT_BRANCH}"

    # Pull latest changes
    git pull origin "${CURRENT_BRANCH}"

    # Check for conflicts
    if [ $? -ne 0 ]; then
        log_error "Git pull failed. Resolve conflicts manually."
        exit 1
    }
}

# Post-Update Configuration
post_update_config() {
    log_step "Performing Post-Update Configuration"

    # Update configuration files
    if [ -f "config/config.yaml.sample" ]; then
        log_warning "New sample configuration detected. Compare with your current config."
        diff config/config.yaml config/config.yaml.sample
    }

    # Run database migrations if applicable
    if [ -f "scripts/migrate.sh" ]; then
        bash scripts/migrate.sh
    }

    # Rebuild virtual environment if requirements changed
    if git diff --name-only | grep -q "requirements.txt"; then
        log_info "Requirements changed. Rebuilding virtual environment..."
        rm -rf .venv
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
    }
}

# Cleanup Old Backups
cleanup_backups() {
    log_step "Cleaning Up Old Backups"

    # Remove backups older than 30 days
    find "${BACKUP_DIR}" -type f -name "gamdl_backup_*.tar.gz" -mtime +30 -delete
    log_info "Old backups removed"
}

# Version Tracking
track_version() {
    log_step "Tracking Version Changes"

    # Get current and latest versions
    CURRENT_VERSION=$(git describe --tags --abbrev=0)
    LATEST_VERSION=$(git ls-remote --tags origin | awk '{print $2}' | grep -v '{}' | sort -V | tail -n1 | sed 's/refs\/tags\///')

    if [ "${CURRENT_VERSION}" != "${LATEST_VERSION}" ]; then
        log_info "Version Update Available:"
        log_info "Current: ${CURRENT_VERSION}"
        log_info "Latest:  ${LATEST_VERSION}"
    else
        log_info "Project is up-to-date"
    }
}

# Main Update Function
update_project() {
    clear
    echo "Gamdl Project Update Script"
    echo "=========================="

    # Confirm update
    log_warning "This will update your Gamdl project. Ensure all work is saved."
    log_warning "Do you want to continue? (y/n)"
    read -r confirm

    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Update cancelled"
        exit 0
    }

    # Update sequence
    pre_update_checks
    backup_project
    git_update
    update_dependencies
    post_update_config
    cleanup_backups
    track_version

    log_info "Update completed successfully!"
}

# Execute update
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    cd "${PROJECT_DIR}" || exit
    update_project
fi

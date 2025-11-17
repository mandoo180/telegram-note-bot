#!/bin/bash
set -e

# Telegram Note Bot Deployment Script
# Pulls latest image from GitHub Container Registry and deploys

# Configuration
GITHUB_USER="${GITHUB_USER:-mandoo180}"
REPO_NAME="${REPO_NAME:-telegram-note-bot}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_NAME="telegram-note-bot"
DATA_DIR="${DATA_DIR:-$(pwd)/data}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_env() {
    if [ ! -f .env ]; then
        log_error ".env file not found!"
        log_info "Copy .env.example to .env and configure your settings:"
        log_info "  cp .env.example .env"
        log_info "  nano .env"
        exit 1
    fi

    # Check for required variables in .env
    if ! grep -q "TELEGRAM_BOT_TOKEN" .env || grep -q "TELEGRAM_BOT_TOKEN=your_token_here" .env; then
        log_error "TELEGRAM_BOT_TOKEN not configured in .env"
        exit 1
    fi

    log_info "Environment configuration OK"
}

pull_image() {
    local image="ghcr.io/${GITHUB_USER}/${REPO_NAME}:${IMAGE_TAG}"
    log_info "Pulling image: ${image}"

    if ! docker pull "${image}"; then
        log_error "Failed to pull image from GHCR"
        log_warn "If the repository is private, authenticate first:"
        log_warn "  echo \$GITHUB_TOKEN | docker login ghcr.io -u ${GITHUB_USER} --password-stdin"
        exit 1
    fi

    log_info "Image pulled successfully"
}

stop_old_container() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_info "Stopping old container..."
        docker stop "${CONTAINER_NAME}" || true
        docker rm "${CONTAINER_NAME}" || true
        log_info "Old container removed"
    else
        log_info "No existing container found"
    fi
}

create_data_dir() {
    if [ ! -d "${DATA_DIR}" ]; then
        log_info "Creating data directory: ${DATA_DIR}"
        mkdir -p "${DATA_DIR}"
    fi

    # Initialize database if it doesn't exist
    if [ ! -f "${DATA_DIR}/telegram_note.db" ]; then
        log_info "Initializing database..."
        docker run --rm \
            -v "${DATA_DIR}:/app/data" \
            -e DATABASE_PATH=/app/data/telegram_note.db \
            "ghcr.io/${GITHUB_USER}/${REPO_NAME}:${IMAGE_TAG}" \
            python init_db.py
        log_info "Database initialized"
    fi
}

start_container() {
    log_info "Starting new container..."

    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        --env-file .env \
        -e DATABASE_PATH=/app/data/telegram_note.db \
        -v "${DATA_DIR}:/app/data" \
        "ghcr.io/${GITHUB_USER}/${REPO_NAME}:${IMAGE_TAG}"

    log_info "Container started successfully"
}

verify_deployment() {
    log_info "Verifying deployment..."

    # Wait a moment for container to start
    sleep 2

    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "Container is not running!"
        log_error "Check logs with: docker logs ${CONTAINER_NAME}"
        exit 1
    fi

    # Check version
    log_info "Bot version:"
    docker exec "${CONTAINER_NAME}" python -c "import sys; sys.path.insert(0, '/app/src'); from version import __version__; print(f'  Version: {__version__}')" 2>/dev/null || log_warn "Could not retrieve version"

    # Show container status
    log_info "Container status:"
    docker ps --filter "name=${CONTAINER_NAME}" --format "  ID: {{.ID}}\n  Status: {{.Status}}\n  Image: {{.Image}}"

    log_info ""
    log_info "✅ Deployment successful!"
    log_info ""
    log_info "Next steps:"
    log_info "  • Test with: /version in Telegram"
    log_info "  • View logs: docker logs -f ${CONTAINER_NAME}"
    log_info "  • Check reminders: docker exec ${CONTAINER_NAME} python check_reminders.py"
}

show_logs() {
    log_info "Showing recent logs (Ctrl+C to exit)..."
    docker logs -f --tail 50 "${CONTAINER_NAME}"
}

# Main deployment flow
main() {
    echo "================================================"
    echo "   Telegram Note Bot - Deployment Script"
    echo "================================================"
    echo ""

    log_info "Image: ghcr.io/${GITHUB_USER}/${REPO_NAME}:${IMAGE_TAG}"
    log_info "Container: ${CONTAINER_NAME}"
    log_info "Data directory: ${DATA_DIR}"
    echo ""

    check_env
    pull_image
    stop_old_container
    create_data_dir
    start_container
    verify_deployment

    # Ask if user wants to see logs
    read -p "View logs? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        show_logs
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Deploy Telegram Note Bot from GitHub Container Registry"
        echo ""
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --logs              Show logs only"
        echo "  --status            Show container status only"
        echo ""
        echo "Environment variables:"
        echo "  GITHUB_USER         GitHub username (default: mandoo180)"
        echo "  REPO_NAME          Repository name (default: telegram-note-bot)"
        echo "  IMAGE_TAG          Image tag to pull (default: latest)"
        echo "  DATA_DIR           Data directory path (default: ./data)"
        echo ""
        echo "Examples:"
        echo "  $0                                    # Deploy latest version"
        echo "  IMAGE_TAG=sha-abc123 $0               # Deploy specific version"
        echo "  $0 --logs                             # View logs"
        ;;
    --logs)
        docker logs -f "${CONTAINER_NAME}"
        ;;
    --status)
        docker ps --filter "name=${CONTAINER_NAME}"
        echo ""
        docker exec "${CONTAINER_NAME}" python -c "import sys; sys.path.insert(0, '/app/src'); from version import __version__; print(f'Version: {__version__}')" 2>/dev/null || echo "Could not retrieve version"
        ;;
    *)
        main
        ;;
esac

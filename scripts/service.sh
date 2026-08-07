#!/usr/bin/env bash
#
# Manage googlecast-mcp as a systemd service.
#
#   ./scripts/service.sh install     # create the unit, enable at boot, start it
#   ./scripts/service.sh remove      # stop, disable, delete the unit
#   ./scripts/service.sh start|stop|restart|status|logs
#
# The server runs over HTTP so remote MCP clients (e.g. Claude Desktop on
# another machine) can reach it. It must stay on the same LAN as the speakers:
# discovery uses mDNS, and the speakers fetch the TTS audio back from it.
#
# Override defaults via the environment, e.g.:
#   MCP_PORT=9000 ./scripts/service.sh install

set -euo pipefail

SERVICE_NAME="googlecast-mcp"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${MCP_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "$RUN_USER")"

# MCP endpoint: bound to all interfaces so other machines can connect.
MCP_HOST="${MCP_HOST:-0.0.0.0}"
MCP_PORT="${MCP_PORT:-8765}"
# Fixed port for serving TTS audio to the speakers; keeps firewall rules simple.
MEDIA_PORT="${MEDIA_PORT:-8766}"
# Extra flags, e.g. MCP_EXTRA_ARGS="--allow-host cast.example.com" when a
# reverse proxy fronts the server under a domain name.
MCP_EXTRA_ARGS="${MCP_EXTRA_ARGS:-}"

die() { echo "error: $*" >&2; exit 1; }

require_uv() {
    UV_BIN="${UV_BIN:-$(command -v uv || true)}"
    [ -n "$UV_BIN" ] || die "uv not found in PATH; set UV_BIN=/path/to/uv"
}

lan_ip() {
    ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}'
}

cmd_install() {
    require_uv
    [ -d "$PROJECT_DIR/src/googlecast_mcp" ] || die "not a googlecast-mcp checkout: $PROJECT_DIR"

    echo "Installing $SERVICE_NAME (user=$RUN_USER, mcp=$MCP_HOST:$MCP_PORT, media=$MEDIA_PORT)"
    # Make sure dependencies are present before systemd tries to run it.
    (cd "$PROJECT_DIR" && "$UV_BIN" sync --frozen 2>/dev/null || "$UV_BIN" sync)

    sudo tee "$UNIT_PATH" >/dev/null <<EOF
[Unit]
Description=googlecast-mcp — MCP server for Google Cast speakers
Documentation=file://$PROJECT_DIR/README.md
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_DIR
Environment=HOME=$HOME
Environment=GOOGLECAST_MCP_MEDIA_PORT=$MEDIA_PORT
ExecStart=$UV_BIN run --directory $PROJECT_DIR googlecast-mcp \\
    --transport http --host $MCP_HOST --port $MCP_PORT $MCP_EXTRA_ARGS
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable --now "$SERVICE_NAME"
    sleep 2
    sudo systemctl --no-pager --lines=0 status "$SERVICE_NAME" || true

    local ip
    ip="$(lan_ip)"
    cat <<EOF

Installed. MCP endpoint for remote clients:

    http://${ip:-<this-host>}:$MCP_PORT/mcp

If a firewall is active, allow both ports from the LAN:

    sudo ufw allow from 192.168.0.0/16 to any port $MCP_PORT proto tcp
    sudo ufw allow from 192.168.0.0/16 to any port $MEDIA_PORT proto tcp
EOF
}

cmd_remove() {
    echo "Removing $SERVICE_NAME"
    sudo systemctl disable --now "$SERVICE_NAME" 2>/dev/null || true
    sudo rm -f "$UNIT_PATH"
    sudo systemctl daemon-reload
    echo "Removed. The device list in ~/.googlecast-mcp was left in place."
}

cmd_status() { systemctl --no-pager --lines=0 status "$SERVICE_NAME"; }

case "${1:-}" in
    install) cmd_install ;;
    remove)  cmd_remove ;;
    start)   sudo systemctl start "$SERVICE_NAME"; cmd_status ;;
    stop)    sudo systemctl stop "$SERVICE_NAME"; echo "stopped" ;;
    restart) sudo systemctl restart "$SERVICE_NAME"; cmd_status ;;
    status)  cmd_status ;;
    logs)    journalctl -u "$SERVICE_NAME" -f -n 50 ;;
    *)
        sed -n '3,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
        exit 1
        ;;
esac

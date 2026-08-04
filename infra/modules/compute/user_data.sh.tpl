#!/bin/bash
set -euo pipefail

INSTALL_DIR="/opt/escribania"
LOG_FILE="/var/log/escribania-bootstrap.log"

exec > >(tee -a "$${LOG_FILE}") 2>&1
echo "=== Escribania API bootstrap $$(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

dnf update -y
dnf install -y docker aws-cli python3
systemctl enable docker
systemctl start docker

dnf install -y docker-compose-plugin || true
if ! docker compose version >/dev/null 2>&1; then
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -fsSL "https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-linux-aarch64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

mkdir -p "$${INSTALL_DIR}"
chmod 755 "$${INSTALL_DIR}"

cat > "$${INSTALL_DIR}/config.env" <<EOF
AWS_REGION=${aws_region}
APP_ENVIRONMENT=${app_environment}
RDS_HOST=${rds_host}
RDS_PORT=${rds_port}
RDS_DB=${rds_database_name}
RDS_USER=${rds_master_username}
SSM_JWT_PARAM=${ssm_jwt_parameter_name}
SSM_DB_PASSWORD_PARAM=${ssm_db_password_parameter_name}
SSM_ADMIN_USERNAME_PARAM=${ssm_admin_username_parameter_name}
SSM_ADMIN_PASSWORD_PARAM=${ssm_admin_password_parameter_name}
SSM_CORS_PARAM=${ssm_cors_origins_parameter_name}
CORS_ORIGINS=${cors_origins}
EOF

cat > "$${INSTALL_DIR}/docker-compose.yml" <<'COMPOSEEOF'
${docker_compose_yml}
COMPOSEEOF

cat > "$${INSTALL_DIR}/load-env-from-ssm.sh" <<'LOADEOF'
${load_env_script}
LOADEOF

chmod 700 "$${INSTALL_DIR}/load-env-from-ssm.sh"

cat > /etc/systemd/system/escribania-api.service <<'UNITEOF'
[Unit]
Description=Escribania Registro de Cajas API (Docker)
After=docker.service network-online.target
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/escribania
ExecStartPre=/opt/escribania/load-env-from-ssm.sh
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
UNITEOF

systemctl daemon-reload
systemctl enable escribania-api.service

"$${INSTALL_DIR}/load-env-from-ssm.sh" || echo "WARN: SSM env load failed (RDS/SSM may not be ready yet)"

if docker image inspect escribania-backend:latest >/dev/null 2>&1; then
  systemctl start escribania-api.service
  echo "API service started"
else
  echo "Image escribania-backend:latest not present; start after deploy-aws.sh loads the image"
fi

echo "=== Bootstrap complete ==="

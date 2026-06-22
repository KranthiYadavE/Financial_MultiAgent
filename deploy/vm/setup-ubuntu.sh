#!/bin/bash
# Bootstrap Ubuntu 22.04/24.04 VM for Financial Multi-Agent (Oracle/AWS/GCP free tier)
set -euo pipefail

echo "=== Installing Docker ==="
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker "$USER"

echo "=== Firewall (UFW) — open API ports ==="
sudo ufw allow OpenSSH
sudo ufw allow 8000/tcp comment "orchestrator"
sudo ufw allow 8020/tcp comment "mcp-server"
sudo ufw --force enable || true

echo ""
echo "=== Done ==="
echo "Log out and back in for docker group, then:"
echo "  git clone https://github.com/KranthiYadavE/Financial_MultiAgent.git"
echo "  cd Financial_MultiAgent"
echo "  cp deploy/cloud/.env.cloud.example .env   # edit POSTGRES_PASSWORD"
echo "  docker compose -f docker-compose.cloud.yml up -d --build"
echo "  docker compose -f docker-compose.cloud.yml --profile init run --rm data-init"
echo ""
echo "Test: curl http://$(curl -s ifconfig.me 2>/dev/null || echo YOUR_VM_IP):8000/health"

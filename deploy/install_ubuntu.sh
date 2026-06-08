#!/usr/bin/env bash
set -e
APP_DIR="/opt/tool-consegne"
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git
cd "$APP_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo tee /etc/systemd/system/tool-consegne.service > /dev/null <<EOF
[Unit]
Description=Tool Consegne Aziendale V2
After=network.target
[Service]
WorkingDirectory=$APP_DIR
Environment=APP_USER=admin
Environment=APP_PASSWORD=cambiaquesta
Environment=APP_SECRET=cambia-questa-chiave-lunga
Environment=DATABASE_URL=sqlite:///./data/consegne.db
ExecStart=$APP_DIR/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable tool-consegne
sudo systemctl restart tool-consegne
echo "Tool avviato su 127.0.0.1:8000"

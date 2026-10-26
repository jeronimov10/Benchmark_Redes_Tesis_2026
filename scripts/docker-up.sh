#!/bin/sh
# Levanta el proyecto con Docker en Linux/macOS. Si tu red intercepta HTTPS, copia su CA raiz (PEM, extension .crt) a certs/ antes.
set -e
cd "$(dirname "$0")/.."
docker compose up --build -d
echo "Frontend: http://localhost:3000   Backend: http://localhost:8000/docs   (logs: docker compose logs -f backend)"

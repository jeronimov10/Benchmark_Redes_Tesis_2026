CAs adicionales para las imagenes Docker (opcional).

Si tu antivirus o red corporativa intercepta HTTPS (Avast/AVG/Kaspersky/ESET/Zscaler...), los contenedores no confian en su CA y todas las
consultas fallan con CERTIFICATE_VERIFY_FAILED. Copia aqui la CA raiz en formato PEM con extension .crt (scripts/docker-up.ps1 lo hace solo)
y reconstruye: docker compose build --no-cache. Los .crt de esta carpeta no se versionan.

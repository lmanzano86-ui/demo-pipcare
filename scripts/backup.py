#!/usr/bin/env python
"""Respaldo cifrado de la base de datos (HIPAA 164.308(a)(7) - Plan de contingencia).

- Hace pg_dump completo (todos los schemas de clínicas) en formato custom.
- Cifra con AES-256-CBC (openssl, PBKDF2) usando BACKUP_ENCRYPTION_KEY.
- Guarda en BACKUP_DIR con manifiesto SHA-256 y rota archivos viejos
  (BACKUP_RETENTION_DAYS, por defecto 30).

Uso:
    BACKUP_ENCRYPTION_KEY='<clave>' python scripts/backup.py
    # Docker (desde el host):
    #   docker compose exec -T web python scripts/backup.py
    # Cron diario (ej. 2:00 AM):
    #   0 2 * * * cd /ruta/sistema-clinicas && BACKUP_ENCRYPTION_KEY='...' \
    #       .venv/bin/python scripts/backup.py >> logs/backup.log 2>&1

RPO: <= 24 h (respaldo diario). RTO objetivo: <= 4 h (ver scripts/restore.py).
La clave de cifrado debe guardarse SEPARADA de los respaldos (gestor de
secretos). Sin la clave, los respaldos son irrecuperables.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "apps"))

# Cargar .env si existe (misma convención que manage.py)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", str(BASE_DIR / "backups")))
RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")
ENCRYPTION_KEY = os.environ.get("BACKUP_ENCRYPTION_KEY", "")


def find_bin(name):
    # 1) pgserver embebido (desarrollo local)
    p = (BASE_DIR / ".venv" / "lib" / "python3.12" / "site-packages"
         / "pgserver" / "pginstall" / "bin" / name)
    if p.exists():
        return str(p)
    # 2) PATH del sistema (Docker: imagen postgres)
    found = shutil.which(name)
    if found:
        return found
    raise SystemExit(f"No se encontró {name}: instale PostgreSQL client o use Docker.")


def run(cmd, **kw):
    print("+", " ".join(cmd[:3]), "...")
    subprocess.run(cmd, check=True, **kw)


def main():
    if not DATABASE_URL:
        raise SystemExit("Falta DATABASE_URL en el entorno.")
    if not ENCRYPTION_KEY:
        raise SystemExit("Falta BACKUP_ENCRYPTION_KEY en el entorno. "
                         "Sin clave no se cifra: el respaldo se aborta.")
    if len(ENCRYPTION_KEY) < 32:
        raise SystemExit("BACKUP_ENCRYPTION_KEY debe tener al menos 32 caracteres.")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dump_file = BACKUP_DIR / f"clinicas-{stamp}.dump"
    enc_file = BACKUP_DIR / f"clinicas-{stamp}.dump.enc"

    print(f"[{stamp}] Iniciando respaldo...")
    # 1) pg_dump completo (todos los schemas de clínicas)
    run([find_bin("pg_dump"), "--dbname=" + DATABASE_URL, "-Fc",
         "-f", str(dump_file)])

    # 2) SHA-256 del dump sin cifrar (para verificar integridad al restaurar)
    sha = hashlib.sha256(dump_file.read_bytes()).hexdigest()

    # 3) Cifrar con AES-256-CBC + PBKDF2
    run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt",
         "-in", str(dump_file), "-out", str(enc_file),
         "-pass", f"env:BACKUP_ENCRYPTION_KEY"])
    dump_file.unlink()  # borrar el sin cifrar de inmediato

    # 4) Manifiesto
    manifest = {
        "created_at": stamp,
        "file": enc_file.name,
        "sha256_plain": sha,
        "size_bytes": enc_file.stat().st_size,
        "algorithm": "AES-256-CBC/PBKDF2",
        "retention_days": RETENTION_DAYS,
    }
    (BACKUP_DIR / f"{enc_file.stem}.json").write_text(json.dumps(manifest, indent=2))

    # 5) Rotación: borrar respaldos más viejos que la retención
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    removed = 0
    for f in BACKUP_DIR.glob("clinicas-*.dump.enc"):
        try:
            fdate = datetime.strptime(f.stem.split("clinicas-")[1].split(".")[0],
                                      "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if fdate < cutoff:
            f.unlink()
            mf = f.with_suffix(".json")
            if mf.exists():
                mf.unlink()
            removed += 1

    print(f"Respaldo OK: {enc_file.name} "
          f"({manifest['size_bytes'] / 1048576:.1f} MB cifrado). "
          f"Rotación: {removed} archivo(s) viejo(s) eliminado(s).")
    print("IMPORTANTE: guarde BACKUP_ENCRYPTION_KEY fuera de este servidor.")


if __name__ == "__main__":
    main()

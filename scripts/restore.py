#!/usr/bin/env python
"""Restaura un respaldo cifrado (ver scripts/backup.py).

Uso:
    BACKUP_ENCRYPTION_KEY='<clave>' python scripts/restore.py <archivo.dump.enc>
        [--target-url postgresql://... ]   # por defecto usa DATABASE_URL

¡CUIDADO! La restauración con --clean borra los datos actuales de la BD
destino. Para pruebas, restaure en una BD vacía separada.

Procedimiento de desastre (RTO objetivo <= 4 h):
  1. Levantar infraestructura (docker compose up -d db).
  2. Crear la BD vacía si no existe.
  3. Ejecutar este script con la clave de cifrado (desde el gestor de secretos).
  4. Correr migraciones si el respaldo es anterior al código: migrate_schemas.
  5. Verificar: entrar al sistema, revisar 1 clínica, 1 paciente, 1 reclamo.
"""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

ENCRYPTION_KEY = os.environ.get("BACKUP_ENCRYPTION_KEY", "")


def find_bin(name):
    p = (BASE_DIR / ".venv" / "lib" / "python3.12" / "site-packages"
         / "pgserver" / "pginstall" / "bin" / name)
    if p.exists():
        return str(p)
    found = shutil.which(name)
    if found:
        return found
    raise SystemExit(f"No se encontró {name}.")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: restore.py <archivo.dump.enc> [--target-url URL]")
    enc_file = Path(sys.argv[1])
    if not enc_file.exists():
        raise SystemExit(f"No existe: {enc_file}")
    if not ENCRYPTION_KEY or len(ENCRYPTION_KEY) < 32:
        raise SystemExit("Falta BACKUP_ENCRYPTION_KEY válida en el entorno.")

    target = os.environ.get("DATABASE_URL", "")
    if "--target-url" in sys.argv:
        target = sys.argv[sys.argv.index("--target-url") + 1]
    if not target:
        raise SystemExit("Falta DATABASE_URL o --target-url.")

    tmp = enc_file.with_suffix(".tmp.dump")
    print(f"Descifrando {enc_file.name}...")
    subprocess.run(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2",
         "-in", str(enc_file), "-out", str(tmp),
         "-pass", "env:BACKUP_ENCRYPTION_KEY"],
        check=True)
    try:
        # Verificar integridad contra el manifiesto si existe
        mf = enc_file.with_suffix(".json")
        if mf.exists():
            import json
            expected = json.loads(mf.read_text()).get("sha256_plain")
            actual = hashlib.sha256(tmp.read_bytes()).hexdigest()
            if expected != actual:
                raise SystemExit("¡INTEGRIDAD FALLIDA! El respaldo no coincide "
                                 "con el manifiesto. No se restaura.")
            print("Integridad verificada (SHA-256 OK).")
        print(f"Restaurando en la BD destino (se reemplazarán los datos)...")
        subprocess.run(
            [find_bin("pg_restore"), "--dbname=" + target,
             "--clean", "--if-exists", "--no-owner", str(tmp)],
            check=True)
        print("Restauración OK. Verifique el sistema antes de ponerlo en línea.")
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

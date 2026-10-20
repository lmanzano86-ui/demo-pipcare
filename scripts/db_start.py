"""Arranca PostgreSQL (pgserver) en modo persistente para desarrollo local."""
import pgserver

PGDATA = "/home/hatch/workspace/sistema-clinicas/.pgdata"

srv = pgserver.get_server(PGDATA, cleanup_mode=None)
uri = srv.get_uri("clinicas")
print(uri)

# Runbook — Publicar la DEMO de PIPCare

**Estado:** demo verificada localmente el 19 oct 2026 (9/9 comprobaciones OK,
ver `demo-preview/`). **NO publicar sin el «Sí» explícito de Lester.**

Esta demo es una herramienta de **ventas**: muestra el sistema con datos
**100% ficticios** (pacientes "María Gómez", "Juan Pérez", teléfonos 555).
**NUNCA ingresar datos reales de pacientes en la demo pública.**

---

## 1. Dónde publicarla (decisión de Lester)

| Opción | Costo | Notas |
|---|---|---|
| **A. Render / Railway / Fly.io** (plan gratuito o básico) | $0–$7/mes | La vía $0 del plan. **Sin BAA** — solo datos ficticios, nunca PHI real. PostgreSQL gestionado incluido o por separado. |
| **B. Docker en la PC de Lester + túnel** (Cloudflare Tunnel / ngrok) | $0 | Control total, la demo vive en su máquina. Requiere que la PC esté encendida durante las demos. |
| **C. VPS barato** (Hetzner / Contabo, ~$5/mes) + Docker | ~$5/mes | Más estable que A. **Sin BAA** — solo demo ficticia. |

**Producción real con PHI de pacientes: SOLO AWS con BAA firmado**
(vía AWS Artifact), al firmar el primer cliente. Ver
`Checklist-Despliegue-Produccion.pdf` en Drive. La demo NUNCA se convierte
en producción: cuando llegue el primer cliente se despliega infraestructura
separada con cifrado KMS, secretos en Secrets Manager y cron de respaldos.

---

## 2. Variables de entorno (obligatorias)

```bash
DJANGO_SECRET_KEY=<generar una nueva: python -c "import secrets; print(secrets.token_urlsafe(50))">
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<dominio de la demo>          # ej: demo-pipcare.onrender.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<dominio de la demo>
DATABASE_URL=<la que provea el hosting>             # en Docker local: postgresql://clinicas:clinicas@db:5432/clinicas
```

**NO copiar el `.env` de desarrollo** (trae `DJANGO_SECRET_KEY=dev-local-no-usar-en-produccion`
y `DEBUG=True`). El zip del código **no incluye `.env`** a propósito.

Opcionales (demo): sin `TWILIO_*` los SMS quedan en modo demo (se registran,
no se envían); sin `EDI_*` la transmisión 837P queda en descarga manual.
Para la demo de ventas no se necesitan.

---

## 3. Pasos de despliegue (cualquier opción)

```bash
# 1. Clonar / extraer el código (zip de Drive, carpeta "sistema clinicas")
#    Si se extrae un zip nuevo: conservar el .env propio.

# 2. Configurar las variables de entorno del §2

# 3. Construir y levantar
docker compose up --build -d        # o el deploy del hosting elegido

# 4. Migraciones (todos los schemas: público + tenants)
docker compose exec web python manage.py migrate_schemas

# 5. Datos de demostración (idempotente: no duplica si ya existen)
docker compose exec web python manage.py shell -c "
from django_tenants.utils import schema_context
exec(open('scripts/seed.py').read().split('django.setup()')[1])
"
# Alternativa simple: docker compose exec web python scripts/seed.py

# 6. Crear el usuario demo para visitantes (rol frontdesk, sin MFA forzado)
docker compose exec web python manage.py shell <<'EOF'
from django_tenants.utils import schema_context
from django.contrib.auth.models import User
from accounts.models import Profile
with schema_context("clinica_demo"):
    u, c = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
    if c:
        u.set_password("demo123"); u.save()
    Profile.objects.get_or_create(user=u, defaults={"role": "frontdesk"})
    print("demo / demo123 listo")
EOF
```

> **Credenciales de la demo:**
> - Visitantes: `demo / demo123` (rol frontdesk — entra directo, sin MFA).
> - Admin: `admin / admin123` — tiene **MFA TOTP activado** (verificado 19 oct 2026):
>   al entrar pide el segundo factor. Para la demo pública, entregar solo las
>   credenciales de `demo`; el acceso admin se muestra en demos guiadas por Lester.

---

## 4. Verificación post-despliegue (checklist)

Con el dominio de la demo (p. ej. `https://demo-pipcare.onrender.com`;
el tenant demo responde en el dominio raíz si es el único, o en
`clinica-demo.<dominio>` según la configuración de dominios):

- [ ] `/` carga la portada pública (200)
- [ ] El modal "Iniciar sesión" abre y `demo / demo123` entra a `/inicio/`
- [ ] `/inicio/` muestra el panel con datos ficticios
- [ ] `/agenda/` carga la vista de día
- [ ] Un reclamo genera el CMS-1500 en PDF (`/reclamo/<id>/pdf/`)
- [ ] `/terminos/` y `/privacidad/` cargan (footer)
- [ ] `admin / admin123` pide el segundo factor MFA (comportamiento esperado)

---

## 5. Reglas de seguridad de la demo

1. **Datos ficticios solamente.** Si alguien ingresa un dato real por error,
   borrarlo de inmediato (no hay BAA en la demo).
2. **Credenciales visibles:** `demo/demo123` es pública por diseño; si se
   abusa (spam de datos), rotar la contraseña y re-seedear.
3. **No indexar (opcional):** si no se quiere que Google la encuentre,
   agregar `Disallow: /` en `robots.txt` o no enlazarla públicamente.
4. **Respaldos:** la demo no lleva PHI; con re-seedear basta. No programar
   el cron de respaldos cifrados aquí (eso es para producción).
5. **Separación total:** la demo y producción son despliegues distintos,
   con bases de datos distintas. Nunca mezclar.

---

## 6. Qué necesita Lester aportar (nada se publica sin esto)

- [ ] **El «Sí» explícito** a publicar la demo.
- [ ] **Decisión de dónde** (opción A, B o C del §1).
- [ ] **Cuenta** en el hosting elegido (si aplica) y **dominio** (opcional;
        sin dominio propio se usa el subdominio del hosting).
- [ ] Confirmar las **credenciales públicas** (`demo / demo123`) o pedir
        otras.

## 7. Qué ya está listo (no depende de Lester)

- Código verificado end-to-end en local (9/9 OK el 19 oct 2026).
- Migraciones al día; `seed.py` idempotente; usuario `demo` creado en el
  tenant de demostración.
- 4 capturas de referencia en `demo-preview/` (landing, panel, agenda,
  cumplimiento).
- PDFs comerciales y de cumplimiento en Drive, carpeta "sistema clinicas".
- Pendiente **antes del primer cliente real** (no de la demo): licencia CPT
  de la AMA, contrato SaaS + BAA con abogado, marca USPTO, seguro cyber
  (ver Checklist Legal en Drive).

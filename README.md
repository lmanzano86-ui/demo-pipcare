# Sistema para Clínicas de Accidentes (PIPCare — nombre comercial propuesto)

Plataforma multi-clínica (Python + Django + PostgreSQL) para clínicas de
accidentes / lesiones personales en Florida, con facturación PIP integrada
(CMS-1500, 837P), firma electrónica y motor de cumplimiento FL 627.736.

Cada clínica vive en su propio **schema de PostgreSQL** (django-tenants):
aislamiento total de datos entre clínicas.

## Apps

| App | Contenido |
|---|---|
| `core` | `Clinic` (tenant): plan, NPI, Tax ID, licencia AHCA, director médico, BAA |
| `accounts` | `Profile` (rol: admin / provider / frontdesk / billing), `LoginAudit` inmutable |
| `patients` | `Patient` (contacto de emergencia, alergias, SMS consent, firma guardada), `Accident` (relojes PIP, flags OIR/AOB/5e) |
| `clinical` | `Visit`, `SoapNote`, `OutcomeMeasure` (Oswestry/NDI/dolor), `TreatmentPlan` |
| `billing` | `Claim`, `ClaimLine` (CPT/mod/ICD-10 + advertencias NCCI), `Payment`, `Denial`, `EDITransmission`, `Service` (catálogo) |
| `documents` | `Document`, `Signature` (canvas, IP, invalidación), `DocTemplate` (plantillas legales versionadas) |
| `scheduling` | `Appointment` (bloqueo de solapes), `ReminderLog`, recordatorios SMS (Twilio) |
| `portal` | `PortalToken`: portal del paciente por enlace seguro (citas + firma desde casa) |

Todos los modelos de tenant tienen audit log (`django-simple-history`).

## Módulos principales

- **Admisión digital** (`/intake/`): paciente + accidente, alerta si falta OIR-B1-1571 o AOB.
- **Formularios** (`/documentos/`): 6 e-firmables (canvas) + 3 solo-imprimibles precargados; firma recordada; invalidación con motivo; plantillas versionadas (`/plantillas/`, solo admin).
- **Portal del paciente** (`/portal/<token>/`): citas, documentos y firma sin contraseña; token de 256 bits, 30 días, revocable.
- **Agenda** (`/agenda/`): vista de día, estados, anti-solapes; `send_reminders` (cron) envía SMS de citas de mañana solo con `sms_allowed()`.
- **Facturación**: reclamo desde visita → líneas (manual o desde catálogo) → CMS-1500 PDF → `claim_mark_sent` **bloquea** si el checklist está incompleto → 837P (`build_837p`, comando `transmit_edi` por SFTP) → carta de demanda imprimible.
- **Reportes** (`/reportes/`): facturado/cobrado/pendiente, por aseguradora y proveedor, AR aging, filtro por período.
- **Cumplimiento**: `Accident.pip_alerts()` (14 días, timely filing 35/75 con aviso de inicio), `compliance_checklist()`; dashboard con alertas enlazadas.
- **Roles** (`accounts/roles.py`): `role_required(*roles)`; plantillas=admin; reportes/servicios/837P=admin+billing; líneas=admin+billing+provider; superuser=admin.

## Arranque local ($0)

### Docker (recomendado)

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate_schemas
docker compose exec web python scripts/seed.py
```

Abrir **http://clinica-demo.localhost:8000** (no localhost plano: cae en el
tenant público) y entrar con **admin / admin123**.

> Al descargar un zip nuevo: extraer **conservando tu `.env`**.

### CSRF en Docker

`CSRF_TRUSTED_ORIGINS` se configura por env `DJANGO_CSRF_TRUSTED_ORIGINS`
(default cubre `*.localhost:8000`).

## Variables de entorno clave

| Variable | Uso |
|---|---|
| `DATABASE_URL` | PostgreSQL (socket local o TCP en Docker) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes confiables para login |
| `TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM` | SMS (sin esto: modo demo, se registra sin enviar) |
| `EDI_SUBMITTER_ID/RECEIVER_ID/RECEIVER_NAME/TAXONOMY` | Cabeceras del 837P |
| `EDI_SFTP_HOST/USER` (+ password o `EDI_SFTP_KEY`) | Transmisión automática; sin esto: subida manual |

## Cumplimiento (resumen)

Investigación completa en `research_notes/` (informe de 52 KB). Puntos
aplicados al código: BAA/licencia AHCA/director en `Clinic`; consentimiento
SMS con revocación; relojes PIP 14d/35d/75d; disclosure 5(e) manuscrita;
demanda con título legal exacto; `LoginAudit` inmutable; passwords mín. 10;
sesión de 30 min; AT obligatorio en 98940-42; modificador 59 prohibido en E/M.

**Decisión del negocio (18 oct 2026):** se descartó el plan Todo Incluido
($199+4% de cobros) por riesgo de *fee-splitting* (F.S. 458.331 + doctrina
Bakarania). Planes vigentes: Esencial $249/mes (1 proveedor), Crecimiento
$399/mes (2-3 proveedores), Total $549/mes (4+ proveedores / multi-sede);
setup $1,500 (gratis con plan anual). Planes anuales (2 meses gratis):
Esencial $2,490/año, Crecimiento $3,990/año, Total $5,490/año.
El modelo por % solo se ofrece bajo estructura aprobada, a consulta.

## Licencia CPT

Se requiere licencia de la AMA antes de distribuir (los códigos CPT son
propiedad de la AMA).

## Bitácora de cambios

Ver `BITACORA_CAMBIOS.md`.

## Respaldos, MFA y respuesta a incidentes (HIPAA)

- **Respaldos cifrados:** `BACKUP_ENCRYPTION_KEY='<clave-32+>' python scripts/backup.py`
  (pg_dump completo, AES-256-CBC, manifiesto SHA-256, retención 30 días).
  Restaurar: `scripts/restore.py <archivo.dump.enc>`. RPO ≤24h, RTO ≤4h.
  En producción, programar el respaldo diario con cron (ver cabecera del script).
- **MFA (segundo factor):** TOTP con app de autenticación. Obligatorio para
  administradores (se exige al entrar); opcional para los demás roles en
  `/cuenta/mfa/configurar/`. El secreto se guarda cifrado en la BD.
- **Plan de respuesta a incidentes:** ver `Plan-de-Respuesta-a-Incidentes-v1.0.pdf`
  en Drive (5 fases, niveles SEV, plazos FIPA ≤30 días / HIPAA ≤60 días).
- **Revisión de accesos:** `python manage.py review_access` (trimestral, archivar firmada).
- **Alertas de seguridad:** el dashboard muestra ráfagas de logins fallidos (≥5 en 10 min).
- **SMS:** sin BAA de Twilio firmado (`twilio_baa_signed` por clínica), no se envían SMS reales.
- **Despliegue:** ver `Checklist-Despliegue-Produccion.pdf` en Drive antes del primer PHI.
  en Drive (5 fases, niveles SEV, plazos FIPA ≤30 días / HIPAA ≤60 días).
- **Análisis de riesgos:** `HIPAA-Risk-Assessment-v1.1.pdf` en Drive.

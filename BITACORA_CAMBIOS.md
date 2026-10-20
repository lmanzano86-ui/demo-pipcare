# Bitácora de cambios — Sistema para Clínicas de Accidentes

Historial de lo construido, en orden cronológico. Cada entrada indica qué se
hizo y qué quedó pendiente.

## 19 oct 2026 (noche) — Demo lista para publicar (NO publicada)

- **Verificación completa en local (9/9 OK):** portada pública `/` (200),
  login modal `ajax-login` (ok + redirect), MFA TOTP del admin (código válido
  → 302 a `/inicio/`), dashboard `/inicio/` (200), agenda `/agenda/` (200),
  reclamo demo → CMS-1500 en PDF (200, %PDF válido), sección `/cumplimiento/`
  (200, 6 enlaces a Drive). Migraciones al día; `seed.py` idempotente.
- **Hallazgo documentado:** el admin demo (`admin/admin123`) tiene MFA
  activado → al entrar pide segundo factor (comportamiento esperado, no fallo).
  Se creó el usuario **`demo / demo123`** (rol frontdesk, sin MFA forzado)
  para visitantes de la demo pública.
- **Datos 100% ficticios verificados:** pacientes "María Gómez", "Juan Pérez",
  teléfonos 555, NPI 1234567890, póliza POL-999.
- **4 capturas** en `demo-preview/` (landing, panel, agenda, cumplimiento).
- **Runbook `DEPLOY-DEMO.md`:** pasos exactos para publicar cuando Lester dé
  el «Sí» (opciones $0: Render/Railway/Fly, Docker+Túnel en su PC, o VPS ~$5;
  producción real con PHI solo en AWS con BAA al primer cliente), env vars,
  checklist post-despliegue y reglas de seguridad de la demo.
- **REGLA:** nada publicado, nada desplegado a URL pública, nada subido a
  GitHub/Drive/nube. Falta solo lo que depende de Lester: el «Sí», decisión
  de dónde hospedar, cuenta y dominio.

## 18 oct 2026 (noche) — Portada pública + acceso

- **Landing page** (`/`): portada pública con información del sistema
  (funciones, cómo funciona, beneficios, precios, seguridad, FAQ) y botón
  **Iniciar sesión**. Si el usuario ya entró, `/` lo lleva a su panel.
- **Dashboard movido a `/inicio/`** (mismo nombre de URL `dashboard`; los
  enlaces internos no cambian). `LOGIN_REDIRECT_URL = "/inicio/"`.
- **Login mejorado:** tarjeta de acceso con enlace "Volver a la portada".
- **Login modal:** el botón de la portada abre un cuadro con usuario y
  contraseña sin salir de la página (AJAX a `/accounts/ajax-login/`;
  errores dentro del cuadro; auditoría LoginAudit intacta).

## 18 oct 2026 (noche) — Cambio de modelo de precios (decisión de Lester)

- **Adiós al %:** se eliminó el plan Todo Incluido ($199+4%) por riesgo de
  fee-splitting (F.S. 458.331 + Bakarania). Nuevos tramos fijos:
  Esencial $249/mes (1 proveedor), Crecimiento $399/mes (2-3),
  Total $549/mes (4+/multi-sede); setup $1,500 (gratis con plan anual).
  Planes anuales (18 oct 2026, 2 meses gratis): Esencial $2,490/año,
  Crecimiento $3,990/año, Total $5,490/año — aplicados en portada,
  presentación y Oferta Comercial.
  El modelo por % solo bajo estructura aprobada, a consulta.
- `Clinic.PLAN_CHOICES` actualizado + migración con mapeo de planes viejos.
- Precios actualizados en: portada, presentación (con nota del %),
  Oferta Comercial (Drive) y README.

## 19 oct 2026 — Documentos de cumplimiento dentro del sistema

- Nueva sección **Cumplimiento** (`/cumplimiento/`, solo administradores):
  los 6 documentos de la carpeta "Risk Assessment" de Drive con enlaces
  de vista, más el estado del análisis de riesgos. Enlace en el sidebar
  solo visible para admin; otros roles reciben 403 (verificado).

## 19 oct 2026 — Riesgos MEDIOS mitigados (R-04, R-06–R-09, R-11, R-13, R-14)

- **R-06 Twilio:** campo `twilio_baa_signed` por clínica; `send_due_reminders`
  omite envíos reales sin BAA (migración `core.0004`).
- **R-07 Admin:** ruta configurable con `DJANGO_ADMIN_PATH` + restricción
  por IP en el checklist de despliegue.
- **R-08 Puerto BD:** cerrado por defecto en `docker-compose.yml`.
- **R-09 Accesos:** comando `review_access` (reporte trimestral) + Política
  de Accesos y Sanciones v1.0 (PDF en Drive).
- **R-11 Intentos fallidos:** alerta `SecurityAlert` al 5to fallo en 10 min,
  visible en el dashboard, el admin la marca como revisada (probado).
  Migración `accounts.0004`.
- **R-13 Dependencias:** `pip-audit` ejecutado (0 vulnerabilidades) + proceso
  mensual documentado.
- **R-14 Capacitación:** material de 45 min + plantilla de asistencia (PDF).
- **R-04 parcial:** cifrado en reposo exigido en el Checklist de Despliegue
  a Producción (PDF en Drive); se verifica al migrar a AWS.
- **Risk Assessment v1.2** (PDF actualizado): 0 altos, 1 medio, 14 bajos.

## 19 oct 2026 — Riesgos ALTOS mitigados (R-01, R-02, R-03)

- **R-01 Respaldos:** `scripts/backup.py` (pg_dump completo, cifrado
  AES-256-CBC/PBKDF2, manifiesto SHA-256, retención 30 días, rotación
  probada) + `scripts/restore.py`; ciclo completo probado con verificación
  de integridad; RPO ≤24h / RTO ≤4h. Falta programar el cron en producción.
- **R-02 MFA:** TOTP (`pyotp`, tolerancia ±30s), secreto cifrado con Fernet,
  QR de alta, middleware que exige el 2º factor cada sesión; obligatorio
  para administradores, opcional para el resto. Verificado 4/4 + frontdesk
  no forzado. Migración `accounts.0003`.
- **R-03 Incidentes:** Plan de Respuesta a Incidentes v1.0 (PDF en Drive)
  + simulacro tabletop #1 documentado (ransomware, RTO 3.5h).
- **Risk Assessment v1.1** (PDF actualizado en Drive): 0 altos, 8 medios,
  7 bajos.

## 19 oct 2026 — HIPAA Risk Assessment v1.0

- **Análisis de Riesgos de Seguridad HIPAA** (PDF en Drive): metodología
  HHS/NIST SP 800-30, alcance e inventario de ePHI, 15 riesgos evaluados
  (3 ALTOS, 8 MEDIOS, 4 BAJOS) con plan de remediación en 2 prioridades.
  Hallazgos altos: sin respaldos (R-01), sin MFA (R-02), sin plan de
  respuesta a incidentes (R-03). Los 3 deben resolverse antes del primer
  cliente con PHI real.
- **R-05 corregido en código:** `settings.py` impide arrancar en producción
  con la clave secreta placeholder (verificado: bloquea en prod, normal
  en desarrollo).

## 19 oct 2026 — Términos/Privacidad + checklist legal

- **Portada pública:** páginas `/terminos/` y `/privacidad/` (vistas en
  `config/urls.py`, plantillas propias) enlazadas en el footer de la landing.
- **Checklist Legal de Distribución** (PDF en Drive): fases 1–3 con costos
  estimados verificados (USPTO $350/clase 2026, seguro cyber healthtech,
  CPT AMA, risk assessment) y orden recomendado.

## Documentos del proyecto (todos en PDF)

- Presentación comercial: `Presentacion-PIPCare-Sistema-Clinicas-Accidentes.pdf`
  (diseño del sistema: fondo cálido, barra teal, tarjetas)
- Manual de usuario: `Manual-de-Usuario-Sistema-Clinicas-Accidentes.pdf`
- Oferta Comercial y Plan de Desarrollo (PDF, precios actualizados)
- Modelo de Negocio (PDF) · Guía de Facturación (PDF)
- Informe de Cumplimiento Florida (PDF, 24 págs)
- Código (zip sin `.env`): carpeta "sistema clinicas" en Drive; ubicación
  anotada en `muse-sync-ESTADO.md`.

## 16 oct 2026 — Fundación

- **Decisión de stack y modelo de negocio:** Python + Django + PostgreSQL,
  multi-tenant con un schema por clínica (django-tenants). Planes: Software
  $249/mes + setup $1,500; Todo Incluido $199/mes + 4% de cobros (destacado);
  sin RCM por separado. Despliegue $0 local (Docker); AWS con BAA al primer
  cliente (Hostinger descartado para producción: no firma BAA).
- **Fase 0:** apps `core`, `accounts`, `patients`, `clinical`, `billing`;
  CMS-1500 en PDF; E2E 9/9 OK con clínica demo (`admin / admin123` en
  `http://clinica-demo.localhost:8000`).
- **MVP:** admisión (`/intake/`), visita → SOAP → Oswestry/NDI, reclamo con
  líneas CPT, CMS-1500 en PDF, marcar como enviado, auditoría. E2E 9/9 OK.
- **Investigación legal de cumplimiento (Florida):** informe de 52 KB
  (`research_notes/`): HIPAA/BAA, Health Care Clinic Act, PIP 627.736
  (14 días, EMC, timely filing 35/75, carta de demanda, disclosure 5(e)
  manuscrita), AKS/Stark/FCA, 817.234, fee-splitting (458.331 + Bakarania),
  licencia CPT/AMA, TCPA, No Surprises Act (GFE), FIPA.
- **Hallazgo crítico:** el plan $199+4% tiene riesgo de fee-splitting.
  Propuesta pendiente de decisión: tarifa fija por tramos ($249/$399/$549).

## 18 oct 2026 (mañana) — Rediseño visual + cumplimiento en código

- **Rediseño UI completo:** sidebar teal oscuro, login con tarjeta sobre
  degradado, tarjetas, badges, responsive con hamburguesa.
- **Cumplimiento aplicado al código:** campos BAA/licencia AHCA/director en
  `Clinic`; consentimiento SMS con revocación en `Patient`; motor de relojes
  PIP en `Accident` (14d, 35/75d, alertas); `claim_mark_sent` bloquea envío
  incompleto; advertencias de codificación (AT en 98940-42, 59 prohibido en
  E/M); carta de demanda con título legal exacto; `LoginAudit` inmutable;
  passwords mín. 10; sesión de 30 min; tablero de alertas en el Inicio.
- **Fix CSRF 403 en Docker:** `CSRF_TRUSTED_ORIGINS` configurable por env.

## 18 oct 2026 (mediodía) — Documentos y firma electrónica

- **App `documents`:** 6 formularios e-firmables (canvas): AOB, HIPAA, TCPA,
  consentimiento de tratamiento, OIR-B1-1571, GFE (válidos ESIGN/UETA).
  3 solo-imprimibles precargados: declaración 5(e) (manuscrita obligatoria),
  declaración jurada, aviso de inicio. Firmar actualiza los flags del caso.
- **Firma recordada:** se dibuja una vez, se guarda en la ficha y se aplica
  con un clic en los siguientes documentos (cada uno con su registro
  fecha/hora/IP).
- **Buscador multi-criterio** en Formularios + **tablero de pendientes** en
  el Inicio ("Qué falta por caso").

## 18 oct 2026 (tarde) — Serie 1/4 a 4/4

- **1/4 Agenda de citas + SMS:** vista de día, estados, bloqueo de solapes,
  recordatorios automáticos de citas de mañana solo con consentimiento TCPA
  (Twilio opcional; comando `send_reminders` para cron).
- **2/4 Reportes de dinero:** facturado/cobrado/pendiente, % de cobro, por
  aseguradora y proveedor, AR aging, filtro por período.
- **3/4 Envío electrónico 837P:** generador ASC X12 005010X222A1 validado,
  botón en el reclamo, descarga del .x12, historial de transmisiones, comando
  `transmit_edi` por SFTP (manual sin credenciales). Requiere clearinghouse
  contratado por la clínica (recomendado: Stedi).
- **4/4 Portal del paciente:** enlace seguro por token (sin contraseña, 30
  días, revocable); el paciente ve citas y firma los 6 documentos desde casa.

## 18 oct 2026 (noche) — Ideas de Clinexa

Tras revisar el repo `yoidel86/clinexa` se implementó lo que aporta:
- **Plantillas legales versionadas** (`DocTemplate`): textos en BD, versiones
  inmutables, solo una activa; cada documento guarda su versión; UI solo-admin
  para publicar vN+1. Migración siembra la v1 de los 9 tipos.
- **Invalidación de firmas:** nunca se borran; se invalidan con motivo, el
  documento vuelve a borrador y puede re-firmarse (nuevo registro); los flags
  del caso se recalculan con firmas válidas. `Signature` con historial.
- **Catálogo de servicios** (`Service`): 6 servicios precargados
  (CPT/modificadores/ICD-10/cargo); en el reclamo se agrega la línea en un
  clic. CRUD en `/servicios/`.
- **Roles aplicados** (`accounts/roles.py`): `role_required`; plantillas solo
  admin; reportes/servicios/837P = admin+billing; líneas = admin+billing+
  provider; menú visible según rol; superuser = admin.
- **Paciente:** contacto de emergencia + alergias (insignia en la ficha).
- **Plan de tratamiento** (`TreatmentPlan`): sesiones indicadas vs.
  realizadas, barra de progreso, auto-completado; documenta necesidad médica.

## Documentos del proyecto

- Presentación comercial: `Presentacion-PIPCare-Sistema-Clinicas-Accidentes.pdf`
- Manual de usuario: `Manual-de-Usuario-Sistema-Clinicas-Accidentes.pdf`
- Modelo de negocio, Oferta comercial, Guía de facturación, Informe de
  cumplimiento: carpeta "sistema clinicas" en Drive.
- Código (zip sin `.env`): carpeta "sistema clinicas" en Drive; ubicación
  anotada en `muse-sync-ESTADO.md`.

## Pendientes (decisiones de Lester)

1. ~~Plan Todo Incluido: mantener $199+4% o cambiar a tramos fijos~~ —
   **DECIDIDO 18 oct 2026:** tramos fijos (Esencial $249 / Crecimiento $399 /
   Total $549; setup $1,500, gratis con plan anual). El modelo por % solo
   bajo estructura aprobada, a consulta. Presentación, portada y `Clinic.plan`
   actualizados.
2. Clearinghouse estándar (Stedi propuesto) y si su costo se absorbe o se
   cobra aparte.
3. Nombre comercial definitivo (propuesto: PIPCare).
4. Licencia CPT de la AMA antes de distribuir.

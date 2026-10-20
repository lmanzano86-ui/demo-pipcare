"""Genera un facsímil del formulario CMS-1500 con los datos del reclamo.

No es el formulario oficial de tinta roja del NUCC; es una representación
con los datos mapeados a los casilleros numerados (items 1-33).
"""
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = letter
M = 0.5 * inch


def _box(c, x, y, w, h, label=None, value=""):
    c.rect(x, y, w, h)
    if label:
        c.setFont("Helvetica", 6)
        c.drawString(x + 2, y + h - 8, label)
    if value:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 4, y + 6, str(value)[:60])


def build_cms1500_pdf(claim, tenant) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    patient = claim.visit.accident.patient
    accident = claim.visit.accident
    lines = list(claim.lines.all().order_by("date_of_service"))

    # Diagnósticos únicos -> letras A, B, C...
    diag_codes = []
    for line in lines:
        if line.icd10_code and line.icd10_code not in diag_codes:
            diag_codes.append(line.icd10_code)
    diag_letters = {code: chr(65 + i) for i, code in enumerate(diag_codes[:12])}

    y = PAGE_H - M
    c.setFont("Helvetica-Bold", 12)
    c.drawString(M, y, "HEALTH INSURANCE CLAIM FORM — CMS-1500")
    c.setFont("Helvetica", 7)
    c.drawString(M, y - 11, "Facsímil generado por el sistema (no es el formulario oficial de tinta roja del NUCC)")
    y -= 28

    # Item 1: tipo de seguro
    _box(c, M, y - 20, 3.5 * inch, 20, "1. MEDICARE / MEDICAID / TRICARE / OTHER", "X  OTHER")
    _box(c, M + 3.6 * inch, y - 20, 3.9 * inch, 20, "1a. INSURED'S I.D. NUMBER",
         accident.policy_number or "")
    y -= 26

    # Item 2 y 5: paciente
    _box(c, M, y - 20, 3.5 * inch, 20, "2. PATIENT'S NAME",
         f"{patient.last_name}, {patient.first_name}")
    _box(c, M + 3.6 * inch, y - 20, 3.9 * inch, 20, "5. PATIENT'S ADDRESS",
         patient.address or "")
    y -= 26

    # Item 3 y 11: nacimiento/sexo y póliza
    dob = patient.date_of_birth.strftime("%m/%d/%Y") if patient.date_of_birth else ""
    _box(c, M, y - 20, 2.2 * inch, 20, "3. PATIENT'S BIRTH DATE", dob)
    _box(c, M + 2.3 * inch, y - 20, 2.5 * inch, 20, "11. INSURED'S POLICY GROUP No.",
         accident.policy_number or "")
    _box(c, M + 4.9 * inch, y - 20, 2.6 * inch, 20, "PAYER", claim.payer or "")
    y -= 26

    # Item 14: fecha de la lesión
    inj = accident.date.strftime("%m/%d/%Y") if accident.date else ""
    _box(c, M, y - 20, 3.5 * inch, 20, "14. DATE OF CURRENT ILLNESS/INJURY (Accident)", inj)
    _box(c, M + 3.6 * inch, y - 20, 3.9 * inch, 20, "20. OUTSIDE LAB?", "NO")
    y -= 30

    # Item 21: diagnósticos
    c.setFont("Helvetica", 7)
    c.drawString(M, y, "21. DIAGNOSIS OR NATURE OF ILLNESS OR INJURY")
    y -= 14
    for i, code in enumerate(diag_codes[:12]):
        letter_ = chr(65 + i)
        _box(c, M + i * 0.62 * inch, y - 16, 0.6 * inch, 16, letter_, code)
    y -= 26

    # Item 24: líneas de servicio
    c.setFont("Helvetica", 7)
    c.drawString(M, y, "24. SERVICE LINES")
    y -= 12
    headers = ["A. DATES OF SERVICE", "B. POS", "D. PROCEDURES (CPT/HCPCS)",
               "E. DIAGNOSIS POINTER", "F. $ CHARGES", "G. UNITS"]
    widths = [1.5 * inch, 0.7 * inch, 1.9 * inch, 1.1 * inch, 1.0 * inch, 0.8 * inch]
    x = M
    c.setFont("Helvetica", 6)
    for h, w in zip(headers, widths):
        c.drawString(x + 2, y, h)
        x += w
    y -= 4
    c.setFont("Helvetica", 9)
    for line in lines[:6]:
        x = M
        c.line(M, y, PAGE_W - M, y)
        dos = line.date_of_service.strftime("%m/%d/%Y") if line.date_of_service else ""
        mods = " ".join(m for m in [line.modifier_1, line.modifier_2] if m)
        vals = [dos, "11", f"{line.cpt_code} {mods}".strip(),
                line.diagnosis_pointer, f"{line.charge:.2f}", str(line.units)]
        for v, w in zip(vals, widths):
            c.drawString(x + 2, y - 12, str(v)[:28])
            x += w
        y -= 18
    y -= 10

    # Totales
    total = claim.total
    paid = sum(p.amount for p in claim.payments.all())
    _box(c, M, y - 20, 2.2 * inch, 20, "28. TOTAL CHARGE", f"${total:.2f}")
    _box(c, M + 2.3 * inch, y - 20, 2.2 * inch, 20, "29. AMOUNT PAID", f"${paid:.2f}")
    _box(c, M + 4.6 * inch, y - 20, 2.9 * inch, 20, "30. BALANCE DUE", f"${(total - paid):.2f}")
    y -= 30

    # Item 32 y 33: facility y billing provider
    _box(c, M, y - 20, 3.5 * inch, 20, "32. SERVICE FACILITY LOCATION",
         f"{tenant.name} {tenant.phone or ''}".strip())
    _box(c, M + 3.6 * inch, y - 20, 3.9 * inch, 20, "33. BILLING PROVIDER INFO",
         f"{tenant.name} NPI {tenant.npi or ''}".strip())
    y -= 40

    c.setFont("Helvetica-Oblique", 7)
    c.drawString(M, y, ("I certify the services shown on this form were medically indicated and furnished. "
                       "(Facsímil con fines demostrativos.)"))
    c.showPage()
    c.save()
    return buf.getvalue()

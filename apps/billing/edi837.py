"""Generador ASC X12 837 Professional (005010X222A1) para reclamos PIP.

Produce un archivo X12 estructuralmente válido desde un Claim. El envío real
al clearinghouse requiere las credenciales SFTP de la clínica (ver el comando
`transmit_edi`); sin ellas el archivo queda listo para subirlo manualmente al
portal del clearinghouse.

Configuración (variables de entorno):
  EDI_SUBMITTER_ID  ID del emisor (default: NPI de la clínica)
  EDI_RECEIVER_ID   ID del receptor/clearinghouse (default: 13333 demo)
  EDI_RECEIVER_NAME Nombre del clearinghouse (default: DEMO CLEARINGHOUSE)
  EDI_TAXONOMY      Taxonomía del proveedor (default: 208D00000X quiropráctico)
"""

import os
import re
import unicodedata
from datetime import datetime


def _clean(s, maxlen=None):
    """Mayúsculas, sin acentos, solo caracteres X12 básicos."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    s = "".join(c for c in s.upper() if c.isalnum() or c in " !&'()*+,-./:;?")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen] if maxlen else s


def _split_address(text):
    """Best-effort: 'calle, ciudad, ST ZIP' -> (n3, city, st, zip)."""
    parts = [p.strip() for p in str(text or "").replace("\n", ",").split(",") if p.strip()]
    n3 = _clean(parts[0][:55]) if parts else ""
    city, st, zipc = "", "", ""
    if len(parts) >= 2:
        city = _clean(parts[1][:30])
    if len(parts) >= 3:
        m = re.match(r"([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?", _clean(parts[2]))
        if m:
            st, zipc = m.group(1), m.group(2) or ""
        else:
            st = _clean(parts[2][:2])
    return n3, city, st, zipc


def _money(v):
    return f"{v:.2f}"


def _isa(sender, receiver, ctrl):
    now = datetime.now()
    f = [
        ("00", 2), (" " * 10, 10), ("00", 2), (" " * 10, 10),
        ("ZZ", 2), (_clean(sender, 15), 15), ("ZZ", 2), (_clean(receiver, 15), 15),
        (now.strftime("%y%m%d"), 6), (now.strftime("%H%M"), 4),
        ("^", 1), ("00501", 5), (str(ctrl).zfill(9)[-9:], 9),
        ("0", 1), ("P", 1), (":", 1),
    ]
    seg = "ISA*" + "*".join(v.ljust(w)[:w] for v, w in f) + "~"
    assert len(seg) == 106, f"ISA inválido: {len(seg)} caracteres"
    return seg


def _prov_name(user):
    full = (user.get_full_name() or user.username).strip()
    parts = full.split()
    first = _clean(parts[0], 35) if parts else ""
    last = _clean(" ".join(parts[1:]) or parts[0] if parts else "", 60)
    return last, first


def build_837p(claim, clinic, control_number):
    """Devuelve el contenido X12 del reclamo."""
    now = datetime.now()
    accident = claim.visit.accident
    patient = accident.patient
    provider = claim.visit.provider
    taxonomy = os.environ.get("EDI_TAXONOMY", "208D00000X")
    submitter = os.environ.get("EDI_SUBMITTER_ID", "") or (clinic.npi or "SUBMITTER")
    receiver = os.environ.get("EDI_RECEIVER_ID", "13333")
    receiver_name = os.environ.get("EDI_RECEIVER_NAME", "DEMO CLEARINGHOUSE")
    gs_ctrl = str(control_number)[-9:].zfill(9)
    st_ctrl = str(control_number)[-9:].zfill(9)

    p_last, p_first = _clean(patient.last_name, 60), _clean(patient.first_name, 35)
    dob = patient.date_of_birth.strftime("%Y%m%d") if patient.date_of_birth else ""
    gender = patient.gender or "U"
    p_n3, p_city, p_st, p_zip = _split_address(patient.address)
    c_n3, c_city, c_st, c_zip = _split_address(clinic.address or getattr(clinic, "address", ""))
    clinic_name = _clean(clinic.name, 60)
    clinic_npi = _clean(clinic.npi or "", 15) or "1234567890"
    tax_id = re.sub(r"\D", "", clinic.tax_id or "")
    r_last, r_first = _prov_name(provider)
    try:
        prov_npi = _clean(provider.profile.npi or "", 15)
    except Exception:  # noqa: BLE001
        prov_npi = ""
    prov_npi = prov_npi or clinic_npi
    payer_name = _clean(claim.payer or accident.auto_insurer or "PAYER", 60)
    payer_id = _clean(claim.payer_id or "99999", 30)
    policy = _clean(accident.policy_number or f"PT{patient.pk}", 30)
    total = _money(sum(l.charge for l in claim.lines.all()))

    # Diagnósticos únicos en orden de aparición (sin puntos).
    diags = []
    for line in claim.lines.all().order_by("pk"):
        d = _clean(line.icd10_code).replace(".", "")
        if d and d not in diags:
            diags.append(d)
    hi = ""
    if diags:
        hi = "HI*ABK:" + diags[0]
        for d in diags[1:8]:
            hi += "*ABF:" + d
        hi += "~"

    S = []
    S.append(_isa(submitter, receiver, gs_ctrl))
    S.append(f"GS*HC*{_clean(submitter, 15)}*{_clean(receiver, 15)}*"
             f"{now:%Y%m%d}*{now:%H%M}*{gs_ctrl}*X*005010X222A1~")
    S.append(f"ST*837*{st_ctrl}*005010X222A1~")
    S.append(f"BHT*0019*00*{st_ctrl}*{now:%Y%m%d}*{now:%H%M}*CH~")
    # 1000A/B
    S.append(f"NM1*41*2*{clinic_name}*****46*{_clean(submitter, 15)}~")
    phone = re.sub(r"\D", "", clinic.phone or "")
    if phone:
        S.append(f"PER*IC*{_clean(clinic_name, 30)}*TE*{phone[:15]}~")
    S.append(f"NM1*40*2*{_clean(receiver_name, 60)}*****46*{_clean(receiver, 15)}~")
    # 2000A / 2010AA
    S.append("HL*1**20*1~")
    S.append(f"PRV*BI*PXC*{taxonomy}~")
    S.append(f"NM1*85*2*{clinic_name}*****XX*{clinic_npi}~")
    if c_n3:
        S.append(f"N3*{c_n3}~")
    S.append(f"N4*{c_city}*{c_st}*{c_zip}~")
    if tax_id:
        S.append(f"REF*EI*{tax_id}~")
    # 2000B / 2010BA / 2010BB (suscriptor = paciente en PIP)
    S.append("HL*2*1*22*1~")
    S.append(f"SBR*P*18*{policy}******CI~")
    S.append(f"NM1*IL*1*{p_last}*{p_first}****MI*{policy}~")
    if p_n3:
        S.append(f"N3*{p_n3}~")
    S.append(f"N4*{p_city}*{p_st}*{p_zip}~")
    if dob:
        S.append(f"DMG*D8*{dob}*{gender}~")
    S.append(f"NM1*PR*2*{payer_name}*****PI*{payer_id}~")
    # 2300
    S.append(f"CLM*{claim.pk}*{total}***11:B:1*Y*A*Y*Y~")
    if accident.date:
        S.append(f"DTP*431*D8*{accident.date:%Y%m%d}~")
    if accident.claim_number:
        S.append(f"REF*D9*{_clean(accident.claim_number, 50)}~")
    if hi:
        S.append(hi)
    # 2310B rendering
    S.append(f"NM1*82*1*{r_last}*{r_first}****XX*{prov_npi}~")
    S.append(f"PRV*PE*PXC*{taxonomy}~")
    # 2400 líneas
    for i, line in enumerate(claim.lines.all().order_by("pk"), 1):
        mods = ":".join(m for m in
                        [_clean(line.modifier_1, 2), _clean(line.modifier_2, 2)] if m)
        proc = f"HC:{_clean(line.cpt_code, 10)}" + (f":{mods}" if mods else "")
        S.append(f"LX*{i}~")
        S.append(f"SV1*{proc}*{_money(line.charge)}*UN*{line.units}***1~")
        S.append(f"DTP*472*D8*{line.date_of_service:%Y%m%d}~")
    S.append(f"SE*{len(S) - 1}*{st_ctrl}~")  # ST..SE inclusive
    S.append(f"GE*1*{gs_ctrl}~")
    S.append(f"IEA*1*{gs_ctrl}~")
    return "".join(S)

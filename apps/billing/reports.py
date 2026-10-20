"""Reportes de dinero: facturado vs cobrado vs pendiente.

Todo se calcula desde ClaimLine (fecha de servicio) y Payment (fecha de pago),
así el filtro por período refleja la realidad financiera.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum

from .models import Claim, ClaimLine, Denial, Payment


def _period_bounds(period, start_str, end_str):
    """Devuelve (start, end) como date o (None, None) = todo."""
    if start_str or end_str:
        s = date.fromisoformat(start_str) if start_str else None
        e = date.fromisoformat(end_str) if end_str else None
        return s, e
    today = date.today()
    if period == "month":
        return today.replace(day=1), today
    if period == "quarter":
        m = ((today.month - 1) // 3) * 3 + 1
        return today.replace(month=m, day=1), today
    if period == "year":
        return today.replace(month=1, day=1), today
    return None, None


def money_report(period="all", start_str="", end_str=""):
    start, end = _period_bounds(period, start_str, end_str)

    lines = ClaimLine.objects.select_related(
        "claim", "claim__visit", "claim__visit__provider",
        "claim__visit__accident__patient")
    if start:
        lines = lines.filter(date_of_service__gte=start)
    if end:
        lines = lines.filter(date_of_service__lte=end)
    lines = list(lines)

    payments = Payment.objects.select_related("claim")
    if start:
        payments = payments.filter(date__gte=start)
    if end:
        payments = payments.filter(date__lte=end)
    payments = list(payments)

    billed = sum((l.charge for l in lines), Decimal("0"))
    collected = sum((p.amount for p in payments), Decimal("0"))

    # Por aseguradora (según el pagador del reclamo).
    by_payer = {}
    for l in lines:
        payer = l.claim.payer or "Sin pagador"
        row = by_payer.setdefault(payer, {"billed": Decimal("0"), "claims": set()})
        row["billed"] += l.charge
        row["claims"].add(l.claim_id)
    pay_collected = {}
    for p in payments:
        payer = p.claim.payer or "Sin pagador"
        pay_collected[payer] = pay_collected.get(payer, Decimal("0")) + p.amount
    payer_rows = []
    for payer, row in sorted(by_payer.items(), key=lambda kv: kv[1]["billed"], reverse=True):
        coll = pay_collected.get(payer, Decimal("0"))
        payer_rows.append({
            "payer": payer, "billed": row["billed"], "collected": coll,
            "pending": row["billed"] - coll, "claims": len(row["claims"]),
        })

    # Por proveedor (quien hizo la visita).
    by_provider = {}
    for l in lines:
        prov = l.claim.visit.provider
        name = prov.get_full_name() or prov.username
        row = by_provider.setdefault(name, {"billed": Decimal("0"), "visits": set(), "claims": set()})
        row["billed"] += l.charge
        row["visits"].add(l.claim.visit_id)
        row["claims"].add(l.claim_id)
    provider_rows = [
        {"provider": name, "billed": r["billed"],
         "visits": len(r["visits"]), "claims": len(r["claims"])}
        for name, r in sorted(by_provider.items(), key=lambda kv: kv[1]["billed"], reverse=True)
    ]

    # Denegaciones abiertas (del período o todas si no hay filtro).
    denials = Denial.objects.filter(status="open")
    open_denials = denials.count()

    return {
        "period": period, "start": start, "end": end,
        "billed": billed, "collected": collected,
        "pending": billed - collected,
        "collection_rate": round(collected / billed * 100, 1) if billed else 0,
        "claims_count": len({l.claim_id for l in lines}),
        "payer_rows": payer_rows,
        "provider_rows": provider_rows,
        "open_denials": open_denials,
    }


def ar_aging():
    """Cuentas por cobrar: reclamos con saldo, agrupados por antigüedad."""
    buckets = [("0–30 días", 0, 30), ("31–60 días", 31, 60),
               ("61–90 días", 61, 90), ("90+ días", 91, 10**6)]
    rows = [{"label": label, "count": 0, "amount": Decimal("0")} for label, _, _ in buckets]
    total = Decimal("0")
    today = date.today()
    claims = Claim.objects.prefetch_related("lines", "payments").exclude(status="draft")
    for c in claims:
        bal = sum((l.charge for l in c.lines.all()), Decimal("0")) - \
              sum((p.amount for p in c.payments.all()), Decimal("0"))
        if bal <= Decimal("0.01"):
            continue
        ref = (c.sent_at.date() if c.sent_at else c.created_at.date())
        age = (today - ref).days
        for i, (_, lo, hi) in enumerate(buckets):
            if lo <= age <= hi:
                rows[i]["count"] += 1
                rows[i]["amount"] += bal
                break
        total += bal
    return {"buckets": rows, "total": total}

"""Export stored records without rerunning providers or evaluating spreadsheet formulas."""

import csv
import io
from html import escape

from fastapi import Response


def csv_response(rows, fields, filename):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        safe = {}
        for key in fields:
            value = row.get(key)
            if isinstance(value, str) and value.lstrip().startswith(
                ("=", "+", "-", "@", "\t", "\r")
            ):
                value = "'" + value
            safe[key] = value
        writer.writerow(safe)
    return Response(
        "\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def analysis_pdf(records, ticker):
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    output = io.BytesIO()
    styles = getSampleStyleSheet()
    content = [Paragraph(escape("Riwayat analisis " + ticker), styles["Title"])]
    content.append(
        Paragraph(
            "Confidence adalah skor model, bukan probabilitas keuntungan terkalibrasi. "
            "Ekspor memakai record tersimpan dan tidak menjalankan model kembali.",
            styles["BodyText"],
        )
    )
    for record in records:
        details = record.details or {}
        metadata = details.get("input_metadata", {})
        verified = record.provenance == "real" and record.model_name and record.data_revision
        for label, value in [
            ("Dibuat", record.generated_at),
            ("Tanggal data", record.analysis_date),
            (
                "Provider/model",
                f"{record.provider_name}/{record.actual_model_name or record.model_name}"
                if verified
                else "unknown",
            ),
            ("Sumber data", metadata.get("source")),
            (
                "Currency/bursa",
                f"{metadata.get('currency') or 'unknown'}/{metadata.get('exchange') or 'unknown'}",
            ),
            ("Basis harga", metadata.get("price_adjustment")),
            ("Basis volume", metadata.get("volume_adjustment")),
            ("Revisi data", record.data_revision),
            ("Versi prompt", record.prompt_version),
            ("Provenance", record.provenance),
            ("Sinyal", record.recommendation),
            ("Skor model (bukan peluang profit)", record.confidence_score),
            ("Ringkasan", record.ai_summary),
            ("Faktor pendukung", "; ".join(details.get("supporting_factors", []))),
            ("Faktor penyangkal", "; ".join(details.get("opposing_factors", []))),
            ("Horizon", details.get("horizon")),
            ("Keterbatasan", details.get("limitations")),
        ]:
            content.append(
                Paragraph(
                    escape(
                        str(label) + ": " + str(value if value is not None else "Belum tersedia")
                    ),
                    styles["BodyText"],
                )
            )
        content.append(Spacer(1, 16))
    SimpleDocTemplate(output).build(content)
    return Response(
        output.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="analysis-{ticker}.pdf"'},
    )

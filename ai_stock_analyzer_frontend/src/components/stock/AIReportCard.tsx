import { Analysis } from "@/services/market";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
export function AIReportCard({ analysis }: { analysis: Analysis | null }) {
  const signal = analysis?.ai_recommendation;
  return (
    <Card variant="glass">
      <CardHeader>
        <CardTitle>Analisis Teknikal AI</CardTitle>
      </CardHeader>
      <CardContent>
        {!signal ? (
          <p>Belum ada analisis AI terverifikasi untuk saham ini.</p>
        ) : (
          <div className="space-y-5">
            {!analysis.analysis_matches_data && (
              <p role="status" className="text-amber-300">
                Analisis memakai revisi data sebelumnya. Jalankan ulang untuk
                memperbarui.
              </p>
            )}
            <div className="flex justify-between gap-4">
              <strong
                className={
                  signal === "BUY" ? "text-emerald-400" : "text-amber-300"
                }
              >
                {signal}
              </strong>
              <span>
                Skor model:{" "}
                {analysis.confidence_score == null
                  ? "Belum tersedia"
                  : analysis.confidence_score + "%"}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Skor model belum terkalibrasi sebagai probabilitas keuntungan.
            </p>
            <p className="whitespace-pre-wrap">
              {analysis.ai_summary ||
                analysis.vpa_insight ||
                "Ringkasan belum tersedia."}
            </p>
            <p className="text-sm">
              Horizon: {analysis.horizon || "Belum tersedia"}
            </p>
            {!!analysis.supporting_factors?.length && (
              <div>
                <h4 className="font-semibold">Faktor pendukung</h4>
                <ul className="list-disc pl-5">
                  {analysis.supporting_factors.map((x, i) => (
                    <li key={i}>{x}</li>
                  ))}
                </ul>
              </div>
            )}
            {!!analysis.opposing_factors?.length && (
              <div>
                <h4 className="font-semibold">Faktor penyangkal</h4>
                <ul className="list-disc pl-5">
                  {analysis.opposing_factors.map((x, i) => (
                    <li key={i}>{x}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-sm text-slate-400">
              {analysis.limitations ||
                "Analisis berbasis harga, volume, dan indikator teknikal harian."}
            </p>
            <p className="text-sm text-slate-400">
              Target harga dan tingkat risiko belum tersedia dari metode yang
              terverifikasi.
            </p>
            <p className="text-xs text-slate-400">
              Data analisis: {analysis.analysis_date || "Belum diketahui"}.
              Dibuat:{" "}
              {analysis.generated_at
                ? new Date(analysis.generated_at).toLocaleString("id-ID")
                : "Belum diketahui"}
              .
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

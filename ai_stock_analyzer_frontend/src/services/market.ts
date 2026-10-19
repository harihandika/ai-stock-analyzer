export interface MarketMetadata {
  source: string | null;
  currency: string | null;
  exchange: string | null;
  market_as_of: string | null;
  fetched_at: string | null;
  interval: string;
  price_adjustment?: string;
  data_state: "fresh" | "stale" | "unavailable" | "demo" | "unknown";
  data_revision: string | null;
  volume_adjustment?: string;
  session_timezone?: string | null;
  market_status?: "open" | "closed" | "unknown";
  expected_market_date?: string | null;
  publication_delay_minutes?: number | null;
}
export interface Quote {
  ticker: string;
  company_name: string;
  current_price: number | null;
  change_percent: number | null;
  metadata: MarketMetadata;
}
export interface Stock {
  ticker: string;
  company_name: string;
  currency: string | null;
  exchange: string | null;
  sector: string | null;
}
export interface Analysis {
  analysis_id: string | null;
  company_name: string;
  ai_recommendation: "BUY" | "HOLD" | "WAIT" | null;
  confidence_score: number | null;
  ai_summary: string | null;
  vpa_insight: string | null;
  generated_at: string | null;
  analysis_date: string | null;
  analysis_matches_data: boolean;
  supporting_factors: string[];
  opposing_factors: string[];
  limitations: string | null;
  horizon: string | null;
  metadata: MarketMetadata;
}
export function formatPrice(
  value: number | string | null | undefined,
  currency?: string | null,
) {
  if (value == null || !Number.isFinite(Number(value))) return "Belum tersedia";
  if (!currency)
    return (
      Number(value).toLocaleString("id-ID") + " (mata uang belum terverifikasi)"
    );
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency,
    minimumFractionDigits: currency === "IDR" ? 0 : 2,
    maximumFractionDigits: 4,
  }).format(Number(value));
}

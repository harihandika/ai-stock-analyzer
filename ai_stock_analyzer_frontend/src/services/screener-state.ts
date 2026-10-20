// Only these public criteria may cross the URL/API boundary. Navigation and
// other research tabs keep their own parameters.
export type Criteria = Record<string, string | number | boolean | null>;
const textFields: Record<string, number> = {
  exchange: 50,
  sector: 100,
  wyckoff_phase: 20,
};
const patterns = [
  "bullish_fvg",
  "bearish_fvg",
  "bos",
  "choch",
  "bullish_ob",
  "bearish_ob",
];
const keys = [
  ...Object.keys(textFields),
  "min_volume",
  "rsi_min",
  "rsi_max",
  "smc",
  "sort",
  "descending",
  "missing_only",
];

export function readScreener(params: URLSearchParams) {
  const criteria: Criteria = {};
  const errors: string[] = [];
  for (const key of keys) {
    const raw = params.get("sc_" + key);
    if (raw === null || raw === "") continue;
    criteria[key] = raw;
    if (textFields[key] && raw.length > textFields[key])
      errors.push("Filter teks terlalu panjang.");
    if (["descending", "missing_only"].includes(key)) {
      if (!["true", "false"].includes(raw))
        errors.push("Pilihan filter harus true atau false.");
      else criteria[key] = raw === "true";
    }
    if (["min_volume", "rsi_min", "rsi_max"].includes(key)) {
      const n = Number(raw);
      if (
        !Number.isFinite(n) ||
        n < 0 ||
        (key === "min_volume" ? !Number.isSafeInteger(n) : n > 100)
      )
        errors.push(
          key === "min_volume"
            ? "Volume minimal harus bilangan bulat nonnegatif."
            : "RSI harus antara 0 dan 100.",
        );
      else criteria[key] = n;
    }
    if (key === "sort" && !["ticker", "volume", "rsi"].includes(raw))
      errors.push("Urutan filter tidak dikenal.");
    if (key === "smc" && !patterns.includes(raw))
      errors.push("Pola SMC tidak dikenal.");
  }
  if (
    criteria.rsi_min != null &&
    criteria.rsi_max != null &&
    Number(criteria.rsi_min) > Number(criteria.rsi_max)
  )
    errors.push("RSI minimum tidak boleh melebihi maksimum.");
  const rawPage = params.get("sc_page") || "1";
  const page = Number(rawPage);
  if (!/^\d+$/.test(rawPage) || !Number.isSafeInteger(page) || page < 1)
    errors.push("Halaman harus bilangan bulat positif.");
  return {
    criteria,
    page: Number.isSafeInteger(page) && page > 0 ? page : 1,
    error: [...new Set(errors)].join(" "),
  };
}

export function screenerParams(
  current: URLSearchParams,
  criteria: Criteria,
  page = 1,
) {
  const next = new URLSearchParams(current);
  for (const key of [...next.keys()])
    if (key.startsWith("sc_")) next.delete(key);
  for (const key of keys) {
    const value = criteria[key];
    if (value != null && value !== "") next.set("sc_" + key, String(value));
  }
  next.set("sc_page", String(page));
  return next;
}

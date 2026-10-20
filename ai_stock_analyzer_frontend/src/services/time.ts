// Instants must carry their timezone. Session dates are deliberately not parsed.
export function formatWib(value: string | null | undefined): string {
  if (!value || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value))
    return "Waktu belum terverifikasi";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Waktu belum terverifikasi";
  return (
    new Intl.DateTimeFormat("id-ID", {
      timeZone: "Asia/Jakarta",
      dateStyle: "long",
      timeStyle: "medium",
    }).format(date) + " WIB"
  );
}

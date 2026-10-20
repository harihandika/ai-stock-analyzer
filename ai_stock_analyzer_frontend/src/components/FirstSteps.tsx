"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export function FirstSteps() {
  const { user } = useAuth();
  const [dismissed, setDismissed] = useState<string | null>(null);
  useEffect(() => {
    if (!user) return;
    try {
      if (localStorage.getItem("stock-first-steps:" + user.id) === "dismissed")
        // Read storage after hydration; each account has its own preference.
        requestAnimationFrame(() => setDismissed(user.id));
    } catch {
      /* Storage may be unavailable; instructions remain accessible. */
    }
  }, [user]);
  if (!user) return null;
  const hidden = dismissed === user.id;
  return (
    <section
      aria-label="Langkah pertama"
      className="rounded border border-sky-800 p-4 space-y-3"
    >
      {hidden ? (
        <button
          className="underline min-h-11"
          onClick={() => {
            setDismissed(null);
            try {
              localStorage.removeItem("stock-first-steps:" + user.id);
            } catch {
              /* optional storage */
            }
          }}
        >
          Tampilkan langkah pertama
        </button>
      ) : (
        <>
          <h2 className="text-xl font-semibold">Mulai riset saham</h2>
          <ol className="list-decimal pl-6 space-y-2">
            <li>
              <button
                className="underline min-h-11"
                onClick={() =>
                  document
                    .querySelector<HTMLInputElement>(
                      '[role="combobox"][aria-label="Cari saham"]',
                    )
                    ?.focus()
                }
              >
                Cari kode atau nama saham
              </button>
              , misalnya BBCA.JK atau AAPL.
            </li>
            <li>
              Buka detail dan periksa sumber serta tanggal penutupan. Sinkronkan
              bila data belum tersedia; data harian bukan harga realtime.
            </li>
            <li>
              Simpan saham ke watchlist dan tulis alasan yang ingin dipantau.
            </li>
          </ol>
          <Link className="inline-block underline p-2" href="/guide">
            Baca panduan dan istilah
          </Link>
          <button
            className="border rounded p-3"
            onClick={() => {
              setDismissed(user.id);
              try {
                localStorage.setItem(
                  "stock-first-steps:" + user.id,
                  "dismissed",
                );
              } catch {
                /* optional storage */
              }
            }}
          >
            Tutup langkah pertama
          </button>
        </>
      )}
    </section>
  );
}

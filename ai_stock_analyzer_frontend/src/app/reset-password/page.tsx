"use client";
import { FormEvent, useState } from "react";
import Link from "next/link";
import { apiClient, errorMessage } from "@/services/api";
import { Input } from "@/components/ui/Input";

export default function PasswordResetPage() {
  const [reset, setReset] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const token = new URLSearchParams(window.location.hash.slice(1)).get(
        "token",
      );
      if (reset && !token)
        throw new Error(
          "Buka tautan reset dari email sebelum mengganti password.",
        );
      const response = await apiClient.post(
        reset ? "/auth/password-reset/confirm" : "/auth/password-reset",
        reset
          ? { token, new_password: form.get("password") }
          : { email: form.get("email") },
      );
      setMessage(response.data.message);
      if (reset)
        window.history.replaceState(null, "", window.location.pathname);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="max-w-lg mx-auto my-12 p-6 space-y-6">
      <h1 className="text-3xl">Pemulihan password</h1>
      <p>
        Untuk meminta tautan, isi email. Jika membuka tautan reset dari email,
        pilih Ganti password dari tautan.
      </p>
      <div className="flex flex-wrap gap-3">
        <button
          className="border rounded p-3"
          aria-pressed={!reset}
          onClick={() => {
            setReset(false);
            setError("");
            setMessage("");
          }}
        >
          Minta tautan reset
        </button>
        <button
          className="border rounded p-3"
          aria-pressed={reset}
          onClick={() => {
            setReset(true);
            setError("");
            setMessage("");
          }}
        >
          Ganti password dari tautan
        </button>
      </div>
      <form key={String(reset)} onSubmit={submit} className="space-y-5">
        {reset ? (
          <Input
            name="password"
            label="Password baru"
            type="password"
            minLength={8}
            maxLength={72}
            required
            autoComplete="new-password"
          />
        ) : (
          <Input
            name="email"
            label="Email akun"
            type="email"
            required
            autoComplete="email"
          />
        )}
        <button className="border rounded p-3" disabled={busy}>
          {busy
            ? "Memproses…"
            : reset
              ? "Simpan password baru"
              : "Kirim permintaan reset"}
        </button>
      </form>
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="text-red-300">
          {error}
        </p>
      )}
      <Link href="/login" className="underline p-2 inline-block">
        Kembali ke login
      </Link>
    </main>
  );
}

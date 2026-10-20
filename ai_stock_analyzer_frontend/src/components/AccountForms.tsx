"use client";
import { FormEvent, useState } from "react";
import { apiClient, errorMessage } from "@/services/api";
import { clearSession } from "@/services/session";
import { Input } from "@/components/ui/Input";

export function AccountForms({
  name,
  notificationsEnabled,
  onSaved,
}: {
  name: string;
  notificationsEnabled: boolean;
  onSaved: () => Promise<void>;
}) {
  const [fullName, setFullName] = useState(name);
  const [notifications, setNotifications] = useState(notificationsEnabled);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const save = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiClient.patch("/auth/me", {
        full_name: fullName,
        notifications_enabled: notifications,
      });
      await onSaved();
      setMessage("Profil dan preferensi disimpan.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  const change = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await apiClient.post("/auth/change-password", {
        current_password: f.get("current_password"),
        new_password: f.get("new_password"),
      });
      clearSession();
      window.location.assign("/login");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section id="notification-preferences" className="space-y-6">
      <h2 className="text-xl">Profil dan preferensi</h2>
      <form onSubmit={save} className="space-y-4">
        <Input
          label="Nama lengkap"
          value={fullName}
          minLength={2}
          maxLength={255}
          required
          onChange={(e) => setFullName(e.target.value)}
        />
        <label className="flex gap-3 items-center">
          <input
            type="checkbox"
            checked={notifications}
            onChange={(e) => setNotifications(e.target.checked)}
          />
          Aktifkan evaluasi notifikasi alert in-app
        </label>
        <p className="text-sm">
          Menonaktifkan preferensi menjeda evaluasi seluruh alert. Tidak
          menghapus riwayat atau mengaktifkan email.
        </p>
        <button className="border rounded p-3" disabled={busy}>
          Simpan profil
        </button>
      </form>
      <h2 className="text-xl">Ubah password</h2>
      <p>
        Setelah berhasil, semua sesi dicabut dan Anda diminta masuk kembali.
      </p>
      <form onSubmit={change} className="space-y-4">
        <Input
          name="current_password"
          label="Password saat ini"
          type="password"
          autoComplete="current-password"
          required
          maxLength={72}
        />
        <Input
          name="new_password"
          label="Password baru"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          maxLength={72}
        />
        <button className="border rounded p-3" disabled={busy}>
          Ubah password dan cabut sesi
        </button>
      </form>
      {busy && <p role="status">Memproses…</p>}
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="text-red-300">
          {error}
        </p>
      )}
    </section>
  );
}

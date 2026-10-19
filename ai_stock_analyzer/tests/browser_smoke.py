"""Run against tests.browser_app and the production Next server. Providers are fixtures."""

import os
import re
import secrets
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.getenv("BROWSER_BASE_URL", "http://127.0.0.1:3001")
OUTPUT = Path(os.getenv("BROWSER_OUTPUT_DIR", "/tmp/ai-stock-browser"))
OUTPUT.mkdir(parents=True, exist_ok=True)


def main():
    email = "browser-" + secrets.token_hex(6) + "@example.com"
    password = secrets.token_urlsafe(24)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, executable_path=os.getenv("BROWSER_EXECUTABLE", "/usr/bin/chromium")
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(30000)
        errors, refreshes = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: refreshes.append(request.url)
            if request.url.endswith("/auth/refresh")
            else None,
        )
        page.goto(BASE + "/register", wait_until="domcontentloaded")
        page.get_by_label("Full Name").fill("Browser Tester")
        page.get_by_label("Email Address").fill(email)
        page.get_by_label("Password", exact=True).fill(password)
        page.get_by_role("button", name="Sign Up", exact=True).click()
        page.wait_for_url(re.compile(r".*/login$"))
        page.get_by_label("Email Address").fill(email)
        page.get_by_label("Password", exact=True).fill(password)
        page.get_by_label("Email Address").focus()
        page.keyboard.press("Tab")
        expect(page.get_by_label("Password", exact=True)).to_be_focused()
        page.keyboard.press("Tab")
        expect(page.get_by_role("button", name="Tampilkan password", exact=True)).to_be_focused()
        page.keyboard.press("Space")
        expect(page.get_by_label("Password", exact=True)).to_have_attribute("type", "text")
        page.keyboard.press("Space")
        expect(page.get_by_label("Password", exact=True)).to_have_attribute("type", "password")
        print("PASS keyboard labels, password toggle and tab order")
        page.get_by_role("button", name="Sign In", exact=True).click()
        page.wait_for_url(re.compile(r".*/dashboard$"))
        expect(page.get_by_role("heading", name="Selamat Datang, Browser")).to_be_visible()
        print("PASS register/login JSON and same-origin API")
        page.get_by_role("button", name="Saham berikutnya", exact=True).click()
        expect(page.get_by_text("Halaman 2 / 2", exact=True)).to_be_visible()
        page.get_by_role("button", name="Saham sebelumnya", exact=True).click()
        expect(page.get_by_text("Halaman 1 / 2", exact=True)).to_be_visible()
        print("PASS dashboard pagination reaches the complete registered universe")
        page.get_by_role("combobox", name="Cari saham").fill("Bank Fixture")
        expect(page.get_by_role("option").first).to_be_visible()
        page.get_by_role("combobox", name="Cari saham").press("Enter")
        page.wait_for_url(re.compile(r".*/stock/BBCA.JK$"))
        print("PASS search company name + Enter resolves ticker")
        page.get_by_role("button", name="Analisis Ulang AI", exact=True).click()
        expect(page.get_by_text("Skor model: 88%", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Analisis Ulang AI", exact=True)).to_be_enabled(
            timeout=30000
        )
        expect(page.locator("canvas").first).to_be_visible()
        chart_box = page.locator("canvas").first.bounding_box()
        page.mouse.move(chart_box["x"] + chart_box["width"] / 2, chart_box["y"] + 50)
        page.screenshot(path=str(OUTPUT / "stock-desktop.png"), full_page=True)
        print("PASS sync -> AI -> persisted result, chart and score")
        page.goto(BASE + "/stock/RELOAD.JK", wait_until="domcontentloaded")
        page.get_by_role("button", name="Analisis Ulang AI", exact=True).click()
        expect(page.get_by_text("Job analisis:", exact=False)).to_be_visible()
        page.reload(wait_until="domcontentloaded")
        expect(page.get_by_role("button", name="Analisis Ulang AI", exact=True)).to_be_disabled()
        expect(page.get_by_role("button", name="Analisis Ulang AI", exact=True)).to_be_enabled(
            timeout=30000
        )
        expect(page.get_by_text("Skor model: 88%", exact=True)).to_be_visible()
        page.goto(BASE + "/stock/BBCA.JK", wait_until="domcontentloaded")
        print("PASS job status and completion survive a full page reload")
        page.get_by_role("button", name="Tambah Watchlist", exact=True).click()
        expect(page.get_by_text("Saham ditambahkan ke watchlist.", exact=True)).to_be_visible()
        page.get_by_role("link", name="Backtest teknikal", exact=True).click()
        page.get_by_label("Target Profit (%)", exact=True).fill("10")
        page.get_by_label("Stop Loss (%)", exact=True).fill("5")
        page.get_by_role("button", name="Run Backtest", exact=True).click()
        expect(
            page.get_by_text("Parameter efektif: target 10% · stop 5%.", exact=True)
        ).to_be_visible()
        expect(page.get_by_text("Max Drawdown", exact=True)).to_be_visible()
        expect(page.get_by_text("Trade History", exact=True)).to_be_visible()
        print("PASS backtest effective parameters, statistics and trades render")
        page.get_by_role("link", name="Watchlist", exact=True).click()
        expect(page.get_by_role("link", name="BBCA.JK", exact=True)).to_be_visible()
        page.get_by_label("Catatan pribadi").fill("Pantau volume pada penutupan.")
        page.get_by_role("button", name="Simpan Catatan", exact=True).click()
        expect(page.get_by_role("button", name="Simpan Catatan", exact=True)).to_be_disabled()
        page.reload()
        expect(page.get_by_label("Catatan pribadi")).to_have_value("Pantau volume pada penutupan.")
        print("PASS watchlist notes persist")
        page.goto(BASE + "/research?tab=screener", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Screener saham", exact=True)).to_be_visible()
        page.get_by_role("textbox", name="Bursa", exact=True).fill("IDX")
        page.get_by_role("button", name="Terapkan filter", exact=True).click()
        expect(page.get_by_text("BBCA.JK · Bank Fixture", exact=True)).to_be_visible()
        page.get_by_label("Nama filter tersimpan").fill("Pantauan IDX")
        page.get_by_role("button", name="Simpan filter aktif", exact=True).click()
        expect(page.get_by_role("button", name="Pantauan IDX", exact=True)).to_be_visible()
        page.goto(BASE + "/research?tab=history&ticker=BBCA.JK", wait_until="domcontentloaded")
        expect(
            page.get_by_text("Ringkasan aktual berdasarkan indikator.", exact=True)
        ).to_be_visible()
        with page.expect_download() as download:
            page.get_by_role("button", name="Ekspor CSV", exact=True).click()
        assert download.value.suggested_filename.endswith(".csv")
        print("PASS full-universe screener, saved filter, analysis history and CSV")
        page.goto(BASE + "/research?tab=plans&ticker=BBCA.JK", wait_until="domcontentloaded")
        for name, value in [
            ("Area entry bawah", "990"),
            ("Area entry atas", "1010"),
            ("Harga entry perhitungan", "1000"),
            ("Stop", "950"),
            ("Target", "1100"),
            ("Horizon", "10 sesi"),
            ("Alasan berbasis data", "Pantau volume"),
            ("Kondisi pembatalan", "Close di bawah support"),
        ]:
            page.get_by_label(name, exact=True).fill(value)
        page.get_by_role("button", name="Hitung risiko dan lot", exact=True).click()
        expect(page.get_by_text("2000 lembar / 20 lot", exact=False)).to_be_visible()
        page.get_by_role("button", name="Simpan rencana", exact=True).click()
        expect(page.get_by_role("button", name="Edit rencana", exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_role("button", name="Edit rencana", exact=True)).to_be_visible()
        print("PASS risk/lot calculation and private persisted trade plan")
        page.goto(BASE + "/research?tab=monitoring&ticker=BBCA.JK", wait_until="domcontentloaded")
        page.get_by_label("Ambang harga (currency instrumen)", exact=True).fill("110")
        page.get_by_role("button", name="Simpan alert", exact=True).click()
        expect(page.get_by_role("button", name="Jeda", exact=True)).to_be_visible()
        expect(
            page.get_by_text("Menunggu data lengkap dan kalender terverifikasi", exact=True)
        ).to_be_visible()
        page.get_by_role("button", name="Jeda", exact=True).click()
        expect(page.get_by_role("button", name="Aktifkan", exact=True)).to_be_visible()
        print("PASS EOD alert creation, pause and honest unknown freshness")
        page.goto(BASE + "/settings", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Pengaturan akun", exact=True)).to_be_visible()
        page.get_by_label("Nama lengkap", exact=True).fill("Browser Updated")
        page.get_by_role("button", name="Simpan profil", exact=True).click()
        expect(page.get_by_text("Profil dan preferensi disimpan.", exact=True)).to_be_visible()
        page.goto(BASE + "/guide", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Free dan Premium", exact=True)).to_be_visible()
        page.goto(BASE + "/watchlist", wait_until="domcontentloaded")
        print("PASS profile editing, quota explanation and onboarding glossary")
        expect(page.get_by_role("heading", name="Watchlist Saham", exact=True)).to_be_visible()
        page.wait_for_load_state("networkidle")
        before = len(refreshes)
        context.add_cookies(
            [{"name": "access_token", "value": "expired", "url": BASE, "sameSite": "Strict"}]
        )
        page.reload()
        expect(page.get_by_role("heading", name="Watchlist Saham", exact=True)).to_be_visible()
        expect(page.get_by_label("Catatan pribadi")).to_have_value("Pantau volume pada penutupan.")
        assert len(refreshes) - before == 1, "Concurrent 401 must share one refresh"
        print("PASS concurrent 401 refresh, no request queue hang")
        tokens = {c["name"]: c["value"] for c in context.cookies()}
        page.get_by_role("button", name="Sign Out", exact=True).click()
        page.wait_for_url(re.compile(r".*/login$"))
        assert (
            context.request.post(
                BASE + "/api/v1/auth/refresh", data={"refresh_token": tokens["refresh_token"]}
            ).status
            == 401
        )
        assert (
            context.request.get(
                BASE + "/api/v1/auth/me",
                headers={"Authorization": "Bearer " + tokens["access_token"]},
            ).status
            == 401
        )
        print("PASS logout revokes refresh and access session")
        page.get_by_label("Email Address").fill(email)
        page.get_by_label("Password", exact=True).fill(password)
        page.get_by_role("button", name="Sign In", exact=True).click()
        page.wait_for_url(re.compile(r".*/dashboard$"))
        page.route(
            "**/stocks/BBCA.JK/analysis/latest",
            lambda route: route.fulfill(status=503, json={"detail": "Analysis unavailable"}),
        )
        page.goto(BASE + "/stock/BBCA.JK", wait_until="domcontentloaded")
        expect(
            page.get_by_text("Belum ada analisis AI terverifikasi untuk saham ini.", exact=True)
        ).to_be_visible()
        expect(page.locator("canvas").first).to_be_visible()
        assert "BULLISH" not in page.locator("body").inner_text()
        page.unroute("**/stocks/BBCA.JK/analysis/latest")
        page.goto(BASE + "/stock/FAILAI.JK", wait_until="domcontentloaded")
        page.get_by_role("button", name="Analisis Ulang AI", exact=True).click()
        expect(
            page.get_by_role("alert").filter(has_text="Provider AI melewati batas waktu.").first
        ).to_be_visible(timeout=30000)
        expect(page.get_by_role("button", name="Analisis Ulang AI", exact=True)).to_be_enabled(
            timeout=30000
        )
        print("PASS partial API/provider failures keep genuine chart and expose error")
        page.goto(BASE + "/stock/MISSING.JK", wait_until="domcontentloaded")
        expect(
            page.get_by_text(
                "Data historis belum tersedia. Sinkronkan data untuk memulai.", exact=True
            )
        ).to_be_visible()
        assert page.locator("canvas").count() == 0
        assert "88%" not in page.locator("body").inner_text()
        print("PASS missing data never creates chart or investment signal")
        page.set_viewport_size({"width": 360, "height": 800})
        page.goto(BASE + "/dashboard", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Selamat Datang, Browser")).to_be_visible()
        assert not page.evaluate(
            "document.documentElement.scrollWidth > innerWidth"
        ), "Mobile dashboard overflows"
        page.get_by_role("button", name="Buka navigasi", exact=True).click()
        expect(page.get_by_role("link", name="Watchlist", exact=True)).to_be_visible()
        page.get_by_role("link", name="Watchlist", exact=True).click()
        expect(page.get_by_role("heading", name="Watchlist Saham", exact=True)).to_be_visible()
        assert not page.evaluate(
            "document.documentElement.scrollWidth > innerWidth"
        ), "Mobile watchlist overflows"
        page.screenshot(path=str(OUTPUT / "watchlist-mobile.png"), full_page=True)
        print("PASS mobile 360px navigation and no horizontal page overflow")
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(BASE + "/stock/BBCA.JK", wait_until="domcontentloaded")
        expect(page.get_by_role("button", name="1Y", exact=True)).to_be_visible()
        for label in ("1M", "3M", "6M", "1Y"):
            box = page.get_by_role("button", name=label, exact=True).bounding_box()
            assert box["width"] >= 44 and box["height"] >= 44
        assert not page.evaluate(
            "document.documentElement.scrollWidth > innerWidth"
        ), "390px detail overflows"
        page.screenshot(path=str(OUTPUT / "stock-390x844.png"), full_page=True)
        page.goto(BASE + "/stock/INVALIDXYZ", wait_until="domcontentloaded")
        expect(
            page.get_by_text(
                "Data historis belum tersedia. Sinkronkan data untuk memulai.", exact=True
            )
        ).to_be_visible()
        assert page.locator("canvas").count() == 0
        assert "88%" not in page.locator("body").inner_text()
        print("PASS exact INVALIDXYZ review case, mobile 390x844 and touch targets")
        assert not errors, errors
        context.close()
        missing = browser.new_context()
        missing.add_cookies(
            [{"name": "access_token", "value": "expired", "url": BASE, "sameSite": "Strict"}]
        )
        bad = missing.new_page()
        bad.goto(BASE + "/dashboard", wait_until="domcontentloaded")
        bad.wait_for_url(re.compile(r".*/login$"), timeout=15000)
        print("PASS expired session without refresh returns to login")
        missing.close()
        browser.close()
        print("All browser smoke checks passed; providers were controlled fixtures.")


if __name__ == "__main__":
    main()

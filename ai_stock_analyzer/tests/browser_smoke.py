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
        page.set_default_timeout(15000)
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
        page.get_by_role("button", name="Sign In", exact=True).click()
        page.wait_for_url(re.compile(r".*/dashboard$"))
        expect(page.get_by_role("heading", name="Selamat Datang, Browser")).to_be_visible()
        print("PASS register/login JSON and same-origin API")
        page.get_by_role("combobox", name="Cari saham").fill("Bank Fixture")
        expect(page.get_by_role("option").first).to_be_visible()
        page.get_by_role("combobox", name="Cari saham").press("Enter")
        page.wait_for_url(re.compile(r".*/stock/BBCA.JK$"))
        print("PASS search company name + Enter resolves ticker")
        page.get_by_role("button", name="Analisis Ulang AI", exact=True).click()
        expect(page.get_by_text("Skor model: 88%", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Analisis Ulang AI", exact=True)).to_be_enabled()
        expect(page.locator("canvas").first).to_be_visible()
        chart_box = page.locator("canvas").first.bounding_box()
        page.mouse.move(chart_box["x"] + chart_box["width"] / 2, chart_box["y"] + 50)
        page.screenshot(path=str(OUTPUT / "stock-desktop.png"), full_page=True)
        print("PASS sync -> AI -> persisted result, chart and score")
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
        expect(page.get_by_role("alert").first).to_contain_text("Provider AI melewati batas waktu.")
        expect(page.get_by_role("button", name="Analisis Ulang AI", exact=True)).to_be_enabled()
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

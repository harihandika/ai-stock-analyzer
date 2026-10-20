"""V3 regressions against production Next and the guarded provider-fixture API.

Uses disposable accounts and controlled responses. No device, human, provider,
SMTP or staging acceptance is inferred from these checks.
"""

import json
import os
import re
import secrets
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.getenv("BROWSER_BASE_URL", "http://127.0.0.1:3001")
OUTPUT = Path(os.getenv("BROWSER_OUTPUT_DIR", "/tmp/ai-stock-stabilization-v3"))


def main():
    if os.getenv("BROWSER_SMOKE") != "1":
        raise RuntimeError("Run only against the dedicated tests.browser_app fixture")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks = []

    def passed(name):
        checks.append({"name": name, "status": "passed"})
        (OUTPUT / "results.json").write_text(json.dumps(checks, indent=2))
        print("PASS", name, flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.getenv("BROWSER_EXECUTABLE", "/usr/bin/chromium"), headless=True
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        email, password = "v3-" + secrets.token_hex(6) + "@example.com", secrets.token_urlsafe(24)
        assert (
            context.request.post(
                BASE + "/api/v1/auth/register",
                data={"email": email, "password": password, "full_name": "V3 Tester"},
            ).status
            == 201
        )
        tokens = context.request.post(
            BASE + "/api/v1/auth/token", data={"email": email, "password": password}
        ).json()
        headers = {"Authorization": "Bearer " + tokens["access_token"]}
        context.add_cookies(
            [
                {"name": k, "value": tokens[k], "url": BASE, "sameSite": "Strict"}
                for k in ("access_token", "refresh_token")
            ]
        )
        for ticker in ["BBCA.JK", "AAPL"]:
            assert (
                context.request.post(
                    BASE + "/api/v1/stocks/" + ticker + "/sync", headers=headers
                ).status
                == 200
            )
        runs = []
        for target in [5, 10]:
            response = context.request.post(
                BASE + "/api/v1/analysis/BBCA.JK/backtest",
                headers=headers,
                data={
                    "years": 3,
                    "target_profit_pct": target,
                    "stop_loss_pct": 3,
                    "initial_capital": 10000000,
                    "lot_size": 100,
                },
            )
            assert response.status == 200, response.status
            runs.append(response.json())
        first, second = (r["run_id"] for r in runs)
        assert all(re.search(r"(?:Z|[+]00:00)$", r["created_at"]) for r in runs)
        passed("ST-03 create returns timezone-aware UTC metadata")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "/stock/BBCA.JK/backtest")
        selector = page.get_by_label("Buka run tersimpan tanpa simulasi ulang")
        panel = page.get_by_role("region", name="Hasil backtest aktif")
        selector.select_option(second)
        expect(panel).to_contain_text(second)
        expect(panel).to_contain_text("target 10%")
        expect(panel).to_contain_text("WIB")
        passed("UXV3-01 active result exposes full identity, source and effective parameters")

        held = []

        def hold(route):
            held.append((route, route.fetch()))

        def wait_held():
            for _ in range(60):
                if held:
                    return
                page.wait_for_timeout(50)
            raise AssertionError("Expected held response")

        endpoint = "**/api/v1/backtests/" + first
        page.route(endpoint, hold)
        selector.select_option(first)
        wait_held()
        selector.select_option(second)
        expect(panel).to_contain_text(second)
        held.pop()[0].fulfill(json=runs[0])
        expect(panel).to_contain_text(second)
        expect(selector).to_have_value(second)
        page.unroute(endpoint, hold)
        passed("BUG-008 held A cannot replace selected B")

        page.route(endpoint, hold)
        selector.select_option(first)
        wait_held()
        selector.select_option(second)
        expect(panel).to_contain_text(second)
        held.pop()[0].fulfill(status=500, json={"detail": "Old run failed"})
        expect(panel).to_contain_text(second)
        expect(page.get_by_role("button", name="Coba muat run lagi")).to_have_count(0)
        page.unroute(endpoint, hold)
        passed("ST-01 old error cannot replace active result or retry state")

        page.route(
            "**/api/v1/backtests/" + second,
            lambda r: r.fulfill(status=503, json={"detail": "Controlled failure"}),
        )
        selector.select_option(second)
        expect(panel).to_have_count(0)
        expect(page.get_by_role("button", name="Coba muat run lagi")).to_be_visible()
        page.unroute("**/api/v1/backtests/" + second)
        page.get_by_role("button", name="Coba muat run lagi").click()
        expect(panel).to_contain_text(second)
        passed("ST-01 selected failure clears old data and retries the selected run")

        wrong = {**runs[0], "run_id": second, "ticker": "AAPL"}
        page.route("**/api/v1/backtests/" + second, lambda r: r.fulfill(json=wrong))
        selector.select_option(second)
        expect(page.get_by_role("alert").filter(has_text="Identitas hasil berbeda")).to_be_visible()
        expect(panel).to_have_count(0)
        page.unroute("**/api/v1/backtests/" + second)
        selector.select_option(first)
        expect(panel).to_contain_text(first)
        selector.select_option(second)
        expect(panel).to_contain_text(second)
        selector.select_option(first)
        expect(panel).to_contain_text(first)
        passed("ST-01 mismatched ticker rejected and A-B-A preserves latest identity")

        export = []
        page.on(
            "request",
            lambda r: export.append(r.url)
            if "/backtests/" in r.url and r.url.endswith("/export")
            else None,
        )
        with page.expect_download():
            page.get_by_role("button", name="Ekspor seluruh transaksi CSV").click()
        assert export[-1].endswith(first + "/export")
        passed("ST-01 CSV target follows active run")
        downloaded = []
        page.on("download", lambda d: downloaded.append(d.suggested_filename))
        page.route(endpoint + "/export", hold)
        page.get_by_role("button", name="Ekspor seluruh transaksi CSV").click()
        wait_held()
        with page.expect_event(
            "requestfailed", predicate=lambda r: r.url.endswith(first + "/export")
        ):
            selector.select_option(second)
        expect(panel).to_contain_text(second)
        route, response = held.pop()
        route.fulfill(response=response)
        page.wait_for_timeout(200)
        assert not downloaded
        page.unroute(endpoint + "/export")
        passed("ST-01 switching runs cancels a pending CSV download")

        page.route(endpoint, hold)
        selector.select_option(first)
        wait_held()
        page.goto(BASE + "/research?tab=screener")
        held.pop()[0].fulfill(json=runs[0])
        expect(page.get_by_role("heading", name="Screener saham")).to_be_visible()
        expect(page.get_by_role("region", name="Hasil backtest aktif")).to_have_count(0)
        page.unroute(endpoint, hold)
        passed("ST-01 leaving the page invalidates pending results")

        # The same timestamp must format identically under different client zones.
        display = []
        fixed = {**runs[0], "created_at": "2026-10-20T04:58:39Z"}
        for zone in ["UTC", "Asia/Jakarta", "America/New_York"]:
            ctx = browser.new_context(timezone_id=zone)
            ctx.add_cookies(context.cookies())
            view = ctx.new_page()
            view.route(endpoint, lambda r: r.fulfill(json=fixed))
            view.goto(BASE + "/stock/BBCA.JK/backtest")
            view.get_by_label("Buka run tersimpan tanpa simulasi ulang").select_option(first)
            active = view.get_by_role("region", name="Hasil backtest aktif")
            expect(active).to_contain_text("11.58.39 WIB")
            display.append(active.locator("p").filter(has_text="Dibuat:").inner_text())
            ctx.close()
        assert len(set(display)) == 1
        passed("BUG-010 same instant displays identical WIB in UTC/Jakarta/New York")
        page.goto(BASE + "/stock/BBCA.JK/backtest")
        selector = page.get_by_label("Buka run tersimpan tanpa simulasi ulang")
        for label, timestamp in [
            ("offset", "2026-10-20T11:58:39+07:00"),
            ("naive", "2026-10-20T04:58:39"),
            ("invalid", "invalid"),
            ("missing", None),
            ("rollover", "2026-10-20T20:58:39Z"),
        ]:
            page.route(endpoint, lambda r: r.fulfill(json={**runs[0], "created_at": timestamp}))
            selector.select_option(first)
            expected = (
                "11.58.39 WIB"
                if label == "offset"
                else "03.58.39 WIB"
                if label == "rollover"
                else "Waktu belum terverifikasi"
            )
            expect(page.get_by_role("region", name="Hasil backtest aktif")).to_contain_text(
                expected
            )
            page.unroute(endpoint)
        passed("ST-03 offset/rollover handled; naive/invalid/missing time is not guessed")

        # A new POST may persist even after the UI selects an existing run.
        page.route("**/api/v1/analysis/BBCA.JK/backtest", hold)
        page.get_by_role("button", name="Jalankan backtest", exact=True).click()
        wait_held()
        route, response = held.pop()
        persisted_id = response.json()["run_id"]
        selector.select_option(second)
        expect(page.get_by_role("region", name="Hasil backtest aktif")).to_contain_text(second)
        route.fulfill(response=response)
        expect(page.get_by_role("region", name="Hasil backtest aktif")).to_contain_text(second)
        page.unroute("**/api/v1/analysis/BBCA.JK/backtest")
        stored = context.request.get(BASE + "/api/v1/backtests", headers=headers).json()["data"]
        assert persisted_id in [r["id"] for r in stored]
        passed("ST-01 opening a stored run supersedes POST display without deleting persisted work")
        page.route(
            "**/api/v1/backtests",
            lambda r: r.fulfill(status=503, json={"detail": "History unavailable"}),
        )
        page.get_by_role("button", name="Jalankan backtest", exact=True).click()
        expect(page.get_by_role("region", name="Hasil backtest aktif")).to_be_visible()
        expect(
            page.get_by_role("status").filter(has_text="Riwayat belum dapat diperbarui")
        ).to_be_visible()
        expect(page.get_by_role("button", name="Ekspor seluruh transaksi CSV")).to_be_visible()
        page.unroute("**/api/v1/backtests")
        passed("ST-01 saved result survives independent history refresh failure")

        assert context.request.post(
            BASE + "/api/v1/stocks/watchlist", headers=headers, data={"ticker": "BBCA.JK"}
        ).status in (200, 201)
        rows = context.request.get(BASE + "/api/v1/stocks/watchlist", headers=headers).json()
        bbca_id = next(r["id"] for r in rows if r["stock_ticker"] == "BBCA.JK")
        assert (
            context.request.patch(
                BASE + "/api/v1/stocks/watchlist/BBCA.JK",
                headers=headers,
                data={"notes": "Saved original"},
            ).status
            == 200
        )
        page.goto(BASE + "/watchlist")
        note = page.locator("#notes-" + bbca_id)
        note.fill("Draft BBCA retained")
        page.get_by_role("button", name="Tambah Saham", exact=True).click()
        page.get_by_label("Cari kode atau nama perusahaan").fill("AAPL")
        page.get_by_role("button", name=re.compile(r"^AAPL ·")).click()
        expect(page.get_by_role("dialog")).not_to_be_visible()
        expect(page.get_by_role("link", name="AAPL", exact=True)).to_be_visible()
        expect(note).to_have_value("Draft BBCA retained")
        expect(page.locator('[data-note-status="BBCA.JK"]')).to_have_text("Catatan belum disimpan")
        passed("BUG-009 adding another ticker preserves unsaved BBCA draft")
        note.fill("")
        page.get_by_role("button", name="Muat Ulang", exact=True).click()
        expect(note).to_have_value("")
        expect(page.locator('[data-note-status="BBCA.JK"]')).to_have_text("Catatan belum disimpan")
        passed("ST-02 empty dirty note survives list reload")
        page.route("**/api/v1/stocks/watchlist", hold)
        page.get_by_role("button", name="Muat Ulang", exact=True).click()
        wait_held()
        note.fill("Typed during refresh")
        route, response = held.pop()
        route.fulfill(response=response)
        expect(note).to_have_value("Typed during refresh")
        page.unroute("**/api/v1/stocks/watchlist")
        passed("ST-02 editing while a refresh response is held preserves newest text")
        note.fill("Sent snapshot")
        page.route("**/api/v1/stocks/watchlist/BBCA.JK", hold)
        # AAPL sorts before BBCA; use the note's own card container.
        card = note.locator("xpath=../..")
        card.get_by_role("button", name="Simpan Catatan", exact=True).click()
        wait_held()
        note.fill("Typed while saving")
        route, response = held.pop()
        route.fulfill(response=response)
        expect(note).to_have_value("Typed while saving")
        expect(page.locator('[data-note-status="BBCA.JK"]')).to_have_text("Catatan belum disimpan")
        page.unroute("**/api/v1/stocks/watchlist/BBCA.JK")
        passed("ST-02 late save acknowledges only sent snapshot and keeps newer text dirty")
        page.route(
            "**/api/v1/stocks/watchlist/BBCA.JK",
            lambda r: r.fulfill(status=503, json={"detail": "Save unavailable"}),
        )
        card.get_by_role("button", name="Simpan Catatan", exact=True).click()
        expect(page.get_by_role("alert").filter(has_text="Draft tetap tersedia")).to_be_visible()
        expect(note).to_have_value("Typed while saving")
        page.unroute("**/api/v1/stocks/watchlist/BBCA.JK")
        passed("ST-02 failed save keeps draft and exposes retry")
        page.once("dialog", lambda d: d.dismiss())
        page.get_by_role("link", name="Beranda", exact=True).click()
        expect(note).to_have_value("Typed while saving")
        assert "/watchlist" in page.url
        passed("ST-02 user can cancel navigation and continue editing")
        page.once("dialog", lambda d: d.dismiss())
        page.get_by_role("button", name="Keluar", exact=True).click()
        expect(note).to_have_value("Typed while saving")
        passed("ST-02 cancelling logout keeps the session and draft")
        rows = context.request.get(BASE + "/api/v1/stocks/watchlist", headers=headers).json()
        other_id = next(r["id"] for r in rows if r["stock_ticker"] == "AAPL")
        other_note = page.locator("#notes-" + other_id)
        other_note.fill("Independent AAPL draft")
        card.get_by_role("button", name="Simpan Catatan", exact=True).click()
        expect(page.locator('[data-note-status="BBCA.JK"]')).to_have_text("Catatan tersimpan")
        expect(other_note).to_have_value("Independent AAPL draft")
        expect(page.locator('[data-note-status="AAPL"]')).to_have_text("Catatan belum disimpan")
        page.once("dialog", lambda d: d.dismiss())
        other_note.locator("xpath=../..").get_by_role("button", name="Hapus", exact=True).click()
        expect(other_note).to_have_value("Independent AAPL draft")
        other_note.locator("xpath=../..").get_by_role(
            "button", name="Simpan Catatan", exact=True
        ).click()
        expect(page.locator('[data-note-status="AAPL"]')).to_have_text("Catatan tersimpan")
        passed("ST-02 saving one ticker preserves another draft; dirty removal can be cancelled")
        page.route("**/api/v1/stocks/watchlist", hold)
        page.get_by_role("button", name="Muat Ulang", exact=True).click()
        wait_held()
        note.fill("Saved through refresh")
        card.get_by_role("button", name="Simpan Catatan", exact=True).click()
        expect(page.locator('[data-note-status="BBCA.JK"]')).to_have_text("Catatan tersimpan")
        expect(page.get_by_role("button", name="Muat Ulang", exact=True)).to_be_enabled()
        route, response = held.pop()
        route.fulfill(response=response)
        expect(note).to_have_value("Saved through refresh")
        expect(page.locator('[data-note-status="BBCA.JK"]')).to_have_text("Catatan tersimpan")
        page.unroute("**/api/v1/stocks/watchlist")
        passed("ST-02 save invalidates stale refresh without leaving loading stuck")
        page.get_by_label("Filter bursa").select_option("IDX")
        page.get_by_label("Urutkan", exact=True).select_option("price_desc")
        expect(page).to_have_url(re.compile(r"wl_exchange=IDX.*wl_sort=price_desc"))
        page.get_by_role("link", name="BBCA.JK", exact=True).click()
        page.wait_for_url(re.compile(r".*/stock/BBCA.JK$"))
        page.go_back()
        expect(page.get_by_role("heading", name="Daftar pantauan saham")).to_be_visible()
        expect(page.get_by_label("Filter bursa")).to_have_value("IDX")
        expect(page.get_by_label("Urutkan", exact=True)).to_have_value("price_desc")
        expect(page.get_by_role("link", name="BBCA.JK", exact=True)).to_be_focused()
        page.reload()
        expect(page.get_by_label("Filter bursa")).to_have_value("IDX")
        expect(note).to_have_value("Saved through refresh")
        passed(
            "UXV3-04 URL preserves watchlist filters/sort through Back and refresh; candidate focus restored"
        )
        page.goto(BASE + "/watchlist?wl_sort=invalid&wl_exchange=%3Cscript%3E")
        expect(page.get_by_role("status").filter(has_text="Filter URL tidak valid")).to_be_visible()
        expect(page.get_by_label("Urutkan", exact=True)).to_have_value("name")
        passed("UXV3-04 invalid URL safely falls back to supported criteria")

        page.goto(BASE + "/research?tab=plans&ticker=BBCA.JK")
        expect(page.get_by_role("heading", name="2. Periksa risiko, lot dan biaya")).to_be_visible()
        expect(
            page.get_by_role("status").filter(has_text="Untuk menyimpan, lengkapi:")
        ).to_be_visible()
        passed("UXV3-02 plan shows review step and missing field summary")
        page.goto(BASE + "/research?tab=monitoring&ticker=BBCA.JK")
        page.get_by_label("Ambang harga (currency instrumen)", exact=True).fill("110")
        page.get_by_role("button", name="Simpan alert", exact=True).click()
        expect(page.get_by_role("link", name="Periksa data saham", exact=True)).to_be_visible()
        expect(page.get_by_text("operator perlu memverifikasinya", exact=False)).to_be_visible()
        passed("UXV3-05 waiting-data alert explains user action and operator calendar dependency")
        assert not errors, errors
        passed("No JavaScript errors in V3 regression journeys")
        page.screenshot(path=str(OUTPUT / "monitoring-guidance.png"), full_page=True)
        browser.close()
    print(f"All {len(checks)} stabilization V3 checks passed; isolated fixtures only.", flush=True)


if __name__ == "__main__":
    main()

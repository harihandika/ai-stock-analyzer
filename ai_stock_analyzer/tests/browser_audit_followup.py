"""Regress N05/N04/J10 using the guarded browser database and real API.

History, notification and reset-token setup is explicitly fixture data. These
checks do not prove provider access, SMTP delivery or physical-device support.
"""

import asyncio
import json
import os
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.getenv("BROWSER_BASE_URL", "http://127.0.0.1:3001")
OUTPUT = Path(os.getenv("BROWSER_OUTPUT_DIR", "/tmp/ai-stock-followup"))


async def fixture(user_id, reset_token):
    from app.core.config import settings
    from app.core.security import hash_token
    from app.domain.models.models import AIAnalysis, AlertEvent, PasswordReset, Stock
    from app.infrastructure.database import AsyncSessionLocal, engine
    from app.services.market_metadata import utcnow

    if os.getenv("BROWSER_SMOKE") != "1" or "browser-r1" not in settings.DATABASE_URL:
        raise RuntimeError("A dedicated browser-r1 database and BROWSER_SMOKE=1 are required")
    ids = []
    async with AsyncSessionLocal() as db:
        stock = await db.get(Stock, "BBCA.JK")
        for score in [78, 88]:
            row = AIAnalysis(
                stock_ticker="BBCA.JK",
                analysis_date=date(2025, 7, 1),
                generated_at=utcnow(),
                recommendation="BUY",
                confidence_score=score,
                ai_summary=f"Audit follow-up BBCA {score}",
                provenance="real",
                provider_name="browser-fixture",
                model_name="controlled-model",
                data_revision=stock.data_revision,
            )
            db.add(row)
            await db.flush()
            ids.append(str(row.id))
        db.add(
            AlertEvent(
                user_id=uuid.UUID(user_id),
                event_key="fixture:" + str(uuid.uuid4()),
                ticker="BBCA.JK",
                details={
                    "kind": "price",
                    "value": 110,
                    "market_as_of": "2025-07-01",
                    "href": "/stock/BBCA.JK",
                },
            )
        )
        db.add(
            PasswordReset(
                user_id=uuid.UUID(user_id),
                token_hash=hash_token(reset_token),
                expires_at=utcnow() + timedelta(minutes=30),
                used=False,
            )
        )
        await db.commit()
    await engine.dispose()
    return ids


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks = []

    def passed(name):
        checks.append({"name": name, "status": "passed"})
        (OUTPUT / "audit-followup-results.json").write_text(json.dumps(checks, indent=2))
        print("PASS", name, flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.getenv("BROWSER_EXECUTABLE", "/usr/bin/chromium"), headless=True
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        errors = []
        page.on(
            "pageerror",
            lambda e: (errors.append(str(e)), print("JSERROR", str(e)[:500], flush=True)),
        )
        email, password = (
            "followup-" + secrets.token_hex(6) + "@example.com",
            secrets.token_urlsafe(24),
        )
        assert (
            context.request.post(
                BASE + "/api/v1/auth/register",
                data={"email": email, "password": password, "full_name": "Followup Tester"},
            ).status
            == 201
        )
        tokens = context.request.post(
            BASE + "/api/v1/auth/token", data={"email": email, "password": password}
        ).json()
        headers = {"Authorization": "Bearer " + tokens["access_token"]}
        context.add_cookies(
            [
                {"name": key, "value": tokens[key], "url": BASE, "sameSite": "Strict"}
                for key in ("access_token", "refresh_token")
            ]
        )
        for ticker in ["BBCA.JK", "AAPL"]:
            assert (
                context.request.post(
                    BASE + "/api/v1/stocks/" + ticker + "/sync", headers=headers
                ).status
                == 200
            )
        user = context.request.get(BASE + "/api/v1/auth/me", headers=headers).json()
        reset_token = secrets.token_urlsafe(32)
        # Playwright's synchronous API owns a running loop on this thread.
        with ThreadPoolExecutor(max_workers=1) as setup:
            first, second = setup.submit(asyncio.run, fixture(user["id"], reset_token)).result()
        page.goto(BASE + "/research?tab=history&ticker=BBCA.JK")

        def select_pair():
            for key in [first, second]:
                page.locator("article").filter(has_text=key).get_by_role("checkbox").check()

        select_pair()
        page.get_by_role("button", name="Bandingkan dua hasil", exact=True).click()
        panel = page.get_by_role("region", name="Perbandingan analisis", exact=True)
        expect(panel).to_contain_text("10 poin persentase")
        expect(panel).to_contain_text(first)
        expect(panel).to_contain_text(second)
        expect(panel).to_contain_text("browser-fixture/controlled-model")
        passed("AF-01 normal compare preserves ordered delta and both record identities")

        held = []

        def delay(route):
            held.append((route, route.fetch()))

        page.route("**/analyses/compare?**", delay)
        page.get_by_role("button", name="Bandingkan dua hasil", exact=True).click()
        for _ in range(40):
            if held:
                break
            page.wait_for_timeout(50)
        assert held
        page.get_by_label("Kode saham", exact=True).fill("AAPL")
        page.get_by_role("button", name="Muat riwayat", exact=True).click()
        expect(page.get_by_label("Saham riwayat aktif")).to_have_text("Riwayat aktif: AAPL")
        held[0][0].fulfill(response=held[0][1])
        expect(panel).to_have_count(0)
        expect(page.locator("article").filter(has_text="Audit follow-up BBCA")).to_have_count(0)
        page.unroute("**/analyses/compare?**", delay)
        passed("BUG-005 N05: held BBCA response cannot appear after AAPL is active")

        page.get_by_label("Kode saham", exact=True).fill("BBCA.JK")
        page.get_by_role("button", name="Muat riwayat", exact=True).click()
        select_pair()

        def mismatch(route):
            response = route.fetch()
            data = response.json()
            data["first"]["ticker"] = "AAPL"
            route.fulfill(response=response, json=data)

        page.route("**/analyses/compare?**", mismatch)
        page.get_by_role("button", name="Bandingkan dua hasil", exact=True).click()
        expect(page.locator('p[role="alert"]')).to_contain_text("Identitas hasil tidak sesuai")
        expect(panel).to_have_count(0)
        page.unroute("**/analyses/compare?**", mismatch)
        passed("AF-01 mismatched response identity is rejected without a comparison panel")

        # Reversed selections and a late response must retain the newest snapshot.
        for key in [first, second]:
            page.locator("article").filter(has_text=key).get_by_role("checkbox").uncheck()
        for key in [second, first]:
            page.locator("article").filter(has_text=key).get_by_role("checkbox").check()
        page.get_by_role("button", name="Bandingkan dua hasil", exact=True).click()
        expect(panel).to_contain_text("-10 poin persentase")
        passed("AF-01 reversing selection reverses the score delta")

        held.clear()
        page.route("**/analyses/compare?**", delay)
        page.get_by_role("button", name="Bandingkan dua hasil", exact=True).click()
        for _ in range(40):
            if held:
                break
            page.wait_for_timeout(50)
        assert held
        page.locator("article").filter(has_text=first).get_by_role("checkbox").uncheck()
        held[0][0].fulfill(status=503, json={"detail": "Old comparison failed"})
        expect(panel).to_have_count(0)
        expect(page.locator('p[role="alert"]')).to_have_count(0)
        page.unroute("**/analyses/compare?**", delay)
        passed("AF-01 a late error after selection changes cannot replace current state")

        select_pair()

        def missing_score(route):
            response = route.fetch()
            data = response.json()
            data["first"]["confidence_score"] = None
            data["confidence_change_points"] = None
            route.fulfill(response=response, json=data)

        page.route("**/analyses/compare?**", missing_score)
        page.get_by_role("button", name="Bandingkan dua hasil", exact=True).click()
        expect(panel).to_contain_text("Belum tersedia poin persentase")
        page.unroute("**/analyses/compare?**", missing_score)
        passed("AF-01 a missing score remains unavailable instead of becoming a default")

        held.clear()
        page.route("**/analyses/compare?**", delay)
        page.get_by_role("button", name="Bandingkan dua hasil", exact=True).click()
        for _ in range(40):
            if held:
                break
            page.wait_for_timeout(50)
        assert held
        page.get_by_role("link", name="Screener", exact=True).click()
        expect(page.get_by_role("heading", name="Screener saham", exact=True)).to_be_visible()
        held[0][0].fulfill(response=held[0][1])
        page.unroute("**/analyses/compare?**", delay)
        expect(panel).to_have_count(0)
        passed("AF-01 leaving the history tab invalidates the pending comparison")

        page.goto(BASE + "/research?tab=monitoring&ticker=BBCA.JK")
        page.get_by_label("Jenis alert", exact=True).select_option("signal")
        for signal in ["BUY", "HOLD", "WAIT"]:
            try:
                page.get_by_label("Sinyal", exact=True).select_option(signal, timeout=8000)
            except Exception:
                print(
                    "Alert diagnostic:",
                    page.url,
                    errors,
                    page.locator("select").evaluate_all(
                        "items=>items.map(i=>({id:i.id,name:i.name,value:i.value}))"
                    ),
                    flush=True,
                )
                page.screenshot(path=str(OUTPUT / "alert-failure.png"), full_page=True)
                raise
            with page.expect_response(
                lambda r: r.request.method == "POST" and r.url.endswith("/alerts")
            ) as pending:
                page.get_by_role("button", name="Simpan alert", exact=True).click()
            response = pending.value
            assert response.status == 201
            body = response.request.post_data_json
            assert body["signal"] == signal and "direction" not in body and "threshold" not in body
            expect(page.locator("article").filter(has_text="Sinyal " + signal)).to_have_count(1)
        page.reload()
        expect(page.locator("article").filter(has_text="Sinyal ")).to_have_count(3)
        passed("BUG-006 N04: UI BUY/HOLD/WAIT persist; irrelevant fields are omitted")
        expect(page.get_by_text("Belum tersedia heartbeat aktif", exact=False)).to_have_count(0)
        expect(
            page.get_by_text("Menunggu data lengkap dan kalender terverifikasi", exact=False)
        ).to_have_count(3)
        passed(
            "KP-03/04 monitoring distinguishes real heartbeat from ineligible fixture market data"
        )

        for kind in ["price", "change_pct"]:
            page.get_by_label("Jenis alert", exact=True).select_option(kind)
            threshold = "110" if kind == "price" else "1"
            label = (
                "Ambang harga (currency instrumen)" if kind == "price" else "Ambang perubahan (%)"
            )
            page.get_by_label(label, exact=True).fill(threshold)
            for direction in ["above", "below"]:
                page.get_by_label("Arah", exact=True).select_option(direction)
                with page.expect_response(
                    lambda r: r.request.method == "POST" and r.url.endswith("/alerts")
                ) as pending:
                    page.get_by_role("button", name="Simpan alert", exact=True).click()
                response = pending.value
                assert response.status == 201
                assert response.request.post_data_json["direction"] == direction
                assert "signal" not in response.request.post_data_json
                expect(page.get_by_role("button", name="Simpan alert", exact=True)).to_be_enabled()
        passed("AF-02 price and percent above/below still persist after changing form kinds")
        page.get_by_label("Jenis alert", exact=True).select_option("price")
        page.get_by_label("Ambang harga (currency instrumen)", exact=True).fill("0")
        with page.expect_response(
            lambda r: r.request.method == "POST" and r.url.endswith("/alerts")
        ) as pending:
            page.get_by_role("button", name="Simpan alert", exact=True).click()
        assert pending.value.status == 422
        expect(page.locator('p[role="alert"]')).to_contain_text("Ambang harga/persen tidak valid")
        expect(page.get_by_label("Ambang harga (currency instrumen)", exact=True)).to_have_value(
            "0"
        )
        passed("AF-02 invalid threshold is rejected while the draft remains editable")

        expect(page.get_by_label("1 notifikasi belum dibaca", exact=True)).to_be_visible()

        # A failing jobs read must not prevent a successful mark-read from
        # updating the independent notification response and header count.
        def jobs_down(route):
            route.fulfill(status=503, json={"detail": "Job list temporarily unavailable"})

        page.route("**/analysis/jobs", jobs_down)
        page.get_by_role("button", name="Tandai dibaca", exact=True).click()
        expect(page.get_by_label("1 notifikasi belum dibaca", exact=True)).to_have_count(
            0, timeout=1000
        )
        assert (
            context.request.get(BASE + "/api/v1/notifications", headers=headers).json()["unread"]
            == 0
        )
        passed("UX-01 mark-read updates header and API count without waiting for the poll")
        page.unroute("**/analysis/jobs", jobs_down)

        page.goto(BASE + "/research?tab=screener&ticker=BBCA.JK")
        page.get_by_label("Bursa", exact=True).fill("IDX")
        page.get_by_label("Volume minimal (lembar)", exact=True).fill("1000")
        page.get_by_label("RSI minimum", exact=True).fill("20")
        page.get_by_label("RSI maksimum", exact=True).fill("60")
        page.get_by_role("button", name="Terapkan filter", exact=True).click()
        expect(page).to_have_url(__import__("re").compile(r".*sc_exchange=IDX.*"))
        bbca = page.locator("#screener-BBCA\\.JK").get_by_role("link")
        expect(bbca).to_be_visible()
        bbca.click()
        page.wait_for_url("**/stock/BBCA.JK")
        page.go_back()
        expect(page.get_by_label("Bursa", exact=True)).to_have_value("IDX")
        expect(page.get_by_label("Volume minimal (lembar)", exact=True)).to_have_value("1000")
        expect(page.get_by_label("RSI minimum", exact=True)).to_have_value("20")
        expect(page.get_by_label("RSI maksimum", exact=True)).to_have_value("60")
        expect(bbca).to_be_focused()
        passed("BUG-007 J10: Back restores applied unsaved criteria and candidate focus")
        page.go_forward()
        page.wait_for_url("**/stock/BBCA.JK")
        page.go_back()
        expect(page.get_by_role("heading", name="Screener saham", exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_label("RSI maksimum", exact=True)).to_have_value("60")
        passed("AF-03 Forward and refresh preserve the same screener criteria")
        for width in [320, 360, 390, 430, 768, 1440]:
            page.set_viewport_size({"width": width, "height": 1000})
            bbca.click()
            page.wait_for_url("**/stock/BBCA.JK")
            page.go_back()
            expect(page.get_by_label("RSI maksimum", exact=True)).to_have_value("60")
            expect(bbca).to_be_focused()
            passed(f"AF-03 candidate focus and filter return at {width}px")

        page.get_by_role("button", name="Reset filter", exact=True).click()
        expect(page.get_by_label("Bursa", exact=True)).to_have_value("")
        expect(page.get_by_label("RSI maksimum", exact=True)).to_have_value("")
        page.get_by_label("Urutkan", exact=True).select_option("ticker")
        # The guarded server registers eight unsynced BROWSE tickers. They are
        # eligible for the missing-data view, giving a real second API page.
        page.get_by_label("Hanya data belum lengkap", exact=True).check()
        page.get_by_role("button", name="Terapkan filter", exact=True).click()
        page.get_by_role("button", name="Berikutnya", exact=True).click()
        expect(page).to_have_url(__import__("re").compile(r".*sc_page=2.*"))
        page.reload()
        expect(page.get_by_text("Halaman 2 / 2", exact=True)).to_be_visible()
        page.get_by_role("link", name="Riwayat AI", exact=True).click()
        page.get_by_role("link", name="Screener", exact=True).click()
        expect(page.get_by_text("Halaman 2 / 2", exact=True)).to_be_visible()
        passed("AF-03 pagination and tab round trip preserve namespaced URL state")
        page.goto(BASE + "/research?tab=screener&sc_page=-1&sc_descending=false")
        expect(page.locator('p[role="alert"]')).to_contain_text(
            "Halaman harus bilangan bulat positif"
        )
        expect(page.get_by_label("Menurun", exact=True)).not_to_be_checked()
        page.get_by_role("button", name="Reset filter", exact=True).click()
        expect(page.locator('p[role="alert"]')).to_have_count(0)
        passed("AF-03 invalid URL page is actionable and false remains false")

        page.goto(BASE + "/dashboard")
        page.get_by_role("button", name="Tutup langkah pertama", exact=True).click()
        page.reload()
        expect(
            page.get_by_role("button", name="Tampilkan langkah pertama", exact=True)
        ).to_be_visible()
        page.get_by_role("button", name="Tampilkan langkah pertama", exact=True).click()
        page.get_by_role("button", name="Cari kode atau nama saham", exact=True).click()
        expect(page.get_by_role("combobox", name="Cari saham", exact=True)).to_be_focused()
        passed("UX-03 first steps can be dismissed, reopened and focus the real search")

        page.goto(BASE + "/stock/BBCA.JK")
        page.get_by_text("Memahami indikator dan pola", exact=True).click()
        expect(page.get_by_text("Indikator sesi", exact=False)).to_be_visible()
        page.get_by_role("button", name="Lihat candle sesi indikator", exact=True).click()
        latest = context.request.get(
            BASE + "/api/v1/stocks/BBCA.JK/analysis/latest", headers=headers
        ).json()
        expect(page.get_by_test_id("candle-date")).to_have_text(
            latest["technical_indicators"]["trading_date"]
        )
        passed("UX-04 indicator evidence selects its actual candle date")

        page.goto(BASE + "/reset-password#token=" + reset_token)
        expect(page.get_by_label("Password baru", exact=True)).to_be_visible()
        new_password = secrets.token_urlsafe(24)
        page.get_by_label("Password baru", exact=True).fill(new_password)
        page.get_by_role("button", name="Simpan password baru", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("Password diperbarui")
        assert "#" not in page.url
        assert context.request.get(BASE + "/api/v1/auth/me", headers=headers).status == 401
        assert (
            context.request.post(
                BASE + "/api/v1/auth/token", data={"email": email, "password": new_password}
            ).status
            == 200
        )
        passed(
            "KP-05 valid fixture reset link opens password mode, clears fragment and revokes old access"
        )
        assert not errors, errors
        context.close()
        browser.close()
        print(
            f"All {len(checks)} follow-up checks passed; providers and reset token were fixtures."
        )


if __name__ == "__main__":
    main()

"""Regression of the four d17f260 audit bugs against isolated browser providers."""

import json
import os
import secrets
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.getenv("BROWSER_BASE_URL", "http://127.0.0.1:3001")
OUTPUT = Path(os.getenv("BROWSER_OUTPUT_DIR", "/tmp/ai-stock-post-audit"))


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.getenv("BROWSER_EXECUTABLE", "/usr/bin/chromium"), headless=True
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        email, password = (
            "audit-" + secrets.token_hex(6) + "@example.com",
            secrets.token_urlsafe(24),
        )
        assert (
            context.request.post(
                BASE + "/api/v1/auth/register",
                data={"email": email, "password": password, "full_name": "Audit Regression"},
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
        for ticker in ("BBCA.JK", "AAPL"):
            assert (
                context.request.post(
                    BASE + "/api/v1/stocks/" + ticker + "/sync", headers=headers
                ).status
                == 200
            )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def passed(name, **detail):
            checks.append({"name": name, "status": "passed", **detail})
            print("PASS", name, flush=True)
            (OUTPUT / "post-audit-results.json").write_text(json.dumps(checks, indent=2))

        page.goto(BASE + "/research?tab=plans&ticker=BBCA.JK")
        for name, value in [
            ("Harga entry perhitungan", "1000"),
            ("Stop", "950"),
            ("Target", "1100"),
        ]:
            page.get_by_label(name, exact=True).fill(value)
        result = page.get_by_role("status", name="Hasil kalkulator terkini", exact=True)
        expect(page.get_by_label("Alasan berbasis data", exact=True)).not_to_be_visible()
        page.get_by_role("button", name="Hitung risiko dan lot", exact=True).click()
        expect(result).to_contain_text("2000 lembar / 20 lot")
        page.get_by_label("Modal", exact=True).fill("1000000")
        expect(result).to_have_count(0)
        expect(page.get_by_text("Input berubah — hitung ulang.", exact=True)).to_be_visible()
        page.get_by_role("button", name="Hitung risiko dan lot", exact=True).click()
        expect(result).to_contain_text("200 lembar / 2 lot")
        passed("BUG-001: changed capital invalidates 20 lots; minimal calculation returns 2 lots")

        # Hold the real API response. Inputs can change before it reaches React.
        held = []

        def delay(route):
            held.append((route, route.fetch()))

        page.route("**/trade-plans/calculate", delay)
        page.get_by_role("button", name="Hitung risiko dan lot", exact=True).click()
        for _ in range(50):
            if held:
                break
            page.wait_for_timeout(100)
        assert held, "Calculation response was not captured"
        page.get_by_label("Modal", exact=True).fill("700000")
        held[0][0].fulfill(response=held[0][1])
        expect(page.get_by_role("button", name="Hitung risiko dan lot", exact=True)).to_be_enabled()
        expect(result).to_have_count(0)
        page.unroute("**/trade-plans/calculate", delay)
        passed("BUG-001: late response cannot reactivate a result for older inputs")

        page.get_by_label("Modal", exact=True).fill("1000000")
        page.get_by_role("button", name="Simpan rencana", exact=True).click()
        expect(page.get_by_label("Area entry bawah", exact=True)).to_be_focused()
        expect(
            page.get_by_role("alert").filter(has_text="Lengkapi area entry bawah")
        ).to_be_visible()
        for name, value in [
            ("Area entry bawah", "990"),
            ("Area entry atas", "1010"),
            ("Horizon", "10 sesi"),
            ("Alasan berbasis data", "Pantau volume"),
            ("Kondisi pembatalan", "Close di bawah support"),
        ]:
            page.get_by_label(name, exact=True).fill(value)
        page.get_by_role("button", name="Simpan rencana", exact=True).click()
        expect(result).to_contain_text("200 lembar / 2 lot")
        expect(page.locator("article")).to_contain_text("200 lembar / 2 lot")
        page.reload()
        expect(page.locator("article")).to_contain_text("200 lembar / 2 lot")
        passed(
            "PA-06: save validates full plan and persists the server calculation without a prior preview"
        )

        page.get_by_role("button", name="Edit rencana", exact=True).click()
        page.get_by_role("button", name="Hitung risiko dan lot", exact=True).click()
        expect(result).to_be_visible()
        for label, changed, original in [
            ("Harga entry perhitungan", "1001", "1000"),
            ("Stop", "940", "950"),
            ("Target", "1200", "1100"),
            ("Batas risiko modal (%)", "2", "1"),
        ]:
            page.get_by_label(label, exact=True).fill(changed)
            expect(result).to_have_count(0)
            page.get_by_label(label, exact=True).fill(original)
            page.get_by_role("button", name="Hitung risiko dan lot", exact=True).click()
            expect(result).to_be_visible()
        page.get_by_text("Biaya dan slippage", exact=True).click()
        for label in ("Fee beli (bps)", "Fee jual (bps)", "Slippage (bps)"):
            page.get_by_label(label, exact=True).fill("10")
            expect(result).to_have_count(0)
            page.get_by_label(label, exact=True).fill("0")
            page.get_by_role("button", name="Hitung risiko dan lot", exact=True).click()
            expect(result).to_be_visible()
        page.get_by_role("button", name="Batal edit", exact=True).click()
        expect(result).to_have_count(0)
        passed(
            "BUG-001: entry/stop/target/risk/fees/slippage and cancel cannot retain the old preview"
        )

        # Concurrent edit through the API must remain a visible optimistic conflict.
        page.get_by_role("button", name="Edit rencana", exact=True).click()
        stored = context.request.get(BASE + "/api/v1/trade-plans", headers=headers).json()["data"][
            0
        ]
        assert (
            context.request.put(
                BASE + "/api/v1/trade-plans/" + stored["id"],
                headers=headers,
                data={
                    **stored["details"]["input"],
                    "expected_version": stored["version"],
                    "target": 1200,
                },
            ).status
            == 200
        )
        page.get_by_role("button", name="Simpan versi baru", exact=True).click()
        page.get_by_role("button", name="Muat ulang versi tersimpan", exact=True).click()
        expect(page.get_by_label("Target", exact=True)).to_have_value("1200")
        passed("PA-01: conflicting saved version has an explicit reload path")

        routes = [
            "/dashboard",
            "/watchlist",
            "/stock/BBCA.JK",
            "/stock/BBCA.JK/backtest",
            "/research?tab=screener",
            "/research?tab=history",
            "/research?tab=monitoring",
            "/research?tab=plans",
            "/settings",
            "/guide",
        ]
        for width in (320, 360, 390, 430, 768, 1440):
            page.set_viewport_size({"width": width, "height": 844})
            for path in routes:
                page.goto(BASE + path, wait_until="domcontentloaded")
                expect(page.get_by_role("button", name="Menu akun", exact=True)).to_be_visible()
                boxes = []
                for label in ("Menu akun", "Notifikasi", "Buka navigasi"):
                    control = page.get_by_role("button", name=label, exact=True)
                    if control.is_visible():
                        box = control.bounding_box()
                        assert (
                            box and box["x"] >= -0.5 and box["x"] + box["width"] <= width + 0.5
                        ), (path, width, label, box)
                        assert box["width"] >= 44 and box["height"] >= 44, (label, box)
                        boxes.append({"label": label, **box})
                search = page.get_by_role("combobox", name="Cari saham", exact=True).bounding_box()
                assert search and search["x"] >= 0 and search["x"] + search["width"] <= width + 0.5
                passed("BUG-002 header " + str(width) + " " + path, boxes=boxes)
            if width in (320, 390):
                page.screenshot(path=str(OUTPUT / f"header-{width}.png"))

        page.goto(BASE + "/research?tab=plans")
        padding = page.get_by_label("Harga entry perhitungan", exact=True).evaluate(
            "el => [getComputedStyle(el).paddingLeft, getComputedStyle(el).paddingTop]"
        )
        assert padding == ["12px", "12px"], padding
        tab = page.get_by_role("link", name="Rencana transaksi", exact=True)
        assert tab.evaluate("el => getComputedStyle(el).paddingLeft") == "16px"
        assert tab.bounding_box()["height"] >= 44
        passed("BUG-003 computed padding and tab touch area match production utilities")

        page.set_viewport_size({"width": 320, "height": 844})
        page.get_by_role("button", name="Menu akun", exact=True).click()
        profile = page.get_by_role("link", name="Profil", exact=True)
        expect(profile).to_be_visible()
        box = profile.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 320
        profile.focus()
        page.keyboard.press("Escape")
        expect(profile).not_to_be_visible()
        expect(page.get_by_role("button", name="Menu akun", exact=True)).to_be_focused()
        passed("PA-02 dropdown stays within 320px and Escape returns focus")

        page.set_viewport_size({"width": 844, "height": 390})
        page.goto(BASE + "/research?tab=plans")
        for label in ("Menu akun", "Notifikasi"):
            box = page.get_by_role("button", name=label, exact=True).bounding_box()
            assert box and box["x"] >= 0 and box["x"] + box["width"] <= 844
        passed("PA-02 landscape 844x390 keeps header controls reachable")
        page.set_viewport_size({"width": 320, "height": 844})
        page.evaluate("document.documentElement.style.fontSize = '200%'")
        for control in page.locator("form input, form select, form button").all():
            if control.is_visible():
                box = control.bounding_box()
                assert box and box["x"] >= -0.5 and box["x"] + box["width"] <= 320.5, box
        page.screenshot(path=str(OUTPUT / "plans-320-text-200.png"), full_page=True)
        page.evaluate("document.documentElement.style.fontSize = ''")
        passed("PA-02 form controls remain within 320px with 200 percent root text")

        mobile = browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        mobile.add_cookies(context.cookies())
        touch = mobile.new_page()
        touch.on("pageerror", lambda error: errors.append(str(error)))
        touch.goto(BASE + "/stock/BBCA.JK")
        panel = touch.get_by_role("region", name="Nilai candle dan indikator", exact=True)
        expect(panel).to_be_visible()
        assert touch.evaluate("matchMedia('(hover: none)').matches")
        assert panel.evaluate("el => getComputedStyle(el).opacity") == "1"
        latest = touch.get_by_test_id("candle-date").inner_text()
        canvas = touch.locator("canvas").first
        canvas.scroll_into_view_if_needed()
        box = canvas.bounding_box()
        session = mobile.new_cdp_session(touch)
        session.send(
            "Input.dispatchTouchEvent",
            {
                "type": "touchStart",
                "touchPoints": [{"x": box["x"] + box["width"] * 0.4, "y": box["y"] + 100}],
            },
        )
        touch.wait_for_timeout(900)
        selected = touch.get_by_test_id("candle-date").inner_text()
        session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        assert selected != latest, (selected, latest)
        expect(touch.get_by_test_id("candle-date")).to_have_text(selected)
        expect(panel).to_be_visible()
        rows = mobile.request.get(
            BASE + "/api/v1/stocks/BBCA.JK/chart?per_page=1825", headers=headers
        ).json()["data"]
        candle = next(row for row in rows if row["trading_date"] == selected)
        expected_close = touch.evaluate(
            "v => new Intl.NumberFormat('id-ID', {style:'currency',currency:'IDR',minimumFractionDigits:0,maximumFractionDigits:4}).format(v)",
            float(candle["close"]),
        )
        assert panel.locator('[data-value="Close"]').inner_text() == expected_close
        panel.screenshot(path=str(OUTPUT / "touch-candle-values.png"))
        passed(
            "BUG-004 long press without hover reveals actual candle date and OHLC", candle=selected
        )

        slider = touch.get_by_role("slider", name="Pilih candle", exact=True)
        index = int(slider.input_value())
        slider.focus()
        touch.keyboard.press("ArrowLeft")
        expect(slider).to_have_value(str(max(0, index - 1)))
        touch.get_by_role("button", name="Candle terbaru", exact=True).click()
        expect(touch.get_by_test_id("candle-date")).to_have_text(latest)
        passed("PA-04 candle selector supports keyboard and explicit latest reset")

        # Inject freshness metadata only: the badge must follow market state, not fetch time.
        def stale(route):
            response = route.fetch()
            body = response.json()
            body["metadata"].update(data_state="stale", fetched_at="2026-10-19T10:00:00Z")
            route.fulfill(response=response, json=body)

        touch.route("**/stocks/BBCA.JK/price", stale)
        touch.reload()
        status = touch.get_by_test_id("market-data-status")
        expect(status.get_by_text("Data lama", exact=True)).to_be_visible()
        status.get_by_text("Rincian sumber dan waktu", exact=True).click()
        expect(status).to_contain_text(
            "WIB. Waktu pengambilan tidak mengubah tanggal penutupan harga."
        )
        expect(status).to_contain_text("IDR")
        passed("PA-05 recent fetch does not make a stale market session fresh")
        assert not errors, errors
        mobile.close()
        context.close()
        browser.close()
        print(f"All {len(checks)} post-audit checks passed; providers were isolated fixtures.")


if __name__ == "__main__":
    main()

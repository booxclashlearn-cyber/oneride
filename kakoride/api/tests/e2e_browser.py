"""Explicit browser rehearsal (not collected by pytest).

Requires Playwright and installed Chrome. Launches an isolated API/database,
uses the actual Vite UI at 5173 and never contacts a messaging provider.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import uuid


def main():
    from playwright.sync_api import sync_playwright, expect
    root = Path(__file__).resolve().parents[3]
    artifacts = root / ".browser-artifacts"
    artifacts.mkdir(exist_ok=True)
    env = {**os.environ, "KAKORIDE_ENVIRONMENT": "development", "KAKORIDE_STORAGE": "sqlite", "KAKORIDE_LOCAL_DATABASE": str(artifacts / ("test-" + uuid.uuid4().hex + ".sqlite"))}
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "kakoride.api.app:app", "--host", "127.0.0.1", "--port", "8091"], cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8091/healthz", timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(.25)
        else:
            raise RuntimeError("Isolated browser API did not start")
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
            context = browser.new_context(viewport={"width": 1480, "height": 1000})
            def proxy(route):
                url = route.request.url
                if "/api/" in url or "/dev/" in url:
                    from urllib.parse import urlsplit
                    parsed = urlsplit(url)
                    response = route.fetch(url="http://127.0.0.1:8091" + parsed.path + ("?" + parsed.query if parsed.query else ""))
                    route.fulfill(response=response)
                else:
                    route.continue_()
            context.route("**/*", proxy)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto("http://127.0.0.1:5173", wait_until="networkidle")
            page.get_by_role("button", name="Open demo dashboard").click()
            expect(page.get_by_role("heading", name="See the demand ahead.")).to_be_visible()
            page.get_by_role("button", name=re.compile("Try the messaging flow")).click()
            page.get_by_role("button", name="SMS", exact=True).click()
            page.get_by_role("button", name="RIDE KAMWALA TOWN 20", exact=True).click()
            total = page.locator(".metrics article").nth(0).locator("strong")
            expect(total).to_have_text("1")
            page.get_by_role("button", name="WhatsApp", exact=True).click()
            page.get_by_role("button", name="RIDE KAMWALA TOWN 20", exact=True).click()
            expect(total).to_have_text("1")
            page.get_by_label("Synthetic sender").select_option("+260970000102")
            page.get_by_role("button", name="RIDE CHILENJE TOWN 25 2", exact=True).click()
            expect(total).to_have_text("3")
            expect(page.locator(".metrics article").nth(2).locator("strong")).to_have_text("K70")
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(artifacts / "driver-desktop.png"), full_page=True)
            page.get_by_role("button", name="+5 min · send reminder", exact=True).click()
            page.get_by_role("button", name="Yes, boarded", exact=True).last.click()
            expect(total).to_have_text("1")
            page.get_by_label("Synthetic sender").select_option("+260970000101")
            page.get_by_role("button", name="SMS", exact=True).click()
            page.get_by_role("button", name="Still waiting", exact=True).last.click()
            expect(page.get_by_text("Still waiting confirmed.", exact=False)).to_be_visible()
            page.get_by_role("button", name="+5 min · test expiry", exact=True).click()
            expect(total).to_have_text("1")
            page.get_by_role("button", name="+5 min · test expiry", exact=True).click()
            expect(total).to_have_text("0")
            page.set_viewport_size({"width": 390, "height": 844})
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(artifacts / "driver-mobile.png"), full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile page overflows horizontally"
            page.get_by_role("button", name="Sign out").last.click()
            page.get_by_role("button", name="Test an account without a subscription").click()
            expect(page.get_by_role("heading", name="Your route access starts here.")).to_be_visible()
            assert not errors, errors
            browser.close()
        print(json.dumps({"result": "PASS", "checks": ["SMS intake", "cross-channel duplicate", "aggregates", "five-minute prompt", "WhatsApp boarding", "SMS renewal", "expiry", "390px no overflow", "subscription gate", "no browser errors"], "artifacts": str(artifacts)}))
    finally:
        server.terminate()
        server.wait(timeout=10)


if __name__ == "__main__":
    main()

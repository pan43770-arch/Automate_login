import asyncio
import subprocess
import time
import urllib.request
from pathlib import Path

from pyppeteer import connect

USERNAME = "hour007"
PASSWORD = "No97@st26"
USERNAME_SELECTORS = [
    'input[name="username"]',
    'input[id="username"]',
    'input[type="email"]',
    'input[autocomplete="username"]',
    'input[type="text"]',
]
PASSWORD_SELECTORS = [
    'input[name="password"]',
    'input[id="password"]',
    'input[autocomplete="current-password"]',
    'input[type="password"]',
]


def wait_for_debugger(port: int, timeout_seconds: int = 15) -> None:
    endpoint = f"http://127.0.0.1:{port}/json/version"
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(endpoint, timeout=1):
                return
        except Exception as exc:  # pragma: no cover
            last_error = exc
            time.sleep(0.5)

    raise RuntimeError(f"Chrome remote debugger did not start: {last_error}")


async def wait_for_first_selector(page, selectors: list[str], timeout: int = 30000) -> str:
    deadline = time.time() + (timeout / 1000)

    while time.time() < deadline:
        for selector in selectors:
            handle = await page.querySelector(selector)
            if handle is not None:
                return selector
        await asyncio.sleep(0.25)

    raise TimeoutError(f"No matching selector found: {selectors}")


async def fill_field(page, selectors: list[str], value: str) -> str:
    selector = await wait_for_first_selector(page, selectors)
    await page.focus(selector)
    await page.evaluate(
        """selector => {
            const element = document.querySelector(selector);
            if (element) {
                element.value = '';
            }
        }""",
        selector,
    )
    await page.type(selector, value)
    return selector


async def click_sign_in(page) -> None:
    submit_xpath = (
        "//button[contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')"
        " or contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'log in')"
        " or contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login')]"
        "|//input[@type='submit']"
        "|//*[@role='button' and (contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')"
        " or contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'log in')"
        " or contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login'))]"
    )
    button = await page.waitForXPath(submit_xpath, {"timeout": 30000})
    await button.click()


async def main() -> None:
    project_dir = Path(__file__).resolve().parent
    profile_dir = project_dir / ".chrome-profile"
    chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    debug_port = 9222
    profile_dir.mkdir(exist_ok=True)
    browser = None

    chrome_process = subprocess.Popen(
        [
            str(chrome_path),
            f"--remote-debugging-port={debug_port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]
    )

    try:
        wait_for_debugger(debug_port)
        browser = await connect(browserURL=f"http://127.0.0.1:{debug_port}")
        page = await browser.newPage()
        page.setDefaultNavigationTimeout(90000)
        await page.setViewport({"width": 1280, "height": 800})
        await page.goto("https://www.facebook.com/", {"waitUntil": "domcontentloaded"})
        await fill_field(page, USERNAME_SELECTORS, USERNAME)
        await asyncio.sleep(2)
        await fill_field(page, PASSWORD_SELECTORS, PASSWORD)
        await asyncio.sleep(1)
        await click_sign_in(page)
        print("GoDaddy opened and sign-in was submitted. Press Ctrl+C in this terminal to stop the script.")

        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if browser is not None:
                await browser.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())

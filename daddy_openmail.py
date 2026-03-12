import asyncio
import subprocess
import time
import urllib.request
from pathlib import Path

from pyppeteer import connect

from read_inbox import read_godaddy_code, read_verification_code

EMAIL = "sohengheath@gmail.com"
PASSWORD = "Ying@salon"
LOGIN_URL = "https://mail.google.com/"
PASSWORD_URL = "https://accounts.google.com/v3/signin/challenge/pwd"
EMAIL_SELECTORS = [
    'input[type="email"]',
    'input[name="identifier"]',
    'input[id="identifierId"]',
]
PASSWORD_SELECTORS = [
    'input[type="password"]',
    'input[name="Passwd"]',
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
            try:
                handle = await page.querySelector(selector)
                if handle is not None:
                    return selector
            except Exception:
                pass
        await asyncio.sleep(0.5)

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


async def wait_for_visible_selector(page, selectors: list[str], timeout: int = 30000) -> str:
    deadline = time.time() + (timeout / 1000)

    while time.time() < deadline:
        for selector in selectors:
            is_visible = await page.evaluate(
                """selector => {
                    const element = document.querySelector(selector);
                    if (!element) {
                        return false;
                    }
                    const style = window.getComputedStyle(element);
                    return style &&
                        style.visibility !== 'hidden' &&
                        style.display !== 'none' &&
                        !element.disabled &&
                        element.offsetParent !== null;
                }""",
                selector,
            )
            if is_visible:
                return selector
        await asyncio.sleep(0.25)

    raise TimeoutError(f"No visible selector found: {selectors}")


async def click_next(page) -> None:
    next_xpath = (
        "//button[.//span[translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='next']]"
        "|//*[@role='button' and .//span[translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='next']]"
        "|//span[translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='next']/ancestor::button[1]"
    )
    button = await page.waitForXPath(next_xpath, {"timeout": 30000})
    await button.click()


async def get_verification_code() -> str:
    """
    Opens Gmail, logs in, finds the latest GoDaddy verification email,
    and returns the 6-digit code.
    """
    project_dir = Path(__file__).resolve().parent
    profile_dir = project_dir / ".chrome-profile-mail"
    chrome_path = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    debug_port = 9224
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
        await page.goto(LOGIN_URL, {"waitUntil": "networkidle0"})
        await asyncio.sleep(3)
        await wait_for_first_selector(page, EMAIL_SELECTORS, timeout=60000)
        await asyncio.sleep(2)
        await fill_field(page, EMAIL_SELECTORS, EMAIL)
        await asyncio.sleep(2)

        await click_next(page)

        for _ in range(120):
            try:
                if page.url.startswith(PASSWORD_URL):
                    break
            except Exception:
                pass
            await asyncio.sleep(0.5)

        print(page.url)
        await asyncio.sleep(3)
        await page.waitForSelector('input[type="password"]', {"timeout": 60000})
        await asyncio.sleep(2)
        await wait_for_visible_selector(page, PASSWORD_SELECTORS, timeout=60000)
        await fill_field(page, PASSWORD_SELECTORS, PASSWORD)
        await asyncio.sleep(2)
        await click_next(page)
        print("Gmail login successful. Now reading GoDaddy verification email...")
        await asyncio.sleep(5)

        code = await read_godaddy_code(page)
        print(f"Your GoDaddy 6-digit code is: {code}")
        return code
    finally:
        try:
            if browser is not None:
                await browser.disconnect()
        except Exception:
            pass


async def get_verification_code_with_config(
    search_query: str = "from:godaddy.com",
    sender_keyword: str = "godaddy",
    code_pattern: str = r"(\d{6})",
) -> str:
    """
    Opens Gmail, logs in, searches with the given query,
    and extracts the verification code using the given pattern.
    """
    project_dir = Path(__file__).resolve().parent
    profile_dir = project_dir / ".chrome-profile-mail"
    chrome_path = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    debug_port = 9224
    profile_dir.mkdir(exist_ok=True)
    browser = None

    subprocess.Popen(
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
        await page.goto(LOGIN_URL, {"waitUntil": "networkidle0"})
        await asyncio.sleep(3)
        # Wait for email input to appear after redirects
        email_sel = await wait_for_first_selector(page, EMAIL_SELECTORS, timeout=60000)
        await asyncio.sleep(2)
        await fill_field(page, EMAIL_SELECTORS, EMAIL)
        await asyncio.sleep(2)

        await click_next(page)

        # Wait for password page with retry on context destruction
        for _ in range(120):
            try:
                if page.url.startswith(PASSWORD_URL):
                    break
            except Exception:
                pass
            await asyncio.sleep(0.5)

        await asyncio.sleep(3)
        await page.waitForSelector('input[type="password"]', {"timeout": 60000})
        await asyncio.sleep(2)
        await wait_for_visible_selector(page, PASSWORD_SELECTORS, timeout=60000)
        await fill_field(page, PASSWORD_SELECTORS, PASSWORD)
        await asyncio.sleep(2)
        await click_next(page)
        print(f"  Gmail login successful. Searching: {search_query}")
        await asyncio.sleep(5)

        code = await read_verification_code(
            page,
            search_query=search_query,
            sender_keyword=sender_keyword,
            code_pattern=code_pattern,
        )
        print(f"  Verification code: {code}")
        return code
    finally:
        try:
            if browser is not None:
                await browser.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    code = asyncio.run(get_verification_code())
    print(f"Code: {code}")

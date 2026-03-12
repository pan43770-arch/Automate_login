import asyncio
import csv
import subprocess
import time
import urllib.request
from pathlib import Path

from pyppeteer import connect

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

LOGIN_URL = "https://www.facebook.com/"


def wait_for_debugger(port: int, timeout_seconds: int = 15) -> None:
    endpoint = f"http://127.0.0.1:{port}/json/version"
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(endpoint, timeout=1):
                return
        except Exception as exc:
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


async def fill_field(page, selectors: list[str], value: str, delay: int = 0) -> str:
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
    await page.type(selector, value, {"delay": delay})
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


async def login_one(browser, page, username: str, password: str, account_num: int, total: int) -> None:
    print(f"\n  Account {account_num}/{total}: {username}")
    await page.goto(LOGIN_URL, {"waitUntil": "domcontentloaded"})
    await asyncio.sleep(3)
    await fill_field(page, USERNAME_SELECTORS, username, delay=100)
    await asyncio.sleep(2)
    await fill_field(page, PASSWORD_SELECTORS, password, delay=150)
    await asyncio.sleep(1)
    await click_sign_in(page)
    print(f"  Login submitted for {username}, waiting 30 seconds...")
    await asyncio.sleep(30)


async def open_browser(profile_dir: Path, chrome_path: Path, debug_port: int):
    """Launch a new Chrome instance with its own profile and return (browser, page)."""
    profile_dir.mkdir(exist_ok=True)

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

    wait_for_debugger(debug_port)
    browser = await connect(browserURL=f"http://127.0.0.1:{debug_port}")
    page = await browser.newPage()
    page.setDefaultNavigationTimeout(90000)
    await page.setViewport({"width": 1280, "height": 800})
    return browser, page


async def main() -> None:
    project_dir = Path(__file__).resolve().parent

    # Ask user for CSV file path
    print("\n  === Login from CSV ===")
    csv_input = input("  Enter CSV file path (or filename in project folder): ").strip()
    if not csv_input:
        print("  ! No file entered.")
        return

    csv_path = Path(csv_input)
    if not csv_path.is_absolute():
        csv_path = project_dir / csv_input

    if not csv_path.exists():
        print(f"  ! CSV file not found: {csv_path}")
        return

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("  ! CSV file is empty.")
        return

    # Determine username/email column
    accounts = []
    for row in rows:
        username = row.get("email") or row.get("username") or row.get("mail") or ""
        password = row.get("password") or ""
        if username and password:
            accounts.append((username, password))

    if not accounts:
        print("  ! No valid accounts found. CSV needs 'email' and 'password' columns.")
        return

    print(f"\n  Found {len(accounts)} account(s) in {csv_path.name}")

    chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    base_port = 9222

    try:
        for i, (username, password) in enumerate(accounts, 1):
            # Each account gets its own chrome profile and debug port
            profile_dir = project_dir / f".chrome-profile-login-{i}"
            debug_port = base_port + i - 1

            print(f"\n  Opening browser {i} (port {debug_port})...")
            browser, page = await open_browser(profile_dir, chrome_path, debug_port)

            try:
                await login_one(browser, page, username, password, i, len(accounts))
            finally:
                try:
                    await browser.disconnect()
                except Exception:
                    pass

        print(f"\n  All {len(accounts)} account(s) done!")

    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    asyncio.run(main())

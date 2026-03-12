import asyncio
import subprocess
import time
import urllib.request
from pathlib import Path

from pyppeteer import connect

from daddy_openmail import get_verification_code

EMAIL = "h.hak123456@protonmail.com"
USERNAME = "h.hak066666655"
PASSWORD = "Hourlay007"
SIGNUP_URL = "https://sso.godaddy.com/account/create?prefillEmail=true"
EMAIL_SELECTORS = [
    'input[name="email"]',
    'input[id="email"]',
    'input[type="email"]',
    'input[autocomplete="email"]',
]
USERNAME_SELECTORS = [
    'input[name="username"]',
    'input[id="username"]',
    'input[autocomplete="username"]',
    'input[type="text"]',
]
PASSWORD_SELECTORS = [
    'input[name="password"]',
    'input[id="password"]',
    'input[autocomplete="new-password"]',
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


async def click_create_account(page) -> None:
    # Use JavaScript to find and click the Create Account button directly
    clicked = await page.evaluate(
        """() => {
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                const text = btn.textContent.trim().toLowerCase();
                if (text === 'create account') {
                    btn.click();
                    return true;
                }
            }
            return false;
        }"""
    )
    if not clicked:
        raise RuntimeError("Could not find 'Create Account' button")


async def click_send_verification_code(page) -> None:
    submit_xpath = (
        "//button[contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send verification code')]"
        "|//input[@type='submit' and contains(translate(@value, "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send verification code')]"
        "|//*[@role='button' and contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send verification code')]"
    )
    button = await page.waitForXPath(submit_xpath, {"timeout": 90000})
    await button.click()


async def sign_up() -> None:
    project_dir = Path(__file__).resolve().parent
    profile_dir = project_dir / ".chrome-profile"
    chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    debug_port = 9223
    profile_dir.mkdir(exist_ok=True)
    browser = None

    chrome_process = subprocess.Popen(
        [
            str(chrome_path),
            f"--remote-debugging-port={debug_port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--incognito",
            "about:blank",
        ]
    )

    try:
        wait_for_debugger(debug_port)
        browser = await connect(browserURL=f"http://127.0.0.1:{debug_port}")
        page = await browser.newPage()
        page.setDefaultNavigationTimeout(90000)
        await page.setViewport({"width": 1280, "height": 800})
        await page.goto(SIGNUP_URL, {"waitUntil": "domcontentloaded"})
        await fill_field(page, EMAIL_SELECTORS, EMAIL)
        await asyncio.sleep(2)
        await fill_field(page, USERNAME_SELECTORS, USERNAME)
        await asyncio.sleep(2)
        await fill_field(page, PASSWORD_SELECTORS, PASSWORD)
        await asyncio.sleep(2)

        # Click "Agree" button
        print("Clicking Agree button...")
        await page.evaluate(
            """() => {
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    const text = btn.textContent.trim().toLowerCase();
                    if (text.includes('agree')) {
                        btn.click();
                        return;
                    }
                }
            }"""
        )
        print("Agree clicked!")
        await asyncio.sleep(2)

        # Scroll down to make sure "Create Account" button is visible
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1)
        await click_create_account(page)
        print("Create Account clicked! Waiting for verification page...")
        await asyncio.sleep(5)
        await click_send_verification_code(page)
        print("Send Verification Code clicked!")
        await asyncio.sleep(5)

        # Get the 6-digit code from Gmail
        print("Opening Gmail to get verification code...")
        code = await get_verification_code()
        print(f"Got verification code: {code}")

        # Enter the code on the GoDaddy signup page
        await page.bringToFront()
        await asyncio.sleep(2)

        print(f"Entering verification code: {code}")
        verification_selectors = [
            'input[name="code"]',
            'input[name="verificationCode"]',
            'input[id="code"]',
            'input[type="text"]',
            'input[type="number"]',
        ]
        code_selector = await wait_for_first_selector(page, verification_selectors, timeout=30000)
        await page.focus(code_selector)
        await page.type(code_selector, code)
        print("Verification code entered.")

        await asyncio.sleep(2)

        # Click "Verify Code" button
        print("Clicking Verify Code button...")
        verify_xpath = (
            "//button[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'verify code')]"
            "|//input[@type='submit' and contains(translate(@value, "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'verify code')]"
            "|//*[@role='button' and contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'verify code')]"
        )
        verify_button = await page.waitForXPath(verify_xpath, {"timeout": 30000})
        await verify_button.click()
        print("Verify Code clicked! Signup verification complete.")

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
    asyncio.run(sign_up())

import asyncio
import subprocess
import time
import urllib.request
from pathlib import Path

import pyautogui
from pyppeteer import connect

PICTURES_DIR = Path(r"C:\Users\hak\Pictures\profile picture")
FACEBOOK_URL = "https://www.facebook.com/"


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


async def open_browser(profile_dir: Path, chrome_path: Path, debug_port: int):
    """Launch Chrome with given profile and return (browser, page)."""
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
    pages = await browser.pages()
    page = pages[0] if pages else await browser.newPage()
    page.setDefaultNavigationTimeout(90000)
    await page.setViewport({"width": 1280, "height": 800})
    return browser, page


async def click_span_text(page, text: str, timeout: int = 10) -> bool:
    """Wait and click on a span containing the given text."""
    text_lower = text.lower()
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = await page.evaluate("""(textToFind) => {
            const spans = document.querySelectorAll('span');
            for (const span of spans) {
                if (span.textContent.trim().toLowerCase() === textToFind) {
                    const clickable = span.closest('a, div[role="button"], div[tabindex], button') || span;
                    clickable.click();
                    return true;
                }
            }
            return false;
        }""", text_lower)
        if found:
            return True
        await asyncio.sleep(0.5)
    return False


async def change_profile_picture(page, picture_num: int) -> None:
    """Navigate to Facebook profile and change profile picture."""

    # Step 1: Go to Facebook
    print(f"    Going to Facebook...")
    await page.goto(FACEBOOK_URL, {"waitUntil": "networkidle0"})
    await asyncio.sleep(5)

    # Step 2: Click on profile link (avatar + name in sidebar)
    print(f"    Clicking on profile link...")
    clicked = await page.evaluate("""() => {
        const links = document.querySelectorAll('a[href]');
        for (const link of links) {
            const href = link.getAttribute('href');
            if (!href) continue;
            const svg = link.querySelector('svg image');
            const span = link.querySelector('span');
            if (svg && span && span.textContent.trim().length > 0) {
                const rect = link.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    link.click();
                    return span.textContent.trim();
                }
            }
        }
        return null;
    }""")

    if clicked:
        print(f"    Clicked profile: {clicked}")
    else:
        print(f"    Could not find profile link!")
        return

    await asyncio.sleep(5)

    # Step 3: Click "Choose profile picture"
    print(f"    Clicking 'Choose profile picture'...")
    if not await click_span_text(page, "Choose profile picture", timeout=10):
        # Try clicking on the profile picture area first to trigger the option
        print(f"    Text not found, clicking profile picture area first...")
        await page.evaluate("""() => {
            const images = document.querySelectorAll('image');
            for (const img of images) {
                const rect = img.getBoundingClientRect();
                if (rect.width >= 100) {
                    const parent = img.closest('a, div[role="button"], div[tabindex], g');
                    if (parent && parent.click) { parent.click(); }
                    else { img.dispatchEvent(new MouseEvent('click', {bubbles: true})); }
                    return true;
                }
            }
            return false;
        }""")
        await asyncio.sleep(3)
        # Try again
        if not await click_span_text(page, "Choose profile picture", timeout=10):
            print(f"    ! Could not find 'Choose profile picture'")
            return

    await asyncio.sleep(3)

    # Step 4: Click "Upload photo"
    print(f"    Clicking 'Upload Photo'...")
    # Click span with exact class from Facebook's Upload Photo button
    found_upload = await page.evaluate("""() => {
        const spans = document.querySelectorAll('span.x1lliihq.x6ikm8r.x10wlt62.x1n2onr6.xlyipyv.xuxw1ft');
        for (const span of spans) {
            if (span.textContent.trim().toLowerCase() === 'upload photo') {
                const clickable = span.closest('a, div[role="button"], div[tabindex], button') || span;
                clickable.click();
                return true;
            }
        }
        return false;
    }""")
    if not found_upload:
        # Fallback to generic span search
        if not await click_span_text(page, "Upload Photo", timeout=10):
            print(f"    ! Could not find 'Upload Photo'")
            return

    await asyncio.sleep(3)

    # Step 5: Windows file dialog opens - type path and select file
    picture_path = PICTURES_DIR / f"{picture_num}.jpg"
    if not picture_path.exists():
        print(f"    ! Picture not found: {picture_path}")
        return

    print(f"    File dialog opened, typing path...")
    await asyncio.sleep(2)

    # Type the folder path in the file dialog address bar
    pyautogui.hotkey("alt", "d")  # Focus address bar
    await asyncio.sleep(1)
    pyautogui.typewrite(str(PICTURES_DIR), interval=0.02)
    await asyncio.sleep(1)
    pyautogui.press("enter")  # Navigate to folder
    await asyncio.sleep(2)

    # Type the filename
    print(f"    Selecting {picture_path.name}...")
    pyautogui.hotkey("alt", "n")  # Focus filename field
    await asyncio.sleep(1)
    pyautogui.typewrite(f"{picture_num}.jpg", interval=0.02)
    await asyncio.sleep(1)
    pyautogui.press("enter")  # Double-click / Open the file
    await asyncio.sleep(5)

    print(f"    Photo uploaded: {picture_path.name}")

    # Step 6: Click Save button on Facebook
    print(f"    Clicking Save...")
    if await click_span_text(page, "Save", timeout=15):
        await asyncio.sleep(5)
        print(f"    Profile picture updated!")
    else:
        print(f"    ! Could not find 'Save' button")


async def main() -> None:
    project_dir = Path(__file__).resolve().parent
    chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    base_port = 9222

    # Find all chrome-profile-login-* directories
    profiles = sorted(project_dir.glob(".chrome-profile-login-*"))
    if not profiles:
        print("  ! No chrome login profiles found. Run open_godaddy.py first.")
        return

    # List available pictures
    pictures = sorted(PICTURES_DIR.glob("*.jpg")) + sorted(PICTURES_DIR.glob("*.png"))

    print(f"\n  === Auto Change Profile Picture ===")
    print(f"  Available profiles:")
    for i, p in enumerate(profiles, 1):
        print(f"    {i}. {p.name}")

    print(f"\n  Available pictures in {PICTURES_DIR}:")
    for pic in pictures:
        print(f"    - {pic.name}")

    # Ask which profile to use
    choice = input(f"\n  Enter profile number (1-{len(profiles)}): ").strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(profiles):
        print("  ! Invalid choice.")
        return

    profile_idx = int(choice)
    profile_dir = profiles[profile_idx - 1]
    debug_port = base_port + profile_idx - 1

    # Ask which picture to use
    pic_choice = input(f"  Enter picture number (e.g. 1 for 1.jpg): ").strip()
    if not pic_choice.isdigit():
        print("  ! Invalid choice.")
        return
    picture_num = int(pic_choice)

    picture_path = PICTURES_DIR / f"{picture_num}.jpg"
    if not picture_path.exists():
        print(f"  ! Picture not found: {picture_path}")
        return

    print(f"\n  Using profile: {profile_dir.name}")
    print(f"  Using picture: {picture_path.name}")
    print(f"  Opening browser (port {debug_port})...")

    browser, page = await open_browser(profile_dir, chrome_path, debug_port)

    try:
        await change_profile_picture(page, picture_num)
    except Exception as e:
        print(f"  ! Error: {e}")
    finally:
        try:
            await browser.disconnect()
        except Exception:
            pass

    print(f"\n  Done!")


if __name__ == "__main__":
    asyncio.run(main())

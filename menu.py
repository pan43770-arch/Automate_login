#!/usr/bin/env python3
"""
Interactive menu for configuring and running auto-signup.
Run: python menu.py
"""
import asyncio
import csv
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from pyppeteer import connect

# ── Config file ───────────────────────────────────────────────────────────────

CONFIG_FILE = Path(__file__).resolve().parent / "signup_config.json"

DEFAULT_CONFIG = {
    "url": "https://sso.godaddy.com/account/create?prefillEmail=true",
    "browser_path": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "debug_port": 9223,
    "profile_dir": ".chrome-profile-menu",
    "csv_file": "",
    "use_email_verification": True,
    "fields": [
        {
            "name": "Email",
            "key": "email",
            "enabled": True,
            "order": 1,
            "selectors": [
                'input[name="email"]',
                'input[id="email"]',
                'input[type="email"]',
                'input[autocomplete="email"]',
            ],
        },
        {
            "name": "Username",
            "key": "username",
            "enabled": True,
            "order": 2,
            "selectors": [
                'input[name="username"]',
                'input[id="username"]',
                'input[autocomplete="username"]',
            ],
        },
        {
            "name": "Password",
            "key": "password",
            "enabled": True,
            "order": 3,
            "selectors": [
                'input[name="password"]',
                'input[id="password"]',
                'input[autocomplete="new-password"]',
                'input[type="password"]',
            ],
        },
        {
            "name": "First Name",
            "key": "first_name",
            "enabled": False,
            "order": 4,
            "selectors": [
                'input[name="firstName"]',
                'input[id="firstName"]',
                'input[name="first_name"]',
                'input[placeholder*="irst"]',
            ],
        },
        {
            "name": "Last Name",
            "key": "last_name",
            "enabled": False,
            "order": 5,
            "selectors": [
                'input[name="lastName"]',
                'input[id="lastName"]',
                'input[name="last_name"]',
                'input[placeholder*="ast"]',
            ],
        },
        {
            "name": "Date of Birth - Day",
            "key": "dob_day",
            "enabled": False,
            "order": 6,
            "selectors": [
                'input[name="day"]',
                'select[name="day"]',
                'input[id="day"]',
            ],
        },
        {
            "name": "Date of Birth - Month",
            "key": "dob_month",
            "enabled": False,
            "order": 7,
            "selectors": [
                'select[name="month"]',
                'input[name="month"]',
                'input[id="month"]',
            ],
        },
        {
            "name": "Date of Birth - Year",
            "key": "dob_year",
            "enabled": False,
            "order": 8,
            "selectors": [
                'input[name="year"]',
                'select[name="year"]',
                'input[id="year"]',
            ],
        },
        {
            "name": "Gender",
            "key": "gender",
            "enabled": False,
            "order": 9,
            "selectors": [
                'select[name="gender"]',
                'input[name="gender"]',
            ],
        },
    ],
    "buttons": [
        {"name": "Agree",                  "text": "agree",                  "enabled": True,  "order": 1},
        {"name": "Create New Account",     "text": "create new account",     "enabled": True,  "order": 2},
        {"name": "Send Verification Code", "text": "send verification code", "enabled": True,  "order": 3},
        {"name": "Verify Code",            "text": "verify code",            "enabled": True,  "order": 4},
        {"name": "Submit",                 "text": "submit",                 "enabled": False, "order": 5},
        {"name": "Login / Sign In",        "text": "sign in",                "enabled": False, "order": 6},
        {"name": "Next",                   "text": "next",                   "enabled": False, "order": 7},
        {"name": "Continue",               "text": "continue",               "enabled": False, "order": 8},
    ],
}


# ── Config helpers ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print("  ✔ Config saved.")


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def pause():
    input("\n  Press Enter to continue...")


def print_header(title: str):
    print("=" * 62)
    print(f"  {title}")
    print("=" * 62)


# ── Sub-menus ──────────────────────────────────────────────────────────────────

def menu_set_url(cfg: dict):
    clear()
    print_header("Set URL")
    print(f"\n  Current: {cfg['url']}")
    val = input("\n  New URL (blank = keep current): ").strip()
    if val:
        cfg["url"] = val
        save_config(cfg)


def menu_set_browser(cfg: dict):
    clear()
    print_header("Set Browser Path")
    print(f"\n  Current: {cfg['browser_path']}")
    print("\n  Examples:")
    print(r"    Edge  : C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    print(r"    Chrome: C:\Program Files\Google\Chrome\Application\chrome.exe")
    print(r"    Brave : C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")
    val = input("\n  New path (blank = keep current): ").strip().strip('"')
    if val:
        if Path(val).exists():
            cfg["browser_path"] = val
            save_config(cfg)
        else:
            print(f"  ! File not found: {val}")
            pause()


def menu_fields(cfg: dict):
    while True:
        clear()
        print_header("Configure Fields")
        fields = sorted(cfg["fields"], key=lambda f: f["order"])

        print(f"\n  {'#':<4} {'STATUS':<7} {'FILL ORDER':<12} {'FIELD NAME':<28} {'CSV COLUMN NAME'}")
        print(f"  {'-'*75}")
        for i, f in enumerate(fields, 1):
            if f["enabled"]:
                status = " ON  <<<"
            else:
                status = " OFF    "
            print(f"  {i:<4} [{status}]  step {f['order']:<6} {f['name']:<28} \"{f['key']}\"")

        # Show active fill order
        active = sorted([f for f in fields if f["enabled"]], key=lambda f: f["order"])
        if active:
            print(f"\n  Fill order: {' → '.join(f['name'] for f in active)}")
            csv_headers = ', '.join(f["key"] for f in active)
            print(f"\n  Your CSV must have these column headers:")
            print(f"  {csv_headers}")
        else:
            print("\n  Fill order: (none selected)")

        print("\n  T <#>        — Toggle ON/OFF  (e.g. T 3)")
        print("  O <#> <pos>  — Change order   (e.g. O 2 1)")
        print("  B            — Back")
        choice = input("\n  > ").strip().upper()

        if choice == "B":
            break
        parts = choice.split()
        if parts[0] == "T" and len(parts) == 2 and parts[1].isdigit():
            idx = int(parts[1]) - 1
            if 0 <= idx < len(fields):
                fields[idx]["enabled"] = not fields[idx]["enabled"]
                save_config(cfg)
        elif parts[0] == "O" and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            idx = int(parts[1]) - 1
            new_order = int(parts[2])
            if 0 <= idx < len(fields):
                fields[idx]["order"] = new_order
                save_config(cfg)
        else:
            print("  ! Unknown command.")
            pause()


def menu_buttons(cfg: dict):
    while True:
        clear()
        print_header("Configure Buttons")
        buttons = sorted(cfg["buttons"], key=lambda b: b["order"])

        print(f"\n  {'#':<4} {'STATUS':<7} {'RUN ORDER':<11} {'BUTTON NAME':<28} {'MATCHES TEXT ON PAGE'}")
        print(f"  {'-'*75}")
        for i, b in enumerate(buttons, 1):
            if b["enabled"]:
                status = " ON  <<<"
            else:
                status = " OFF    "
            print(f"  {i:<4} [{status}]  step {b['order']:<6} {b['name']:<28} \"{b['text']}\"")

        # Show active flow summary
        active = sorted([b for b in buttons if b["enabled"]], key=lambda b: b["order"])
        if active:
            print(f"\n  Active flow: {' → '.join(b['name'] for b in active)}")
        else:
            print("\n  Active flow: (none selected)")

        print("\n  T <#>        — Toggle ON/OFF  (e.g. T 2)")
        print("  O <#> <pos>  — Change order   (e.g. O 3 1)")
        print("  B            — Back")
        choice = input("\n  > ").strip().upper()

        if choice == "B":
            break
        parts = choice.split()
        if parts[0] == "T" and len(parts) == 2 and parts[1].isdigit():
            idx = int(parts[1]) - 1
            if 0 <= idx < len(buttons):
                buttons[idx]["enabled"] = not buttons[idx]["enabled"]
                save_config(cfg)
        elif parts[0] == "O" and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            idx = int(parts[1]) - 1
            new_order = int(parts[2])
            if 0 <= idx < len(buttons):
                buttons[idx]["order"] = new_order
                save_config(cfg)
        else:
            print("  ! Unknown command.")
            pause()


def menu_csv(cfg: dict):
    clear()
    print_header("Set CSV File")
    print(f"\n  Current: {cfg['csv_file'] or '(none)'}")
    print("\n  CSV column names (use only the fields you enabled):")
    print("  ┌────────────────────────────────────────────────────┐")
    print("  │  email, username, password, first_name, last_name  │")
    print("  │  dob_day, dob_month, dob_year, gender              │")
    print("  └────────────────────────────────────────────────────┘")
    print("\n  Example CSV:")
    print("  email,username,password")
    print("  user1@mail.com,user1,Pass@123")
    print("  user2@mail.com,user2,Pass@456")
    val = input("\n  CSV file path (blank = keep current): ").strip().strip('"')
    if val:
        p = Path(val)
        if p.exists():
            cfg["csv_file"] = str(p)
            save_config(cfg)
            with open(p, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            cols = list(rows[0].keys()) if rows else []
            print(f"\n  Loaded {len(rows)} row(s).")
            print(f"  Columns found: {', '.join(cols)}")
        else:
            print(f"\n  ! File not found: {val}")
        pause()


def menu_verification(cfg: dict):
    clear()
    print_header("Email Verification")
    status = "ON" if cfg["use_email_verification"] else "OFF"
    print(f"\n  Auto-read verification code from Gmail: [{status}]")
    print("\n  When ON  — after clicking 'Send Verification Code', the")
    print("             script opens Gmail, finds the code and enters it.")
    print("  When OFF — script pauses and you enter the code manually.")
    toggle = input("\n  Toggle? (y/n): ").strip().lower()
    if toggle == "y":
        cfg["use_email_verification"] = not cfg["use_email_verification"]
        save_config(cfg)
        new_status = "ON" if cfg["use_email_verification"] else "OFF"
        print(f"  → Email verification is now {new_status}")
        pause()


# ── Browser / page helpers ─────────────────────────────────────────────────────

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
    raise RuntimeError(f"Browser remote debugger did not start: {last_error}")


async def wait_for_first_selector(page, selectors: list, timeout: int = 30000) -> str:
    deadline = time.time() + timeout / 1000
    while time.time() < deadline:
        for sel in selectors:
            if await page.querySelector(sel) is not None:
                return sel
        # Also try to find visible input/select inside dialogs or modals
        found = await page.evaluate(
            """(sels) => {
                for (const sel of sels) {
                    const el = document.querySelector(sel);
                    if (el) return sel;
                }
                // Check inside iframes
                const iframes = document.querySelectorAll('iframe');
                for (const iframe of iframes) {
                    try {
                        const doc = iframe.contentDocument;
                        if (!doc) continue;
                        for (const sel of sels) {
                            if (doc.querySelector(sel)) return sel;
                        }
                    } catch(e) {}
                }
                return null;
            }""",
            selectors,
        )
        if found:
            return found
        await asyncio.sleep(0.25)
    raise TimeoutError(f"No selector found: {selectors}")


async def find_input_by_label(page, label_text: str, field_key: str = "", timeout: int = 30000):
    """Find an input/select by its visible label text (works with Facebook's dynamic IDs).

    field_key helps disambiguate when multiple inputs exist near the same label group
    (e.g. dob_day, dob_month, dob_year are all near 'Date of birth').
    """
    deadline = time.time() + timeout / 1000

    # Map field keys to search hints for Facebook's specific DOM
    LABEL_MAP = {
        "first_name": ["first name"],
        "last_name": ["surname", "last name"],
        "email": ["mobile number or email", "email address or phone number", "email"],
        "password": ["new password", "password"],
        "dob_day": ["date of birth"],
        "dob_month": ["date of birth"],
        "dob_year": ["date of birth"],
        "gender": ["gender"],
    }

    # For DOB: Facebook uses div[role="combobox"] with aria-label
    DOB_COMBOBOX_LABEL = {
        "dob_day": "select day",
        "dob_month": "select month",
        "dob_year": "select year",
    }

    search_labels = LABEL_MAP.get(field_key, [label_text.lower()])

    combobox_label = DOB_COMBOBOX_LABEL.get(field_key, "")

    while time.time() < deadline:
        result = await page.evaluate(
            """(args) => {
                const searchLabels = args.labels;
                const fieldKey = args.fieldKey;
                const comboboxLabel = args.comboboxLabel;
                const uniqueId = 'auto-' + fieldKey;

                function isClaimed(el) {
                    const attr = el.getAttribute('data-auto-found');
                    return attr && attr !== uniqueId;
                }

                function labelMatches(text, search) {
                    const t = text.trim().toLowerCase();
                    return t === search || t === search + ' *' || t === search + ':';
                }

                // For DOB: directly find combobox by aria-label (e.g. "Select day")
                if (comboboxLabel) {
                    const combobox = document.querySelector(
                        '[role="combobox"][aria-label="' + comboboxLabel + '" i]'
                    );
                    if (combobox) {
                        combobox.setAttribute('data-auto-found', uniqueId);
                        return { tag: 'combobox', type: 'combobox',
                                 selector: '[data-auto-found="' + uniqueId + '"]',
                                 ariaLabel: comboboxLabel };
                    }
                    // Fallback: case-insensitive search through all comboboxes
                    const allCombo = document.querySelectorAll('[role="combobox"]');
                    for (const cb of allCombo) {
                        const aria = (cb.getAttribute('aria-label') || '').toLowerCase();
                        if (aria === comboboxLabel && !isClaimed(cb)) {
                            cb.setAttribute('data-auto-found', uniqueId);
                            return { tag: 'combobox', type: 'combobox',
                                     selector: '[data-auto-found="' + uniqueId + '"]',
                                     ariaLabel: comboboxLabel };
                        }
                    }
                }

                // Strategy 1: find <label> whose text matches exactly
                const labels = document.querySelectorAll('label');
                for (const label of labels) {
                    let directText = '';
                    for (const node of label.childNodes) {
                        if (node.nodeType === 3) directText += node.textContent;
                    }
                    const lt = (directText.trim() || label.textContent.trim()).toLowerCase();
                    for (const search of searchLabels) {
                        if (!labelMatches(lt, search) && lt !== search) continue;
                        const forId = label.getAttribute('for');
                        if (forId) {
                            const el = document.getElementById(forId);
                            if (el && !isClaimed(el)) {
                                el.setAttribute('data-auto-found', uniqueId);
                                return { id: forId, tag: el.tagName.toLowerCase(), type: el.type || '' };
                            }
                        }
                        const input = label.querySelector('input, select, textarea');
                        if (input && !isClaimed(input)) {
                            input.setAttribute('data-auto-found', uniqueId);
                            return { tag: input.tagName.toLowerCase(), type: input.type || '',
                                     selector: '[data-auto-found="' + uniqueId + '"]' };
                        }
                    }
                }

                // Strategy 2: find text elements matching the label
                const allEls = document.querySelectorAll('span, div, p, label, h2, h3, td, th');
                for (const el of allEls) {
                    const fullText = el.textContent.trim().toLowerCase();
                    if (!fullText) continue;

                    for (const search of searchLabels) {
                        const matches = fullText === search
                            || fullText === search + ' *'
                            || fullText === search + ':'
                            || (el.children.length === 0 && fullText.includes(search) && fullText.length < search.length + 10);
                        if (!matches) continue;

                        // For gender: find radio buttons, select, or combobox
                        if (fieldKey === 'gender') {
                            let container = el.parentElement;
                            for (let i = 0; i < 10 && container; i++) {
                                // Check for combobox first
                                const combo = container.querySelector('[role="combobox"]');
                                if (combo && !isClaimed(combo)) {
                                    combo.setAttribute('data-auto-found', uniqueId);
                                    return { tag: 'combobox', type: 'combobox',
                                             selector: '[data-auto-found="' + uniqueId + '"]' };
                                }
                                const selects = container.querySelectorAll('select');
                                for (const s of selects) {
                                    if (!isClaimed(s)) {
                                        s.setAttribute('data-auto-found', uniqueId);
                                        return { tag: 'select', type: '',
                                                 selector: '[data-auto-found="' + uniqueId + '"]' };
                                    }
                                }
                                const radios = container.querySelectorAll('input[type="radio"]');
                                if (radios.length >= 2) {
                                    radios[0].setAttribute('data-auto-found', uniqueId);
                                    return { tag: 'input', type: 'radio',
                                             selector: '[data-auto-found="' + uniqueId + '"]' };
                                }
                                container = container.parentElement;
                            }
                        }

                        // Default: find nearest unclaimed input (skip for DOB — handled above)
                        if (!comboboxLabel && fieldKey !== 'gender') {
                            let parent = el.parentElement;
                            for (let i = 0; i < 5 && parent; i++) {
                                const inputs = parent.querySelectorAll(
                                    'input:not([type="hidden"]):not([type="radio"]):not([type="submit"]), select, textarea'
                                );
                                for (const input of inputs) {
                                    if (!isClaimed(input)) {
                                        input.setAttribute('data-auto-found', uniqueId);
                                        return { tag: input.tagName.toLowerCase(), type: input.type || '',
                                                 selector: '[data-auto-found="' + uniqueId + '"]' };
                                    }
                                }
                                parent = parent.parentElement;
                            }
                        }
                    }
                }
                return null;
            }""",
            {"labels": search_labels, "fieldKey": field_key,
             "comboboxLabel": combobox_label},
        )
        if result:
            if result.get('id'):
                return f"#{result['id']}", result['tag'], result['type']
            elif result.get('selector'):
                return result['selector'], result['tag'], result['type']
        await asyncio.sleep(0.5)
    return None, None, None


async def fill_field(page, selectors: list, value: str, field_name: str = "", field_key: str = ""):
    # First try standard CSS selectors
    sel = None
    tag_name = ""
    input_type = ""
    try:
        sel = await wait_for_first_selector(page, selectors, timeout=5000)
        tag_name = await page.evaluate(
            "s => { const e = document.querySelector(s); return e ? e.tagName.toLowerCase() : ''; }",
            sel,
        )
        input_type = await page.evaluate(
            "s => { const e = document.querySelector(s); return e ? (e.type || '') : ''; }",
            sel,
        )
    except TimeoutError:
        # Fallback: find input by its label text (for sites like Facebook with random IDs)
        if field_name:
            print(f"    (selectors not found, searching by label text: \"{field_name}\")")
            sel, tag_name, input_type = await find_input_by_label(
                page, field_name, field_key=field_key, timeout=15000
            )
            if not sel:
                raise TimeoutError(f"No selector or label found for: {field_name}")
        else:
            raise

    if tag_name == "combobox":
        # Custom ARIA combobox (Facebook style): click to open, then click the option
        # For month: convert number to month name
        MONTH_NAMES = {
            "1": "January", "2": "February", "3": "March", "4": "April",
            "5": "May", "6": "June", "7": "July", "8": "August",
            "9": "September", "10": "October", "11": "November", "12": "December",
        }
        option_text = str(value).strip()
        # If month is a number, convert to name; if already a name, use as-is
        if field_key == "dob_month":
            if option_text in MONTH_NAMES:
                option_text = MONTH_NAMES[option_text]
            # else assume it's already a month name like "May", "June"
        print(f"    → Clicking combobox, selecting: {option_text}")

        # Click the combobox to open it
        await page.click(sel)
        await asyncio.sleep(3)

        # Find and click the matching option
        clicked = await page.evaluate(
            """(optText) => {
                const options = document.querySelectorAll('[role="option"]');
                const target = optText.trim().toLowerCase();
                for (const opt of options) {
                    if (opt.textContent.trim().toLowerCase() === target) {
                        opt.click();
                        return true;
                    }
                }
                return false;
            }""",
            option_text,
        )
        if not clicked:
            print(f"    ! Could not find option: {option_text}")
        await asyncio.sleep(3)

    elif tag_name == "select":
        # Native <select> dropdown
        await page.click(sel)
        await asyncio.sleep(3)
        await page.evaluate(
            """(args) => {
                const el = document.querySelector(args.sel);
                if (!el) return;
                el.value = args.val;
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }""",
            {"sel": sel, "val": str(value)},
        )
        await asyncio.sleep(3)

    elif input_type == "radio":
        # For gender: Facebook uses value="1" for Female, value="2" for Male
        gender_val = str(value).strip().lower()
        gender_map = {"female": "1", "male": "2", "1": "1", "2": "2"}
        radio_value = gender_map.get(gender_val, gender_val)
        clicked = await page.evaluate(
            """(val) => {
                const radios = document.querySelectorAll('input[type="radio"]');
                for (const r of radios) {
                    if (r.value === val) {
                        const label = r.closest('label') || document.querySelector('label[for="' + r.id + '"]');
                        if (label) { label.click(); return true; }
                        r.click();
                        r.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
                return false;
            }""",
            radio_value,
        )
        if not clicked:
            await page.click(sel)
        await asyncio.sleep(3)

    else:
        # Text input
        await page.click(sel)
        await asyncio.sleep(3)
        await page.evaluate(
            "s => { const e = document.querySelector(s); if (e) e.value = ''; }",
            sel,
        )
        await page.type(sel, str(value))
        await asyncio.sleep(3)


async def click_button_by_text(page, text: str, timeout: int = 30000):
    lower = text.lower()
    upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    lower_alpha = "abcdefghijklmnopqrstuvwxyz"
    tr = f"translate(normalize-space(.),'{upper}','{lower_alpha}')"
    xpath = (
        # button whose own text matches
        f"//button[contains({tr},'{lower}')]"
        # button containing a span/child whose text matches (e.g. Facebook)
        f"|//button[.//*[contains(translate(normalize-space(.),'{upper}','{lower_alpha}'),'{lower}')]]"
        # role=button element
        f"|//*[@role='button' and contains({tr},'{lower}')]"
        f"|//*[@role='button' and .//*[contains(translate(normalize-space(.),'{upper}','{lower_alpha}'),'{lower}')]]"
        # anchor tag acting as button
        f"|//a[contains({tr},'{lower}')]"
        # input submit
        f"|//input[@type='submit' and contains(translate(@value,'{upper}','{lower_alpha}'),'{lower}')]"
    )
    btn = await page.waitForXPath(xpath, {"timeout": timeout})
    await btn.click()
    print(f"  → Clicked [{text}]")


# ── Signup runner ──────────────────────────────────────────────────────────────

async def run_signup(cfg: dict, row: dict):
    project_dir = Path(__file__).resolve().parent
    profile_dir = project_dir / cfg["profile_dir"]
    browser_path = Path(cfg["browser_path"])
    debug_port = int(cfg["debug_port"])
    profile_dir.mkdir(exist_ok=True)
    browser = None

    subprocess.Popen([
        str(browser_path),
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    ])

    try:
        wait_for_debugger(debug_port)
        browser = await connect(browserURL=f"http://127.0.0.1:{debug_port}")
        page = await browser.newPage()
        page.setDefaultNavigationTimeout(90000)
        await page.setViewport({"width": 1280, "height": 800})

        print(f"\n  Opening: {cfg['url']}")
        await page.goto(cfg["url"], {"waitUntil": "networkidle0"})
        await asyncio.sleep(4)

        # ── Build unified execution list (fields + buttons merged by order) ───
        steps = []
        for f in cfg["fields"]:
            if f["enabled"]:
                steps.append({"type": "field", "order": f["order"], "data": f})
        for b in cfg["buttons"]:
            if b["enabled"]:
                steps.append({"type": "button", "order": b["order"], "data": b})
        steps.sort(key=lambda s: s["order"])

        # ── Execute each step in order ────────────────────────────────────────
        for step in steps:
            if step["type"] == "field":
                field = step["data"]
                value = row.get(field["key"], "").strip()
                if not value:
                    print(f"  ⚠ Skipping [{field['name']}] — no value in CSV row")
                    continue
                print(f"  Filling [{field['name']}]: {value}")
                await fill_field(page, field["selectors"], value, field_name=field["name"], field_key=field["key"])
                await asyncio.sleep(1)

            else:  # button
                btn_text = step["data"]["text"]

                if btn_text == "send verification code":
                    await click_button_by_text(page, btn_text, timeout=90000)
                    await asyncio.sleep(5)

                    if cfg["use_email_verification"]:
                        from daddy_openmail import get_verification_code
                        print("  Fetching verification code from Gmail...")
                        code = await get_verification_code()
                        print(f"  Got code: {code}")
                        await page.bringToFront()
                        await asyncio.sleep(2)
                    else:
                        code = input("  Enter the verification code you received: ").strip()

                    code_selectors = [
                        'input[name="code"]',
                        'input[name="verificationCode"]',
                        'input[id="code"]',
                        'input[type="number"]',
                        'input[type="text"]',
                    ]
                    code_sel = await wait_for_first_selector(page, code_selectors, timeout=30000)
                    await page.focus(code_sel)
                    await page.type(code_sel, code)
                    print(f"  Verification code [{code}] entered.")
                    await asyncio.sleep(2)

                else:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)
                    await click_button_by_text(page, btn_text)
                    await asyncio.sleep(3)
                    # Wait for navigation or modal to load after button click
                    try:
                        await page.waitForNavigation({"waitUntil": "networkidle0", "timeout": 5000})
                    except Exception:
                        pass  # No navigation happened (e.g. modal popup)
                    await asyncio.sleep(2)

        print("\n  ✔ Signup flow complete! Browser stays open. Press Ctrl+C to exit.")
        while True:
            await asyncio.sleep(3600)

    except KeyboardInterrupt:
        pass
    finally:
        try:
            if browser:
                await browser.disconnect()
        except Exception:
            pass


async def run_all(cfg: dict):
    if not cfg.get("csv_file"):
        print("\n  No CSV file set. Please go to menu → Set CSV File first.")
        pause()
        return

    csv_path = Path(cfg["csv_file"])
    if not csv_path.exists():
        print(f"\n  ! CSV file not found: {csv_path}")
        pause()
        return

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("\n  ! CSV file is empty.")
        pause()
        return

    print(f"\n  {len(rows)} account(s) found in CSV.")
    for i, row in enumerate(rows, 1):
        label = row.get("email") or row.get("username") or f"row {i}"
        print(f"\n{'='*62}")
        print(f"  Account {i}/{len(rows)}: {label}")
        print("=" * 62)
        await run_signup(cfg, row)
        if i < len(rows):
            cont = input("\n  Continue to next account? (y/n): ").strip().lower()
            if cont != "y":
                print("  Stopped.")
                break


# ── Main menu ──────────────────────────────────────────────────────────────────

def show_summary(cfg: dict):
    csv_label = Path(cfg["csv_file"]).name if cfg["csv_file"] else "(none)"
    verif = "ON" if cfg["use_email_verification"] else "OFF"
    print(f"\n  URL     : {cfg['url'][:55]}")
    print(f"  Browser : {Path(cfg['browser_path']).name}")
    print(f"  CSV     : {csv_label}")
    print(f"  Gmail verification: {verif}")

    # Combined full execution flow — merge fields + buttons sorted by their order number
    all_steps = []
    for f in cfg["fields"]:
        if f["enabled"]:
            all_steps.append({"type": "field",  "order": f["order"], "data": f})
    for b in cfg["buttons"]:
        if b["enabled"]:
            all_steps.append({"type": "button", "order": b["order"], "data": b})
    all_steps.sort(key=lambda s: s["order"])

    print(f"\n  {'─'*62}")
    print(f"  FULL EXECUTION FLOW  (order number controls position)")
    print(f"  {'─'*62}")
    if not all_steps:
        print(f"  (nothing configured)")
    for s in all_steps:
        if s["type"] == "field":
            f = s["data"]
            print(f"  Order {s['order']:<4} [FILL]   {f['name']:<26} CSV: \"{f['key']}\"")
        else:
            b = s["data"]
            print(f"  Order {s['order']:<4} [CLICK]  {b['name']:<26} text: \"{b['text']}\"")
    print(f"  {'─'*62}")
    print(f"  To change position: go to menu 3 (Fields) or 4 (Buttons)")
    print(f"  then type:  O <row#> <new order number>")


def main():
    cfg = load_config()
    while True:
        clear()
        print_header("Auto Signup — Main Menu")
        show_summary(cfg)
        print("\n  1. Set URL")
        print("  2. Set Browser Path")
        print("  3. Configure Fields  (choose & order)")
        print("  4. Configure Buttons (choose & order)")
        print("  5. Set CSV File")
        print("  6. Email Verification (auto-read from Gmail)")
        print("  7. Run Signup")
        print("  0. Exit")

        choice = input("\n  Choice: ").strip()
        if choice == "1":
            menu_set_url(cfg)
        elif choice == "2":
            menu_set_browser(cfg)
        elif choice == "3":
            menu_fields(cfg)
        elif choice == "4":
            menu_buttons(cfg)
        elif choice == "5":
            menu_csv(cfg)
        elif choice == "6":
            menu_verification(cfg)
        elif choice == "7":
            clear()
            print_header("Run Signup")
            show_summary(cfg)
            confirm = input("\n  Start? (y/n): ").strip().lower()
            if confirm == "y":
                asyncio.run(run_all(cfg))
        elif choice == "0":
            print("\n  Bye!")
            sys.exit(0)


if __name__ == "__main__":
    main()

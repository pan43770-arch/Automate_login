import asyncio
import re
import time


async def read_godaddy_code(page, timeout: int = 60000) -> str:
    """
    Given a Gmail inbox page, find the latest GoDaddy verification email
    and extract the 6-digit code after "Here is your email verification code:".
    Returns the code as a string.
    """

    # Step 1: Wait for Gmail inbox to fully load
    print("Waiting for Gmail inbox to load...")
    await page.waitForSelector('input[aria-label="Search mail"]', {"timeout": 60000})
    await asyncio.sleep(3)
    print("Inbox loaded.")

    # Step 2: Search for GoDaddy emails
    print("Searching for GoDaddy emails...")
    search_input = await page.querySelector('input[aria-label="Search mail"]')
    await search_input.click()
    await asyncio.sleep(1)
    await search_input.type('from:godaddy.com')
    await asyncio.sleep(0.5)
    await page.keyboard.press("Enter")
    await asyncio.sleep(5)
    print("Search complete.")

    # Step 3: From the search results, filter only rows where sender contains "GoDaddy"
    # then pick the one with the latest timestamp
    print("Filtering only GoDaddy sender rows and finding the latest...")
    result = await page.evaluate(
        """() => {
            const rows = document.querySelectorAll('tr.zA, tr.zE');
            const godaddyRows = [];

            for (let i = 0; i < rows.length; i++) {
                // Check if the sender name/column contains "GoDaddy" (case-insensitive)
                const senderEl = rows[i].querySelector('.yX .yW span[email], .yX .yW .bA4 span, .yX .yW span');
                const senderText = senderEl ? senderEl.textContent : '';
                const rowText = rows[i].innerText || '';

                if (senderText.toLowerCase().includes('godaddy') || rowText.toLowerCase().includes('godaddy')) {
                    // Get the timestamp
                    const timeSpan = rows[i].querySelector('td.xW span[title]');
                    const timeTitle = timeSpan ? timeSpan.getAttribute('title') : '';
                    const timestamp = timeTitle ? new Date(timeTitle).getTime() : 0;

                    godaddyRows.push({
                        index: i,
                        sender: senderText,
                        time: timeTitle,
                        timestamp: timestamp
                    });
                }
            }

            if (godaddyRows.length === 0) return null;

            // Sort by timestamp descending (newest first)
            godaddyRows.sort((a, b) => b.timestamp - a.timestamp);

            return {
                total: rows.length,
                godaddyCount: godaddyRows.length,
                latest: godaddyRows[0],
                all: godaddyRows
            };
        }"""
    )

    if not result:
        raise RuntimeError("No GoDaddy emails found in search results.")

    print(f"Search returned {result['total']} total emails, {result['godaddyCount']} are from GoDaddy.")
    for row in result['all']:
        print(f"  - Sender: {row['sender']}, Time: {row['time']}")

    latest = result['latest']
    print(f"Clicking the latest GoDaddy email: sender='{latest['sender']}', time='{latest['time']}'")

    # Click the latest GoDaddy email row
    await page.evaluate(
        """(idx) => {
            const rows = document.querySelectorAll('tr.zA, tr.zE');
            if (rows[idx]) rows[idx].click();
        }""",
        latest['index'],
    )

    # Step 4: Wait for the email to open and load
    print("Waiting for email content to load...")
    await asyncio.sleep(5)

    # Step 5: Read the email body
    body_text = await page.evaluate(
        """() => {
            const selectors = [
                '.a3s.aiL',
                'div.a3s',
                'div[data-message-id]',
                'div[role="list"] div[role="listitem"]',
                'div.gs',
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText.trim().length > 0) {
                    return el.innerText;
                }
            }
            const main = document.querySelector('div[role="main"]');
            return main ? main.innerText : document.body.innerText;
        }"""
    )

    print(f"Email body preview: {body_text[:300]}...")

    # Step 6: Find the 6-digit code
    match = re.search(
        r'[Hh]ere is your email verification code[:\s]*(\d{6})',
        body_text,
    )

    if match:
        code = match.group(1)
        print(f"GoDaddy verification code: {code}")
        return code

    # Fallback: find any standalone 6-digit number
    fallback = re.search(r'\b(\d{6})\b', body_text)
    if fallback:
        code = fallback.group(1)
        print(f"GoDaddy verification code (fallback): {code}")
        return code

    raise ValueError(f"Could not find 6-digit code in email body:\n{body_text[:500]}")

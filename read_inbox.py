import asyncio
import re
import time


async def read_verification_code(
    page,
    search_query: str = "from:godaddy.com",
    sender_keyword: str = "godaddy",
    code_pattern: str = r"(\d{6})",
    timeout: int = 60000,
) -> str:
    """
    Given a Gmail inbox page, search for emails matching the query,
    find the latest one from the sender, and extract the verification code.

    Args:
        page: pyppeteer page object (already on Gmail inbox)
        search_query: Gmail search query (e.g. "from:godaddy.com", "from:github.com")
        sender_keyword: keyword to filter sender rows (e.g. "godaddy", "github", "facebook")
        code_pattern: regex pattern to extract the code from email body
        timeout: max wait time in ms
    """

    # Step 1: Wait for Gmail inbox to fully load
    print("  Waiting for Gmail inbox to load...")
    await page.waitForSelector('input[aria-label="Search mail"]', {"timeout": 60000})
    await asyncio.sleep(3)
    print("  Inbox loaded.")

    # Step 2: Search for emails
    print(f"  Searching: {search_query}")
    search_input = await page.querySelector('input[aria-label="Search mail"]')
    await search_input.click()
    await asyncio.sleep(1)
    await search_input.type(search_query)
    await asyncio.sleep(0.5)
    await page.keyboard.press("Enter")
    await asyncio.sleep(5)
    print("  Search complete.")

    # Step 3: Filter rows by sender keyword and pick the latest
    sender_lower = sender_keyword.lower()
    print(f"  Filtering sender rows containing \"{sender_keyword}\"...")
    result = await page.evaluate(
        """(senderKeyword) => {
            const rows = document.querySelectorAll('tr.zA, tr.zE');
            const matchedRows = [];

            for (let i = 0; i < rows.length; i++) {
                const senderEl = rows[i].querySelector('.yX .yW span[email], .yX .yW .bA4 span, .yX .yW span');
                const senderText = senderEl ? senderEl.textContent : '';
                const rowText = rows[i].innerText || '';

                if (senderText.toLowerCase().includes(senderKeyword) || rowText.toLowerCase().includes(senderKeyword)) {
                    const timeSpan = rows[i].querySelector('td.xW span[title]');
                    const timeTitle = timeSpan ? timeSpan.getAttribute('title') : '';
                    const timestamp = timeTitle ? new Date(timeTitle).getTime() : 0;

                    matchedRows.push({
                        index: i,
                        sender: senderText,
                        time: timeTitle,
                        timestamp: timestamp
                    });
                }
            }

            if (matchedRows.length === 0) return null;

            matchedRows.sort((a, b) => b.timestamp - a.timestamp);

            return {
                total: rows.length,
                matchCount: matchedRows.length,
                latest: matchedRows[0],
                all: matchedRows
            };
        }""",
        sender_lower,
    )

    if not result:
        raise RuntimeError(f"No emails found matching sender \"{sender_keyword}\".")

    print(f"  Found {result['matchCount']} email(s) from \"{sender_keyword}\".")
    for row in result['all']:
        print(f"    - Sender: {row['sender']}, Time: {row['time']}")

    latest = result['latest']
    print(f"  Opening latest: sender='{latest['sender']}', time='{latest['time']}'")

    # Click the latest email row
    await page.evaluate(
        """(idx) => {
            const rows = document.querySelectorAll('tr.zA, tr.zE');
            if (rows[idx]) rows[idx].click();
        }""",
        latest['index'],
    )

    # Step 4: Wait for the email to open
    print("  Waiting for email content to load...")
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

    print(f"  Email body preview: {body_text[:200]}...")

    # Step 6: Extract the code using the pattern
    match = re.search(code_pattern, body_text)
    if match:
        code = match.group(1)
        print(f"  Verification code found: {code}")
        return code

    # Fallback: any standalone 6-digit number
    fallback = re.search(r'\b(\d{6})\b', body_text)
    if fallback:
        code = fallback.group(1)
        print(f"  Verification code (fallback): {code}")
        return code

    raise ValueError(f"Could not find verification code in email body:\n{body_text[:500]}")


# Keep backward compatibility
async def read_godaddy_code(page, timeout: int = 60000) -> str:
    return await read_verification_code(
        page,
        search_query="from:godaddy.com",
        sender_keyword="godaddy",
        code_pattern=r'[Hh]ere is your email verification code[:\s]*(\d{6})',
        timeout=timeout,
    )

"""
Discord Output Formatters  [SHARED — used by Discord bot AND agent fast-lane]
==========================
Converts InboundRouter responses (HTML-formatted for Telegram) to Discord
markdown format. Thin translation layer — all business logic stays in
tg_router.py and tg_format.py.

Design:
  - Telegram uses HTML: <b>bold</b>, <code>mono</code>, <i>italic</i>
  - Discord uses Markdown: **bold**, `mono`, *italic*
  - Telegram uses inline_keyboard buttons with callback_data
  - Discord uses discord.ui.View with discord.ui.Button components
"""

import re
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════
# HTML → Discord Markdown conversion
# ═══════════════════════════════════════════════════════════════════

def html_to_discord(html: str) -> str:
    """
    Convert Telegram HTML subset to Discord markdown.

    Handles:
      <b>text</b>  →  **text**
      <i>text</i>  →  *text*
      <code>text</code>  →  `text`
      <pre>text</pre>  →  ```text```
      <a href="url">text</a>  →  [text](url)
      &amp; &lt; &gt;  →  & < >
    """
    if not html:
        return ""

    text = html

    # Block-level: <pre> → code block
    text = re.sub(r"<pre>(.*?)</pre>", r"```\1```", text, flags=re.DOTALL)

    # Inline: <code> → backtick (must come after <pre>)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)

    # Bold: <b> or <strong>
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)

    # Italic: <i> or <em>
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)

    # Links: <a href="url">text</a>
    text = re.sub(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", text, flags=re.DOTALL)

    # Strip any remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')

    return text


def convert_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a router response from Telegram format to Discord format.

    Input:  {"text": "<b>HTML</b>", "reply_markup": {"inline_keyboard": [...]}, "parse_mode": "HTML"}
    Output: {"content": "**Markdown**", "buttons": [{"label": "...", "custom_id": "..."}]}
    """
    content = html_to_discord(response.get("text", ""))

    # Discord message limit is 2000 chars
    if len(content) > 2000:
        content = content[:1997] + "..."

    result: Dict[str, Any] = {"content": content}

    # Convert inline keyboard to flat button list
    markup = response.get("reply_markup")
    if markup and isinstance(markup, dict):
        keyboard = markup.get("inline_keyboard", [])
        buttons = []
        for row in keyboard:
            for btn in row:
                button_data = {
                    "label": btn.get("text", "?"),
                    "custom_id": btn.get("callback_data", ""),
                }
                # Skip buttons with no callback_data (e.g., URL buttons)
                if btn.get("url"):
                    button_data["url"] = btn["url"]
                    button_data.pop("custom_id", None)
                if button_data.get("custom_id") or button_data.get("url"):
                    buttons.append(button_data)
            # Row separator — Discord allows up to 5 buttons per ActionRow
            if buttons and buttons[-1] != "ROW_BREAK":
                buttons.append("ROW_BREAK")

        # Remove trailing ROW_BREAK
        while buttons and buttons[-1] == "ROW_BREAK":
            buttons.pop()

        if buttons:
            result["buttons"] = buttons

    return result

#!/usr/bin/env python3
"""Generate bounty PDF from README.md with professional styling."""
import markdown
from weasyprint import HTML
from pathlib import Path

README = Path(__file__).parent / "README.md"
OUTPUT = Path(__file__).parent / "BOUNTY_PITCH.pdf"

CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
}
body {
    font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a2e;
}
h1 {
    font-size: 22pt;
    color: #0a0a14;
    border-bottom: 3px solid #00b4d8;
    padding-bottom: 8px;
    margin-top: 30px;
}
h2 {
    font-size: 16pt;
    color: #0a0a14;
    border-bottom: 1px solid #ddd;
    padding-bottom: 4px;
    margin-top: 24px;
}
h3 {
    font-size: 12pt;
    color: #333;
    margin-top: 18px;
}
blockquote {
    border-left: 4px solid #00b4d8;
    padding: 8px 16px;
    margin: 16px 0;
    background: #f0f9ff;
    color: #333;
    font-style: italic;
}
code {
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 9pt;
    background: #f4f4f8;
    padding: 1px 4px;
    border-radius: 3px;
}
pre {
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 8.5pt;
    background: #f4f4f8;
    border: 1px solid #e0e0e8;
    border-radius: 6px;
    padding: 12px 16px;
    overflow-x: auto;
    line-height: 1.4;
    white-space: pre-wrap;
}
pre code {
    background: none;
    padding: 0;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 9.5pt;
}
th {
    background: #0a0a14;
    color: white;
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
}
td {
    padding: 6px 12px;
    border-bottom: 1px solid #e8e8ee;
}
tr:nth-child(even) td {
    background: #fafafe;
}
strong {
    color: #0a0a14;
}
a {
    color: #00b4d8;
    text-decoration: none;
}
ul, ol {
    padding-left: 24px;
}
li {
    margin-bottom: 4px;
}
hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 24px 0;
}
/* Header badge */
.header-badge {
    display: inline-block;
    background: #00b4d8;
    color: white;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 0.05em;
}
"""

md_text = README.read_text()
html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

full_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div style="text-align:center; margin-bottom:30px;">
    <div style="font-size:28pt; font-weight:800; color:#0a0a14; letter-spacing:0.05em;">SPACE LORD</div>
    <div style="font-size:10pt; color:#666; margin-top:4px;">Hedera Hello Future Apex Hackathon 2026 — OpenClaw Bounty Track</div>
    <div style="margin-top:12px;">
        <span style="display:inline-block; background:#00b4d8; color:white; padding:4px 14px; border-radius:4px; font-size:9pt; font-weight:700; letter-spacing:0.05em;">OPENCLAW BOUNTY SUBMISSION</span>
    </div>
</div>
{html_body}
</body>
</html>"""

HTML(string=full_html).write_pdf(str(OUTPUT))
print(f"Generated: {OUTPUT}")

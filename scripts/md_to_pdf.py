#!/usr/bin/env python3
"""Convert a markdown file to a styled PDF with Space Lord branding.
White background, dark text, cyan (#00b4d8) accent colour throughout.
"""
import re
import sys
import markdown
from weasyprint import HTML

def convert(md_path, pdf_path, title="Space Lord"):
    with open(md_path, "r") as f:
        md_text = f.read()

    # Pre-process: convert page-break divs to a marker
    md_text = re.sub(
        r'<div\s+style="page-break-after:\s*always;?">\s*</div>',
        '\n\n<hr class="page-break">\n\n',
        md_text,
    )
    # Strip remaining divs so markdown processes content inside them
    md_text = re.sub(r'<div[^>]*>\s*', '\n', md_text)
    md_text = md_text.replace("</div>", "\n")

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "codehilite", "toc", "attr_list", "md_in_html"],
    )

    # Restore page break markers
    html_body = re.sub(
        r'<hr\s+class="page-break"\s*/?>',
        '<div class="page-break"></div>',
        html_body,
    )
    html_body = html_body.replace(
        '<hr class="page-break">',
        '<div class="page-break"></div>',
    )

    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@page {{
    size: A4;
    margin: 2cm 2.5cm;
    @bottom-center {{
        content: counter(page);
        font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
        font-size: 9pt;
        color: #999;
    }}
}}
@page :first {{
    @bottom-center {{ content: none; }}
}}

body {{
    font-family: -apple-system, 'Helvetica Neue', 'Segoe UI', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.65;
    color: #2a2a3a;
    background: #ffffff;
}}

.page-break {{
    page-break-after: always;
    height: 0; margin: 0; padding: 0; border: none;
}}

/* ── TITLE PAGE ── */
body > h1:first-of-type {{
    font-size: 36pt;
    text-align: center;
    margin-top: 100px;
    margin-bottom: 0.15em;
    border-bottom: none;
    padding-bottom: 0;
    color: #0a0a14;
    letter-spacing: 0.12em;
}}
body > h1:first-of-type + h3 {{
    text-align: center;
    color: #00859e;
    font-size: 14pt;
    font-weight: 600;
    margin-bottom: 1.5em;
}}

/* ── HEADINGS ── */
h1 {{
    font-size: 24pt;
    font-weight: 800;
    color: #0a0a14;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-top: 0.3em;
    margin-bottom: 0.4em;
    border-bottom: 2.5px solid #00b4d8;
    padding-bottom: 0.12em;
}}
h2 {{
    font-size: 15pt;
    font-weight: 700;
    color: #00859e;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-top: 1.6em;
    margin-bottom: 0.45em;
    border-bottom: 1px solid #d0d0d8;
    padding-bottom: 0.1em;
}}
h3 {{
    font-size: 12pt;
    font-weight: 700;
    color: #1a1a2e;
    margin-top: 1.1em;
    margin-bottom: 0.3em;
}}
h4 {{
    font-size: 11pt;
    font-weight: 700;
    color: #00859e;
    margin-top: 0.8em;
    margin-bottom: 0.2em;
}}

/* ── TEXT ── */
p {{
    margin-bottom: 0.65em;
    color: #333;
}}
strong {{
    color: #1a1a2e;
    font-weight: 700;
}}
em {{
    color: #00859e;
}}
a {{
    color: #0088a8;
    text-decoration: none;
}}

/* ── BLOCKQUOTES ── */
blockquote {{
    border-left: 3.5px solid #00b4d8;
    margin: 0.8em 0;
    padding: 0.5em 1em;
    background: #f0f9fb;
    border-radius: 0 6px 6px 0;
}}
blockquote p {{
    color: #2a5a6a;
    font-style: italic;
    margin-bottom: 0.2em;
}}

/* ── TABLES ── */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0.7em 0 1.1em 0;
    font-size: 9.5pt;
}}
th {{
    background: #00b4d8;
    color: #ffffff;
    font-weight: 700;
    text-align: left;
    padding: 7px 9px;
    font-size: 8.5pt;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}}
td {{
    padding: 6px 9px;
    border-bottom: 1px solid #e0e0e8;
    color: #333;
    vertical-align: top;
}}
tr:nth-child(even) {{
    background: #f6f8fa;
}}
/* First column bold for comparison tables */
td:first-child {{
    font-weight: 600;
    color: #1a1a2e;
}}

/* ── CODE ── */
code {{
    font-family: 'SF Mono', 'Fira Code', Consolas, monospace;
    font-size: 9pt;
    background: #f0f4f8;
    color: #00859e;
    padding: 1px 4px;
    border-radius: 3px;
    border: 1px solid #d8dfe6;
}}
pre {{
    background: #f5f7fa;
    border: 1px solid #d8dfe6;
    border-radius: 6px;
    padding: 0.8em;
    overflow-x: auto;
    margin: 0.7em 0;
}}
pre code {{
    background: none;
    border: none;
    padding: 0;
    color: #2a5060;
    font-size: 8.5pt;
    line-height: 1.5;
}}

/* ── LISTS ── */
ul, ol {{
    margin: 0.4em 0 0.8em 1.5em;
    color: #333;
}}
li {{
    margin-bottom: 0.3em;
    font-size: 10.5pt;
}}
li strong {{
    color: #1a1a2e;
}}

/* ── HORIZONTAL RULES ── */
hr {{
    border: none;
    border-top: 1px solid #d0d0d8;
    margin: 1.5em 0;
}}

img {{
    max-width: 100%;
    display: block;
    margin: 0 auto;
}}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    HTML(string=full_html).write_pdf(pdf_path)
    print(f"Created: {pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python md_to_pdf.py input.md output.pdf [title]")
        sys.exit(1)
    title = sys.argv[3] if len(sys.argv) > 3 else "Space Lord"
    convert(sys.argv[1], sys.argv[2], title)

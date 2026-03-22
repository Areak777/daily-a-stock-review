# -*- coding: utf-8 -*-
"""
A股每日复盘 - 邮件发送脚本
从 Markdown 复盘报告生成 HTML 邮件并发送
"""
import os
import sys
import re
import json
import glob
import requests
import argparse
from datetime import datetime


def read_md(filepath):
    """读取 Markdown 文件，支持通配符"""
    files = glob.glob(filepath)
    if not files:
        print(f"ERROR: No file found matching: {filepath}")
        sys.exit(1)
    target = files[0]
    print(f"Reading: {target}")
    with open(target, "r", encoding="utf-8") as f:
        return f.read(), target


def md_table_to_html(table_str):
    """将 Markdown 表格转为 HTML 表格"""
    lines = [l.strip() for l in table_str.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return ""
    headers = [c.strip() for c in lines[0].split("|")[1:-1]]
    html = "<table style='width:100%;border-collapse:collapse;margin:12px 0;font-size:13px'>"
    html += "<tr style='background:#1a1a2e'>"
    for h in headers:
        html += f"<th style='padding:8px 10px;text-align:left;border-bottom:2px solid #e94560;font-weight:600;color:#fff'>{h}</th>"
    html += "</tr>"
    for i, line in enumerate(lines[2:]):
        cells = [c.strip() for c in line.split("|")[1:-1]]
        bg = "#f8f9fa" if i % 2 == 0 else "#fff"
        html += f"<tr style='background:{bg};border-bottom:1px solid #eee'>"
        for c in cells:
            # 涨红跌绿
            color = "#e74c3c" if re.search(r'(\+|涨|红|🔥)', c) else "#27ae60" if re.search(r'(-|跌|绿|❄️)', c) else "#333"
            html += f"<td style='padding:8px 10px;color:{color}'>{c}</td>"
        html += "</tr>"
    html += "</table>"
    return html


def md_to_email_html(md_content):
    """将 A股复盘 Markdown 报告转为邮件 HTML"""
    lines = md_content.split("\n")

    # Extract title
    title = "A股每日复盘报告"
    for l in lines:
        if l.startswith("# "):
            title = l.replace("# ", "").strip()
            break

    # Extract date info from meta
    subtitle = ""
    for l in lines:
        if l.startswith(">") and ("生成时间" in l or "数据来源" in l):
            subtitle = l.replace(">", "").strip()
            break

    # Parse all sections (## level)
    sections = []
    current_section = None
    current_content = []

    for l in lines:
        if re.match(r'^##\s+', l) and not l.startswith('## '):
            pass
        if re.match(r'^##\s+', l):
            if current_section is not None:
                sections.append((current_section, current_content))
            current_section = l.replace("## ", "").strip()
            current_content = []
        elif l.startswith("# ") or l.startswith(">") or l.strip() == "---":
            continue
        elif current_section is not None:
            current_content.append(l)

    if current_section is not None:
        sections.append((current_section, current_content))

    # Section color scheme (dark theme accent)
    section_colors = {
        "一": "#e94560",
        "二": "#0f3460",
        "三": "#f39c12",
        "四": "#e94560",
        "五": "#8e44ad",
        "六": "#2980b9",
        "七": "#d35400",
        "八": "#16a085",
    }

    def get_color(name):
        for k, v in section_colors.items():
            if k in name[:3]:
                return v
        return "#2c3e50"

    body_html = ""
    for sec_title, sec_lines in sections:
        color = get_color(sec_title)
        content_html = ""

        # Handle ### subsections
        subsections = []
        cur_sub = None
        cur_sub_lines = []
        for l in sec_lines:
            if re.match(r'^###\s+', l):
                if cur_sub is not None:
                    subsections.append((cur_sub, cur_sub_lines))
                cur_sub = l.replace("### ", "").strip()
                cur_sub_lines = []
            elif cur_sub is not None:
                cur_sub_lines.append(l)
            else:
                content_html += format_line(l)
        if cur_sub is not None:
            subsections.append((cur_sub, cur_sub_lines))

        # Convert subsections
        for sub_title, sub_lines in subsections:
            # Check for tables
            joined = "\n".join(sub_lines)
            if "|" in joined:
                pre_text = []
                in_table = False
                table_lines = []
                table_blocks = []
                for l in sub_lines:
                    stripped = l.strip()
                    if stripped.startswith("|"):
                        if not in_table:
                            in_table = True
                            table_lines = [stripped]
                        else:
                            table_lines.append(stripped)
                    else:
                        if in_table:
                            table_blocks.append("\n".join(table_lines))
                            table_lines = []
                            in_table = False
                        pre_text.append(l)
                if in_table:
                    table_blocks.append("\n".join(table_lines))
                for t in pre_text:
                    content_html += format_line(t)
                for tb in table_blocks:
                    content_html += md_table_to_html(tb)
            else:
                for l in sub_lines:
                    content_html += format_line(l)

        if content_html.strip():
            body_html += f"""
            <div style="margin-bottom:20px">
                <h2 style="font-size:17px;color:{color};margin:0 0 12px;padding-bottom:8px;border-bottom:2px solid {color};border-radius:2px">{sec_title}</h2>
                <div style="font-size:14px;line-height:1.8">{content_html}</div>
            </div>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0f0f1a;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f1a;padding:20px 0">
<tr><td align="center">
<table width="700" cellpadding="0" cellspacing="0" style="background:#1a1a2e;border-radius:12px;overflow:hidden;margin:0 16px;border:1px solid #333">
    <tr><td style="background:linear-gradient(135deg,#0f3460,#1a1a2e);padding:28px 24px;text-align:center">
        <h1 style="color:#fff;font-size:22px;margin:0 0 6px">📊 {title}</h1>
        <p style="color:rgba(255,255,255,.6);font-size:12px;margin:0">{subtitle}</p>
    </td></tr>
    <tr><td style="padding:24px 24px">
        {body_html}
    </td></tr>
    <tr><td style="padding:16px 24px;text-align:center;font-size:11px;color:#666;border-top:1px solid #333">
        由 GitHub Actions 自动推送 | 数据来源公开搜索 | ⚠️ 仅供参考，不构成投资建议
    </td></tr>
</table>
</td></tr>
</table>
</body></html>"""
    return html


def format_line(l):
    """将单行 Markdown 转为 HTML 片段"""
    stripped = l.strip()
    if not stripped:
        return ""
    if stripped.startswith("- "):
        return f'<li style="margin:4px 0;padding-left:4px;color:#ccc">{stripped[2:]}</li>'
    elif stripped.startswith("  - "):
        return f'<li style="margin:2px 0 2px 16px;color:#999;font-size:13px">{stripped[4:]}</li>'
    elif re.match(r'^\d+\.\s', stripped):
        return f'<p style="margin:6px 0;color:#ccc;line-height:1.7">{stripped}</p>'
    elif stripped.startswith("**") and stripped.endswith("**"):
        return f'<p style="margin:8px 0 4px;font-weight:600;color:#eee">{stripped}</p>'
    elif stripped.startswith("**") or "**" in stripped:
        # Bold text inline
        converted = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#eee">\1</strong>', stripped)
        return f'<p style="margin:4px 0;color:#ccc;line-height:1.6">{converted}</p>'
    elif stripped:
        return f'<p style="margin:4px 0;color:#ccc;line-height:1.6">{stripped}</p>'
    return ""


def send_email(api_key, to_email, subject, html_content, from_email="onboarding@resend.dev"):
    """通过 Resend API 发送邮件"""
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "from": f"A股复盘 <{from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        },
        timeout=30,
    )
    return resp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--md", required=True, help="Markdown report file path")
    args = parser.parse_args()

    api_key = os.environ.get("RESEND_API_KEY", "")
    to_email = os.environ.get("EMAIL_TO", "")
    from_email = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")

    if not api_key or not to_email:
        print("ERROR: RESEND_API_KEY and EMAIL_TO must be set")
        sys.exit(1)

    md_content, actual_path = read_md(args.md)
    today_str = datetime.now().strftime("%Y年%m月%d日")

    html = md_to_email_html(md_content)

    # Save HTML for preview
    html_path = actual_path.replace(".md", "_email.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Email HTML saved: {html_path}")

    # Send email
    subject = f"A股每日复盘 {today_str}"
    print(f"Sending email to {to_email}...")
    resp = send_email(api_key, to_email, subject, html, from_email)

    if resp.status_code == 200:
        print(f"Email sent successfully! ID: {resp.json().get('id')}")
    else:
        print(f"Email failed: {resp.status_code} {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()

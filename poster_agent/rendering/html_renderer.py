"""Render validated poster content into a standalone printable HTML document."""

from __future__ import annotations

from html import escape

from poster_agent.design.themes import THEMES


def render_poster(poster: dict[str, object]) -> str:
    theme = THEMES[str(poster["theme"])]
    sections = poster["sections"]
    section_html = []
    for index, section in enumerate(sections, 1):
        bullets = "".join(f"<li>{escape(item)}</li>" for item in section["bullets"])
        body = f"<p>{escape(section['body'])}</p>" if section["body"] else ""
        section_html.append(
            f'<section class="card card-{index}"><span class="number">{index:02}</span>'
            f"<h2>{escape(section['heading'])}</h2>{body}<ul>{bullets}</ul></section>"
        )
    audience = f'<span>{escape(poster["audience"])}</span>' if poster["audience"] else ""
    poster_type = f'<span>{escape(poster["poster_type"])}</span>' if poster["poster_type"] else ""
    visual = f'<p class="visual">{escape(poster["visual_metaphor"])}</p>' if poster["visual_metaphor"] else ""
    call_to_action = f'<p class="cta">{escape(poster["call_to_action"])}</p>' if poster["call_to_action"] else ""
    sources = poster["sources"]
    source_html = (
        '<footer class="sources"><strong>Sources / notes</strong><ul>'
        + "".join(f"<li>{escape(source)}</li>" for source in sources)
        + "</ul></footer>"
        if sources
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(poster['title'])}</title>
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;min-height:100%;font-family:Arial,Helvetica,sans-serif;color:{theme['ink']}}}
body{{background:#e8e8e8;padding:24px}}
.poster{{--paper:{theme['paper']};--ink:{theme['ink']};--accent:{theme['accent']};--soft:{theme['soft']};
position:relative;overflow:hidden;max-width:900px;min-height:1165px;margin:0 auto;padding:64px;
background:var(--paper);color:var(--ink);box-shadow:0 12px 48px #0002;display:flex;flex-direction:column}}
.poster:before{{content:"";position:absolute;width:390px;height:390px;border:2px solid var(--accent);
border-radius:50%;right:-210px;top:110px;opacity:.18}}
.meta{{display:flex;gap:10px;flex-wrap:wrap;text-transform:uppercase;letter-spacing:.13em;font-size:11px;font-weight:700;color:var(--accent)}}
.meta span{{padding:7px 10px;border:1px solid currentColor}}
h1{{position:relative;max-width:740px;font-size:clamp(48px,8vw,90px);line-height:.94;letter-spacing:-.055em;margin:45px 0 14px}}
.subtitle{{max-width:660px;font-family:Georgia,serif;font-size:24px;line-height:1.3;margin:0}}
.visual{{font-size:12px;letter-spacing:.04em;margin:24px 0 0;color:var(--accent);font-weight:700}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:42px}}
.card{{position:relative;padding:22px 22px 18px;background:var(--soft);border-top:4px solid var(--accent);break-inside:avoid}}
.number{{font-size:10px;font-weight:800;letter-spacing:.16em;color:var(--accent)}}
h2{{font-size:23px;line-height:1.05;margin:10px 0}}
.card p,.card li{{font-size:14px;line-height:1.38}}
.card p{{margin:0 0 10px}}
.card ul{{padding-left:18px;margin:8px 0 0}}
.card li+li{{margin-top:5px}}
.cta{{margin:auto 0 0;padding:20px 24px;background:var(--accent);color:white;font-size:20px;font-weight:800;line-height:1.2}}
.sources{{margin-top:20px;font-size:10px;line-height:1.3}}
.sources ul{{display:flex;gap:10px 22px;flex-wrap:wrap;padding-left:16px}}
@page{{size:A3 portrait;margin:0}}
@media(max-width:650px){{body{{padding:0}}.poster{{min-height:100vh;padding:30px 22px}}.grid{{grid-template-columns:1fr}}h1{{font-size:56px}}}}
@media print{{html,body{{width:297mm;height:420mm;background:white}}body{{padding:0}}.poster{{width:297mm;height:420mm;min-height:0;max-width:none;margin:0;padding:17mm;box-shadow:none;-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style>
</head>
<body>
<main class="poster">
<div class="meta">{poster_type}{audience}</div>
<h1>{escape(poster['title'])}</h1>
<p class="subtitle">{escape(poster['subtitle'])}</p>
{visual}
<div class="grid">{''.join(section_html)}</div>
{call_to_action}
{source_html}
</main>
</body>
</html>"""

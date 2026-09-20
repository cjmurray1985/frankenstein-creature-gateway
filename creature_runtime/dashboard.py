from __future__ import annotations

import html
from datetime import datetime
from typing import Any


DASHBOARD_CSS = r"""
:root { color-scheme: dark; --canvas:#0b0c0c; --surface:#141514; --raised:#1a1b19; --ink:#eee9de; --muted:#aaa398; --faint:#77736c; --brass:#b9a477; --bright:#d3bf8d; --danger:#a65349; --rule:#34342f; --serif:Georgia,"Times New Roman",serif; --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
* { box-sizing:border-box; }
html { background:var(--canvas); }
body { margin:0; min-height:100vh; background:radial-gradient(circle at 85% -10%,rgba(185,164,119,.08),transparent 28rem),var(--canvas); color:var(--ink); font:17px/1.62 var(--serif); -webkit-font-smoothing:antialiased; }
a { color:inherit; }
a:focus-visible,button:focus-visible,input:focus-visible { outline:2px solid var(--bright); outline-offset:3px; }
.shell { width:min(100% - 36px,760px); margin:0 auto; padding:42px 0 88px; }
.masthead { border-bottom:1px solid var(--rule); padding-bottom:28px; margin-bottom:26px; }
.eyebrow,.date,.speaker,.record-number,.meta,.privacy { font-family:var(--sans); text-transform:uppercase; letter-spacing:.13em; }
.eyebrow { color:var(--brass); font-size:11px; font-weight:650; }
h1 { max-width:11ch; margin:14px 0 12px; font-size:clamp(2.7rem,13vw,5.3rem); font-weight:400; letter-spacing:-.035em; line-height:.93; text-wrap:balance; }
.lede { max-width:34rem; margin:0; color:var(--muted); font-size:1.02rem; }
.records { display:grid; gap:12px; }
.record { position:relative; display:grid; grid-template-columns:1fr auto; gap:7px 18px; min-height:142px; padding:20px 21px 19px; overflow:hidden; border:1px solid var(--rule); border-radius:3px; background:linear-gradient(135deg,var(--raised),var(--surface)); color:inherit; text-decoration:none; transition:border-color .16s ease,transform .16s ease; }
.record::before { content:""; position:absolute; inset:0 auto 0 0; width:3px; background:var(--brass); opacity:.72; }
.record:hover { border-color:#625b4c; transform:translateY(-1px); }
.record > * { min-width:0; overflow-wrap:anywhere; }
.date { grid-column:1; color:var(--brass); font-size:10px; }
.record-number { grid-column:2; grid-row:1; color:var(--faint); font-size:10px; }
.summary { grid-column:1/-1; margin:5px 0 3px; font-size:1.13rem; line-height:1.42; text-wrap:pretty; }
.meta { grid-column:1/-1; color:var(--muted); font-size:10px; }
.empty { padding:28px 22px; border:1px solid var(--rule); background:var(--surface); color:var(--muted); }
.back { display:inline-flex; gap:8px; align-items:center; margin-bottom:32px; color:var(--bright); font:600 12px/1 var(--sans); letter-spacing:.1em; text-decoration:none; text-transform:uppercase; }
.back span { font-size:18px; font-weight:400; }
.conversation-head { margin-bottom:34px; }
.conversation-head h1 { margin-bottom:24px; }
.conversation-summary { margin:0; padding:17px 19px; border:1px solid var(--rule); border-left:3px solid var(--brass); background:var(--surface); color:#d5cfc3; line-height:1.48; }
.transcript { display:grid; gap:29px; }
.exchange { display:grid; gap:10px; }
.utterance { margin:0; padding:18px 19px 20px; border:1px solid var(--rule); }
.speaker { display:block; margin-bottom:8px; color:var(--muted); font-size:10px; font-weight:700; }
.visitor { margin-right:9%; background:#171817; }
.creature { margin-left:5%; border-color:#463f33; background:#151412; font-size:1.08rem; }
.creature .speaker { display:flex; align-items:center; gap:8px; color:var(--brass); }
.emotion-badge { font-size:10px; line-height:1; letter-spacing:.11em; }
.emotion-hopeful { color:#a9bd7c; }
.emotion-engaged,.emotion-curious { color:#80b7ba; }
.emotion-wary { color:#d0a55f; }
.emotion-hurt { color:#c78d91; }
.emotion-angry { color:#db756a; }
.emotion-withdrawn { color:#aaa6bd; }
.emotion-neutral { color:#aaa398; }
.still { display:block; width:100%; height:auto; margin:0 0 34px; border:1px solid var(--rule); }
.audio-player { width:100%; margin:0 0 34px; accent-color:var(--brass); }
.danger-zone { margin-top:64px; padding-top:24px; border-top:1px solid var(--rule); }
.danger-zone h2 { margin:0 0 5px; font:650 12px/1.3 var(--sans); letter-spacing:.1em; text-transform:uppercase; }
.danger-zone p { margin:0 0 18px; color:var(--muted); font-size:.9rem; }
.delete-form { display:grid; gap:11px; }
.delete-form label { color:var(--muted); font:13px/1.45 var(--sans); }
.delete-form strong { color:var(--ink); }
input { width:100%; margin-top:8px; padding:13px 14px; border:1px solid #4a4842; border-radius:3px; background:#0f1010; color:var(--ink); font:16px var(--sans); }
button { justify-self:start; min-height:44px; padding:11px 16px; border:1px solid #75413b; border-radius:3px; background:#2b1715; color:#ecd9d4; font:650 13px var(--sans); cursor:pointer; }
button:hover { background:#3a1c19; border-color:var(--danger); }
.privacy { margin-top:54px; color:var(--faint); font-size:9px; }
@media (min-width:640px) { .shell{padding-top:68px}.record{padding:24px 27px 23px}.delete-form{grid-template-columns:minmax(260px,1fr) auto;align-items:end}button{margin-bottom:1px} }
@media (prefers-reduced-motion:reduce) { .record{transition:none} }
"""


def _head(title: str) -> str:
    return ('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="theme-color" content="#0b0c0c"><title>{html.escape(title)}</title>'
            '<link rel="stylesheet" href="/assets/dashboard.css">')


def _emotion_class(value: str) -> str:
    known = {"hopeful", "engaged", "curious", "wary", "hurt", "angry", "withdrawn"}
    return value if value in known else "neutral"


def render_dashboard(records: list[dict[str, Any]]) -> str:
    cards = []
    for index, record in enumerate(records, start=1):
        rid = html.escape(str(record["record_id"]), quote=True)
        started = datetime.fromisoformat(record["started_at"]).astimezone().strftime("%b %d, %Y · %I:%M %p")
        summary = html.escape(str(record["emotional_summary"]))
        turns, visitors = int(record["turn_count"]), int(record["group_size"])
        turn_label = "turn" if turns == 1 else "turns"
        visitor_label = "visitor" if visitors == 1 else "visitors"
        cards.append(f'<a class="record" href="/records/{rid}"><span class="date">{started}</span>'
                     f'<span class="record-number">No. {index:03d}</span><p class="summary">{summary}</p>'
                     f'<span class="meta">{turns} {turn_label} · {visitors} {visitor_label}</span></a>')
    content = "".join(cards) or '<p class="empty">No conversations have been archived.</p>'
    return ('<!doctype html><html lang="en"><head>' + _head("Creature Archive") + '</head><body>'
            '<main class="shell"><header class="masthead"><span class="eyebrow">Private collection · Christopher only</span>'
            '<h1>Creature Archive</h1><p class="lede">Completed encounters, preserved apart from the Creature’s own speech and memory.</p>'
            f'</header><section class="records" aria-label="Archived conversations">{content}</section>'
            '<p class="privacy">Encrypted at rest · Available only within your private tailnet</p></main></body></html>')


def render_record(record: dict[str, Any]) -> str:
    rid = html.escape(str(record["record_id"]), quote=True)
    summary = html.escape(str(record["emotional_summary"]))
    turns = []
    for turn in record.get("turns", []):
        visitor = html.escape(str(turn["visitor_text"]))
        creature = html.escape(str(turn["creature_reply"]))
        raw_emotion = str(turn["emotion"]).strip().lower()
        emotion = html.escape(raw_emotion)
        emotion_class = _emotion_class(raw_emotion)
        turns.append(f'<article class="exchange"><p class="utterance visitor"><b class="speaker">Visitor</b>{visitor}</p>'
                     f'<p class="utterance creature"><b class="speaker">The Creature '
                     f'<span class="emotion-badge emotion-{emotion_class}">{emotion}</span></b>{creature}</p></article>')
    image = (f'<img class="still" src="/records/{rid}/image" alt="Still captured after this conversation">'
             if record.get("still_image_path") else "")
    audio = (f'<audio class="audio-player" controls preload="metadata" src="/records/{rid}/audio">'
             'Your browser cannot play this Creature reply.</audio>' if record.get("speech_audio_present") else "")
    return ('<!doctype html><html lang="en"><head>' + _head("Conversation · Creature Archive") + '</head><body>'
            '<main class="shell"><a class="back" href="/"><span aria-hidden="true">←</span> Archive</a>'
            '<header class="conversation-head"><span class="eyebrow">Encounter record</span><h1>Conversation</h1>'
            f'<p class="conversation-summary">{summary}</p></header>{image}{audio}'
            f'<section class="transcript" aria-label="Conversation transcript">{"".join(turns)}</section>'
            f'<section class="danger-zone"><h2>Remove from archive</h2><p>This permanently deletes the conversation and any attached still.</p>'
            f'<form class="delete-form" method="post" action="/records/{rid}/delete"><label>Type <strong>{rid}</strong> to confirm'
            '<input required autocomplete="off" autocapitalize="none" spellcheck="false" name="confirm"></label>'
            '<button type="submit">Delete conversation</button></form></section>'
            '<p class="privacy">Encrypted at rest · Available only within your private tailnet</p></main></body></html>')

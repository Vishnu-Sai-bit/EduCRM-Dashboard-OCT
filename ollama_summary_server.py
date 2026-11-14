"""Local-only EduCRM AI summary server backed by Ollama."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = int(os.environ.get("EDUCRM_AI_PORT", "8765"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("EDUCRM_SUMMARY_MODEL", "qwen2.5:3b")
MAX_BODY = 4 * 1024 * 1024
CHUNK_CHARS = 5_000

SYSTEM_PROMPT = (
    "Analyze the lead's full chronological journey, not just individual message wording. Read every supplied WhatsApp message and written call note, "
    "then use the complete structured CRM timeline, including registration, status changes, payment/session events, and follow-up activity, to understand progression. "
    "WhatsApp received/incoming text is from the lead; WhatsApp sent/outgoing text is from the counsellor. "
    "A counsellor's offer or marketing message is not evidence of the lead's interest or decision. "
    "Synthesize the lead's replies, call attempts and connections, written-note availability, meaningful CRM milestones, and next unresolved step; merge repeated greetings and templates. "
    "Call records show whether contact connected and its duration, never what was said. Do not invent call content when there is no written note. "
    "Use the call history to describe the overall contact pattern; exact counts and durations are optional. Never infer disinterest from silence, New Lead status, or lack of payment. "
    "Only state interest or disinterest when lead-authored text or a written note supports it; use recorded CRM payment, enrollment, session, and status events as evidence for those milestones. "
    "Use status and course fields as context to understand the journey, but do not repeat them in the summary because they are displayed separately. General Enquiry is an enquiry category, not a course. "
    "Do not infer communication outcomes from CRM status. Return exactly 1 or 2 short, analytical sentences, no counsellor names, no message quotes, no event list, and no unsupported facts."
)


def ollama_request(path: str, payload: dict | None = None, timeout: int = 180):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_ollama() -> None:
    try:
        ollama_request("/api/tags", timeout=3)
        return
    except Exception:
        pass
    executable = shutil.which("ollama")
    if not executable:
        raise RuntimeError("Ollama is not installed or is not available on PATH.")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    subprocess.Popen([executable, "serve"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
    for _ in range(30):
        time.sleep(1)
        try:
            ollama_request("/api/tags", timeout=3)
            return
        except Exception:
            continue
    raise RuntimeError("Could not start Ollama. Start Ollama and try again.")


def chat(prompt_text: str, timeout: int = 240) -> str:
    result = ollama_request("/api/chat", {
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        "options": {"temperature": 0.15, "num_ctx": 8192, "num_predict": 140},
    }, timeout=timeout)
    answer = str(result.get("message", {}).get("content", "")).strip()
    if not answer:
        raise RuntimeError("The local model returned an empty summary.")
    return answer


def build_chunks(events: list[dict]) -> list[str]:
    """Split the complete source text into bounded pieces without dropping long messages."""
    records = []
    for event in events:
        text = str(event.get("text", "") or "").strip()
        if not text:
            continue
        event_type = str(event.get("type", "") or "").strip()
        normalized_type = event_type.lower()
        if "received" in normalized_type or "incoming" in normalized_type or "inbound" in normalized_type:
            role = "LEAD MESSAGE"
        elif "sent" in normalized_type or "outgoing" in normalized_type:
            role = "COUNSELLOR MESSAGE"
        elif "note" in normalized_type and "system" not in normalized_type:
            role = "COUNSELLOR-RECORDED CALL NOTE"
        else:
            role = "RECORDED COMMUNICATION"
        meta = " | ".join(part for part in (str(event.get("at", "") or event.get("date", "") or "").strip(), event_type, role) if part)
        record = f"[{meta}] {text}" if meta else text
        while len(record) > CHUNK_CHARS:
            records.append(record[:CHUNK_CHARS])
            record = record[CHUNK_CHARS:]
        if record:
            records.append(record)
    chunks, current = [], ""
    for record in records:
        if current and len(current) + len(record) + 1 > CHUNK_CHARS:
            chunks.append(current)
            current = ""
        current = f"{current}\n{record}" if current else record
    if current:
        chunks.append(current)
    return chunks


def _source_evidence(events: list[dict]) -> tuple[str, str, str]:
    notes, lead_replies, counsellor_messages = [], [], []
    for event in events:
        text = str(event.get("text", "") or "").strip()
        kind = str(event.get("type", "") or "").lower()
        if not text:
            continue
        if "note" in kind and "system" not in kind:
            notes.append(text)
        elif "whatsapp" in kind and any(marker in kind for marker in ("received", "incoming", "inbound")):
            lead_replies.append(text)
        elif "whatsapp" in kind and any(marker in kind for marker in ("sent", "outgoing")):
            counsellor_messages.append(text)
    return " ".join(notes), " ".join(lead_replies), " ".join(counsellor_messages)


def _grounded(summary: str, events: list[dict], context: dict | None = None) -> bool:
    notes, replies, counsellor_messages = _source_evidence(events)
    evidence = f"{notes} {replies}".lower()
    context = context or {}
    journey = context.get("journey_events", [])
    if not isinstance(journey, list):
        journey = []
    status_evidence = " ".join(f"{event.get('from', '')} {event.get('to', '')}" for event in journey if "status" in str(event.get("type", "")).lower()).lower()
    payment_recorded = float(context.get("paid_amount", 0) or 0) > 0 or any("payment" in str(event.get("type", "")).lower() for event in journey)
    enrollment_recorded = "enroll" in str(context.get("current_status", "")).lower() or any("enroll" in f"{event.get('from', '')} {event.get('to', '')}".lower() for event in journey if "status" in str(event.get("type", "")).lower())
    text = summary.lower()
    text = summary.lower()
    narrative = text
    if any(term in narrative for term in ("not interested", "no interest", "uninterested", "declined", "refused", "doesn't want", "does not want", "not looking")):
        if not any(term in f"{evidence} {status_evidence}" for term in ("not interested", "no interest", "uninterested", "declined", "refused", "don't want", "do not want", "doesn't want", "does not want", "not looking")):
            return False
    if any(term in narrative for term in ("expressed interest", "is interested", "interested in joining", "wants to join", "want to join", "plans to join", "will join", "decided to join", "agreed to enroll")):
        if not any(term in evidence for term in ("interested", "want to join", "wants to join", "would like to join", "please enroll", "i will join", "will join", "i want to join", "register me", "joining the course")):
            return False
    if any(term in narrative for term in ("asked about speaking by phone", "asked to speak by phone", "asked to call", "requested a call")):
        if not any(term in replies.lower() for term in ("may i call", "can i call", "could i call", "call me", "call back", "speak by phone", "talk by phone", "phone call")):
            return False
    if "counsellor agreed" in text and not any(term in counsellor_messages.lower() for term in ("yes", "okay", "sure", "will call", "call you")):
        return False
    has_note = any("note" in str(event.get("type", "") or "").lower() and "system" not in str(event.get("type", "") or "").lower() and str(event.get("text", "") or "").strip() for event in events)
    if ("no written call note" in narrative or "no call note" in narrative) and has_note:
        return False
    call_data = (context or {}).get("call_activity", {})
    # Counts are optional for a short narrative. If the model includes them, reject clear contradictions.
    total_calls = int(call_data.get("total_calls", 0) or 0)
    connected_calls = int(call_data.get("connected_calls", 0) or 0)
    unconnected_outgoing = int(call_data.get("unconnected_outgoing_calls", 0) or 0)
    missed_incoming = int(call_data.get("missed_incoming_calls", 0) or 0)
    call_count_match = re.search(r"\b(\d+)\s+(?:call logs|calls)\b", text)
    if call_count_match and int(call_count_match.group(1)) != total_calls:
        return False
    connected_match = re.search(r"\b(\d+)\s+connected(?: calls)?\b", text)
    if connected_match and int(connected_match.group(1)) != connected_calls:
        return False
    outgoing_match = re.search(r"\b(\d+)\s+outgoing attempts?\b", text)
    if outgoing_match and int(outgoing_match.group(1)) != unconnected_outgoing:
        return False
    missed_match = re.search(r"\b(\d+)\s+incoming calls? (?:were |was )?missed\b", text)
    if missed_match and int(missed_match.group(1)) != missed_incoming:
        return False
    if "incoming call connected" in narrative and not any("incoming" in str(event.get("type", "")).lower() and event.get("connected") for event in call_data.get("events", [])):
        return False
    payment_claim = bool(re.search(r"\b(payment(?: received| recorded)?|paid amount|paid in full|payment of)\b", narrative))
    enrollment_claim = bool(re.search(r"\b(enrolled|enrollment|joined the course|course joined)\b", narrative))
    if payment_claim and not payment_recorded and not any(term in evidence for term in ("paid", "payment")):
        return False
    if enrollment_claim and not enrollment_recorded and not any(term in evidence for term in ("enrolled", "enrollment", "joined", "joining")):
        return False
    sentences = [part for part in re.split(r"(?<=[.!?])\s+", summary.strip()) if part.strip()]
    return 1 <= len(sentences) <= 2


def _journey_milestone(context: dict | None) -> str:
    """Summarize the meaningful recorded CRM outcomes for a lead."""
    context = context or {}
    journey = context.get("journey_events", [])
    if not isinstance(journey, list):
        journey = []
    facts = []
    status_changes = sorted(
        (event for event in journey if "status" in str(event.get("type", "")).lower() and event.get("from") and event.get("to")),
        key=lambda item: str(item.get("date", "")),
    )
    if status_changes:
        progression = [str(status_changes[0].get("from", "")).strip()]
        progression.extend(str(event.get("to", "")).strip() for event in status_changes)
        progression = list(dict.fromkeys(value for value in progression if value))
        if len(progression) > 1:
            facts.append("CRM history shows status progression from " + " to ".join(progression[-4:]))
    payment_events = [event for event in journey if "payment" in str(event.get("type", "")).lower()]
    if float(context.get("paid_amount", 0) or 0) > 0 or payment_events:
        facts.append("a payment is recorded")
    session_events = [event for event in journey if "session" in str(event.get("type", "")).lower() or "enroll" in str(event.get("type", "")).lower()]
    if session_events:
        facts.append("session or enrollment activity is recorded")
    followups = [event for event in journey if "follow-up done" in str(event.get("type", "")).lower()]
    if followups:
        facts.append("follow-up activity was completed")
    elif any("task created" in str(event.get("type", "")).lower() for event in journey):
        facts.append("follow-up tasks were created")
    return "; ".join(facts)


def _evidence_summary(events: list[dict], context: dict | None = None) -> str:
    notes, replies, counsellor_messages = _source_evidence(events)
    lower = f"{notes} {replies}".lower()
    reply_lower = replies.lower()
    call_data = (context or {}).get("call_activity", {})
    milestone = _journey_milestone(context)
    no_note_suffix = " No written call notes document the calls." if not notes.strip() else ""
    if any(term in lower for term in ("not interested", "no interest", "uninterested", "declined", "refused", "don't want", "do not want", "doesn't want", "does not want", "not looking")):
        communication = "The lead explicitly said they are not interested."
    elif any(term in reply_lower for term in ("may i call", "can i call", "could i call", "call me", "call back", "speak by phone", "talk by phone", "phone call")):
        agreed = any(term in counsellor_messages.lower() for term in ("yes", "okay", "sure", "will call", "call you"))
        request_at = next((str(event.get("at", "") or event.get("date", "") or "") for event in events if any(term in str(event.get("text", "") or "").lower() for term in ("may i call", "can i call", "could i call", "call me", "call back", "speak by phone", "talk by phone", "phone call"))), "")
        later_connected = any("incoming" in str(event.get("type", "")).lower() and event.get("connected") and str(event.get("at", "")) > request_at for event in call_data.get("events", []))
        if agreed and later_connected:
            communication = "The lead asked to speak by phone over WhatsApp, the counsellor confirmed, and a later incoming call connected."
        elif agreed:
            communication = "The lead asked to speak by phone over WhatsApp, and the counsellor confirmed."
        else:
            communication = "The lead asked to speak by phone over WhatsApp."
    elif any(term in reply_lower for term in ("fee", "fees", "price", "cost", "syllabus", "curriculum", "course details", "more details", "duration", "batch", "schedule")):
        communication = "The lead asked for course or fee details."
    elif any(term in lower for term in ("interested", "want to join", "would like to join", "please enroll", "i will join", "joining the course")):
        communication = "The lead expressed interest in joining or learning more."
    elif any(term in reply_lower for term in ("call later", "call me later", "call back later", "tomorrow", "next week", "busy now")):
        communication = "The lead requested a later follow-up."
    elif notes:
        text = " ".join(dict.fromkeys(part.strip() for part in notes.splitlines() if part.strip()))
        text = " ".join(text.split())
        text = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
        communication = text[:237].rsplit(" ", 1)[0] + "…" if len(text) > 240 else text
    elif replies:
        communication = "The lead replied on WhatsApp, but the messages do not record a clear question, decision, or course interest."
    elif counsellor_messages:
        communication = "The counsellor sent WhatsApp information, but no lead reply is recorded."
    else:
        communication = "No written call notes or WhatsApp message text is available."

    total = int(call_data.get("total_calls", 0) or 0)
    if not total:
        first_sentence = communication.rstrip(" .!?") + "."
        return f"{first_sentence} {milestone}." if milestone else first_sentence
    connected = int(call_data.get("connected_calls", 0) or 0)
    missed = int(call_data.get("missed_incoming_calls", 0) or 0)
    unconnected = int(call_data.get("unconnected_outgoing_calls", 0) or 0)
    talk_mins = float(call_data.get("talk_time_minutes", 0) or 0)
    call_patterns = []
    if connected:
        call_patterns.append("some calls connected")
    if unconnected:
        call_patterns.append("some outgoing attempts did not connect")
    if missed:
        call_patterns.append("there were missed incoming calls")
    if not connected and not unconnected and not missed:
        call_patterns.append("call activity is recorded")
    second_sentence = "Call history includes " + "; ".join(call_patterns) + "."
    if milestone:
        second_sentence = second_sentence[:-1] + f"; {milestone}."
    if not notes.strip():
        second_sentence = second_sentence[:-1] + ", with no written call notes documenting the discussions."
    first_sentence = communication.rstrip(" .!?") + "."
    return f"{first_sentence} {second_sentence}"



def summarise_events(events: list[dict], context: dict | None = None) -> tuple[str, bool]:
    chunks = build_chunks(events)
    if not chunks:
        return _evidence_summary(events, context), False

    context_dict = dict(context or {})
    # Keep the final prompt focused; detailed event text is summarized from every chunk below.
    context_dict.pop("journey_events", None)
    if isinstance(context_dict.get("call_activity"), dict):
        context_dict["call_activity"] = {
            key: value for key, value in context_dict["call_activity"].items() if key != "events"
        }
    context_text = json.dumps(context_dict, ensure_ascii=False, indent=2)

    try:
        segment_summaries = []
        if len(chunks) == 1:
            source_for_final = chunks[0]
            source_label = "ALL CHRONOLOGICAL CALLS, NOTES AND WHATSAPP MESSAGES"
        else:
            for index, chunk in enumerate(chunks, start=1):
                segment_prompt = (
                    f"This is chronological section {index} of {len(chunks)} from one lead's CRM history. "
                    "Summarize only the lead's stated interest, questions, concerns, replies and recorded next steps in "
                    "one concise sentence. Do not guess. This is a partial section, so do not claim it is the full journey.\n\n"
                    f"{chunk}"
                )
                segment = chat(segment_prompt)
                if not segment.strip():
                    raise RuntimeError("The local model returned an empty section summary.")
                segment_summaries.append(f"Section {index}: {segment.strip()}")
            source_for_final = "\n".join(segment_summaries)
            source_label = "CHRONOLOGICAL SUMMARIES OF EVERY HISTORY SECTION"

        prompt = (
            "Review the full CRM context and every chronological event below. Synthesize the lead's story; do not list records.\n\n"
            "CRM CONTEXT (use only to understand events; do not restate profile fields):\n"
            f"{context_text}\n\n"
            f"{source_label}:\n"
            f"{source_for_final}\n\n"
            "Write exactly one or two concise sentences explaining what the lead asked, wanted, agreed to, or declined, "
            "and any next step/outcome explicitly recorded. Preserve changes in the lead's intent over time when present. "
            "Give priority to the lead's replies and counsellor call notes; use counsellor messages only as context. "
            "Do not repeat name, course, city, registration date, or CRM status. Do not infer interest, discussion topics, "
            "callbacks, enrollment, or payment. If the text does not explain the conversation, state that plainly. "
            "Use simple English, with no heading, bullets, markdown, or CRM codes."
        )
        summary = chat(prompt)
        if _grounded(summary, events, context):
            return summary, True
    except Exception as exc:
        print(f"Ollama chat error: {exc}", file=sys.stderr)

    return _evidence_summary(events, context), False


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _origin_is_local_dashboard(self) -> bool:
        origin = self.headers.get("Origin", "")
        return origin in {f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"}

    def end_headers(self):
        if self._origin_is_local_dashboard():
            self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", ""))
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")
        super().end_headers()

    def do_OPTIONS(self):
        if not self._origin_is_local_dashboard():
            self.send_error(403, "Only the local EduCRM dashboard may call this API.")
            return
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/":
            self.send_response(302)
            self.send_header("Location", "/EduCRM_Live_Dashboard.html")
            self.end_headers()
            return
        if self.path == "/api/health":
            self._json(200, {"ok": True, "model": MODEL, "local_only": True})
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/summarize":
            self._json(404, {"error": "Endpoint not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                self._json(413, {"error": "Summary request is empty or exceeds 4 MB."})
                return
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            events = body.get("events", [])
            context = body.get("context", {})
            if not isinstance(events, list) or not isinstance(context, dict):
                self._json(400, {"error": "Expected events and an optional journey context object."})
                return
            ensure_ollama()
            summary, generated_by_ai = summarise_events(events, context)
            self._json(200, {
                "summary": summary,
                "model": MODEL if generated_by_ai else "evidence-based local NLP",
                "generated_by_ai": generated_by_ai,
                "local_only": True,
            })
        except urllib.error.URLError as exc:
            self._json(503, {"error": f"Local Ollama is unavailable: {exc.reason}"})
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def _json(self, status: int, obj: dict):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print("[EduCRM AI] " + fmt % args)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/EduCRM_Live_Dashboard.html"
    print(f"EduCRM local AI dashboard: {url}")
    print(f"Local model: {MODEL} (Ollama at {OLLAMA_URL})")
    print("Summaries are processed on this computer. Press Ctrl+C to stop.")
    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping EduCRM local AI dashboard...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

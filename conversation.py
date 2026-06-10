"""
Manages per-thread conversation history and generates grounded answers using UCSD API.
Sensitive notes (API keys, tokens, etc.) are shown to the user but stripped from LLM context.
"""
from collections import defaultdict
import openai
import db
import query_engine
from config import UCSD_API_KEY, UCSD_BASE_URL, LLM_CHAT_MODEL, LLM_MAX_TOKENS, MAX_THREAD_HISTORY
from sensitive import is_sensitive   # single source of truth

_client = openai.OpenAI(api_key=UCSD_API_KEY, base_url=UCSD_BASE_URL)
_history: dict[str, list[dict]] = defaultdict(list)


# ── conversation ──────────────────────────────────────────────────────────────

def _trim(thread_id: str):
    h = _history[thread_id]
    if len(h) > MAX_THREAD_HISTORY * 2:
        _history[thread_id] = h[-(MAX_THREAD_HISTORY * 2):]


def answer(thread_id: str, user_id: str, user_message: str) -> tuple[str, list[dict], list[dict]]:
    """
    Returns (llm_text_answer, safe_notes, sensitive_notes).
    safe_notes go to LLM context; sensitive_notes are shown to user only.
    """
    note_ids = query_engine.retrieve(user_message, user_id)
    notes = db.get_notes_by_ids(note_ids)

    safe_notes, sensitive_notes = [], []
    for n in notes:
        # Use is_sensitive() — also checks the stored is_sensitive DB flag
        if n.get("is_sensitive") or is_sensitive(n["content_text"]):
            sensitive_notes.append(n)
        else:
            safe_notes.append(n)

    context_parts = []
    for n in safe_notes:
        snippet = n["content_text"][:400]
        context_parts.append(f"[Note {n['id']} | {n['source_type']} | {n['timestamp'][:10]}]\n{snippet}")
    context_block = "\n\n".join(context_parts) if context_parts else "No saved notes found."

    system_prompt = (
        "You are SnapVault, a personal memory assistant. "
        "Answer the user's question using ONLY the notes below. "
        "Be concise and direct. If the answer isn't in the notes, say so.\n\n"
        f"SAVED NOTES:\n{context_block}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    _history[thread_id].append({"role": "user", "content": user_message})
    _trim(thread_id)
    messages.extend(_history[thread_id])

    response = _client.chat.completions.create(
        model=LLM_CHAT_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        messages=messages
    )
    reply = (
        response.choices[0].message.content
        or response.choices[0].message.reasoning_content
        or ""
    ).strip()
    _history[thread_id].append({"role": "assistant", "content": reply})

    return reply, safe_notes, sensitive_notes


def clear(thread_id: str):
    _history.pop(thread_id, None)
"""
Manages per-thread conversation history and generates grounded answers using UCSD API.
conversation.py holds a Python dict called _history keyed by thread_id. Each entry is a list of {"role": "user"/"assistant", "content": "..."} -> short-term memory
When answer() is called: it retrieves relevant notes, truncates each to 400 chars, and injects into the system prompt as a context block. 
Then it appends the new user message to _history[thread_id], calls the API with the full history, appends the assistant reply back to history, and trims the history to the last 8 turns (MAX_THREAD_HISTORY * 2 messages). 
"""
from collections import defaultdict
import openai
import db
import query_engine
from config import UCSD_API_KEY, UCSD_BASE_URL, LLM_CHAT_MODEL, LLM_MAX_TOKENS, MAX_THREAD_HISTORY

# Initialize OpenAI client configured for UCSD TritonAI
_client = openai.OpenAI(api_key=UCSD_API_KEY, base_url=UCSD_BASE_URL)

# History store: { thread_id: [ {"role": ..., "content": ...}, ... ] }
_history: dict[str, list[dict]] = defaultdict(list)


def _trim(thread_id: str):
    h = _history[thread_id]
    if len(h) > MAX_THREAD_HISTORY * 2:
        _history[thread_id] = h[-(MAX_THREAD_HISTORY * 2):]


def answer(thread_id: str, user_id: str, user_message: str) -> tuple[str, list[dict]]:
    """
    Returns (llm_text_answer, retrieved_notes_list).
    """
    # 1. Retrieve relevant notes from your vector DB
    note_ids = query_engine.retrieve(user_message, user_id)
    notes = db.get_notes_by_ids(note_ids)

    # 2. Format the notes into a clean context block
    context_parts = []
    for n in notes:
        snippet = n["content_text"][:400]
        context_parts.append(f"[Note {n['id']} | {n['source_type']} | {n['timestamp'][:10]}]\n{snippet}")
    context_block = "\n\n".join(context_parts) if context_parts else "No saved notes found."

    # 3. Create the strict system prompt instructions
    system_prompt = (
        "You are SnapVault(Otter), a personal memory assistant. "
        "Answer the user's question using ONLY the notes below. "
        "Be concise and direct. If the answer isn't in the notes, say so.\n\n"
        f"SAVED NOTES:\n{context_block}"
    )

    # 4. Construct OpenAI-style messages array
    messages = [{"role": "system", "content": system_prompt}]
    
    # Track the active user conversation turn
    _history[thread_id].append({"role": "user", "content": user_message})
    _trim(thread_id)
    
    # Append conversation logs after the system instructions
    messages.extend(_history[thread_id])

    # 5. Call the 120B Chat Model
    response = _client.chat.completions.create(
        model=LLM_CHAT_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        messages=messages
    )
    reply = response.choices[0].message.content.strip()

    # Log the response to short-term memory
    _history[thread_id].append({"role": "assistant", "content": reply})

    return reply, notes


def clear(thread_id: str):
    _history.pop(thread_id, None)
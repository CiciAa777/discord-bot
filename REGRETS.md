# SnapVault — Regrets

## Things I Wish I'd Gotten To

**Persistent cloud storage**
Railway's ephemeral filesystem means SQLite and ChromaDB wipe on every redeploy. Every demo starts from a blank slate. The fix is a mounted Railway volume or swapping SQLite for a hosted Postgres and ChromaDB for a hosted vector DB (Pinecone, Weaviate). This should have been scoped in from the start — treating storage as an afterthought meant discovering the problem at deployment, not design time.

**Rate limiting**
One user hammering `/save` burns the shared UCSD API quota for everyone. A simple in-memory counter per `user_id` per minute would have taken an hour to add. It wasn't a problem during solo testing and then became an obvious gap the moment other users joined.

**Multi-user isolation**
The bot is technically multi-user (all queries filter by `user_id`) but there's no access control at the Discord level — anyone who joins the server can see the bot and interact with it. A proper multi-tenant design would scope the bot to DMs only, or require registration before use.

**Google Calendar reliability**
The LLM event parser works on clean inputs but fails silently on ambiguous ones — returning `None` with no fallback UI. Should have added a structured form fallback: if parsing fails, ask the user for title, date, and time explicitly rather than just saying "couldn't parse."

---

## Where Time Was Wasted

**Debugging the reasoning model output format**
The UCSD 120B model puts output in `reasoning_content`, not `content`. This caused silent `None` returns across the classifier, event parser, and consolidation LLM. Each one had to be debugged separately. A single test script that validated the API response format at the start would have saved hours across the project.

**ChromaDB embedding dimension mismatch**
`find_similar()` initially passed `query_texts` to ChromaDB, which used its built-in MiniLM model (384d) instead of the UCSD model (1024d) used at upsert time. The error only appeared at runtime after deployment. Should have written a test for the full upsert → query round-trip before building anything on top of it.

**Discord `view=None` TypeError**
`followup.send()` raises a `TypeError` if `view=None` is passed explicitly — it needs to be omitted. This caused `/save` to fail silently in production. A quick local test of the slash command before deploying would have caught it immediately.

---

## Advice for a Future Engineer Picking This Up

**Test the API response format before writing any logic around it.**
The UCSD models behave differently from standard OpenAI — always check whether output is in `content` or `reasoning_content` before building classifiers or parsers on top.

**Solve storage persistence before everything else.**
The ephemeral filesystem problem is a blocker for any real use. Set up a Railway volume or a hosted DB in the first hour, not as a post-deployment cleanup task.

**The LLM classifier is the weakest link.**
Classification works well for clear save/query cases but struggles with short or ambiguous messages. A future improvement is a fine-tuned small classifier (or even a well-constructed few-shot prompt with examples) rather than asking the 120B reasoning model to output one word.

**The consolidation threshold (0.85) needs tuning.**
It was set arbitrarily. In practice it fires too rarely — notes that are clearly about the same topic score below 0.85 because the phrasing differs. Consider lowering to 0.75 and letting the LLM comparison step handle false positives.

**Google Calendar OAuth is the most fragile part.**
The token refresh logic relies on the Google client library handling expiry automatically. In practice, tokens expire and the refresh can fail silently if the `refresh_token` is missing (which happens when the user authorizes more than once without `prompt=consent`). Add explicit token validation and re-auth prompting.

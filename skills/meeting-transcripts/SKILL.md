---
name: meeting-transcripts
description: "Reliably ingest, archive, index, retrieve, and re-analyze full meeting transcripts from webhook, API, MCP, or manually supplied sources."
version: 2.0.0
---

# Meeting transcript archive

Maintain a durable local source of truth for meeting transcripts so historical questions and regenerated summaries use the original meeting content rather than conversational memory.

## Trigger conditions

Use this skill when:

- receiving a new or changed meeting note/transcript from any provider;
- designing webhook, API, MCP, or scheduled transcript ingestion;
- backing up meeting history;
- searching for what was discussed or decided previously;
- re-evaluating or re-summarizing a past meeting.

Provider-specific integration details belong in `references/`, while the archive and retrieval workflow remains provider-independent.

## Core invariants

1. **Persist before summarizing.** Save the complete transcript first; derived summaries are replaceable.
2. **Use stable source IDs.** Deduplicate and upsert by provider meeting/note ID, never by title alone.
3. **Preserve provenance.** Record provider, timestamps, participants, source URL when available, and backup time.
4. **Treat updates as updates.** Regenerated or edited notes should refresh the existing archive entry without adding duplicate index rows.
5. **Keep routine logs content-free.** Log IDs, counts, and errors—not transcript bodies.
6. **Search, then read.** Locate candidate meetings through the index/search command, then load the complete transcript before answering.
7. **Separate ingestion from analysis.** Deterministic scripts/API calls should archive data; the agent should summarize or synthesize only after archival succeeds.

## Ingestion workflow

1. Authenticate the source event or request when applicable.
2. Deduplicate the source event and identify the stable meeting ID.
3. Fetch the complete current record if the event contains only metadata.
4. Normalize title, meeting date, participants, summary, notes, transcript, and provenance.
5. Save or upsert the local Markdown record.
6. Update the searchable index atomically.
7. Verify the saved record can be retrieved by ID.
8. Only then generate summaries, action items, or user-facing notifications.

For providers with webhooks, acknowledge quickly and process asynchronously. Pair event-driven ingestion with a scheduled reconciliation query so missed deliveries do not create permanent gaps.

## Local helper

The packaged `scripts/meetings.sh` supports the current file archive:

- `meetings.sh save "<title>" "<date:YYYY-MM-DD>" [meeting_id]` — reads the transcript from stdin, saves it under `data/`, and records it in the index.
- `meetings.sh list [since:YYYY-MM-DD]` — lists indexed meetings as JSONL.
- `meetings.sh search "<term>"` — finds meetings whose archived content contains the term.
- `meetings.sh get "<file-or-substring>"` — prints one complete archived transcript.

The current helper is suitable for append-only/manual ingestion. Automated provider integrations must add idempotent upsert behavior or check the index by stable ID before calling `save`.

## Retrieval workflow

1. Use `list` for a known date range or `search` for people, topics, decisions, or projects.
2. If multiple meetings match, use dates, participants, and titles to choose the right records.
3. Call `get` for each selected record and read the complete text.
4. Answer from those records, identifying the meeting and date when useful.
5. Distinguish exact transcript evidence from interpretation or inferred conclusions.

## Storage and privacy

- Restrict archive directories and transcript files to the owning user.
- Keep API keys, OAuth tokens, and webhook signing secrets out of files and logs.
- Do not place full transcript text in persistent assistant memory.
- Do not sync or transmit the archive to third parties unless the user explicitly requests it.
- Follow participant-consent, workplace, recording, and retention policies.

## Provider references

- **Granola:** See `references/granola-ingestion.md` for MCP versus API selection, webhook events, signature verification, retries, plan limits, and the recommended webhook-plus-reconciliation backup design.

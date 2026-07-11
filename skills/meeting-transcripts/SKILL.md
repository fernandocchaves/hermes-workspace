---
name: meeting-transcripts
description: "Save and retrieve full meeting transcripts received from Meetily via webhook. Use when processing a new meeting transcript (save it before summarizing), or when the user asks to re-evaluate, search, or re-summarize a past meeting."
---

# meeting-transcripts

Salva e recupera transcrições completas de reuniões (recebidas via webhook do
Meetily) pra consulta e re-resumo posterior.

## Quando usar

- Ao processar uma nova transcrição de reunião recebida via webhook: sempre
  chamar `save` antes de gerar o resumo.
- Quando o usuário pedir pra reavaliar, buscar, ou refazer o resumo de uma
  reunião anterior: usar `search`/`list` pra encontrar a reunião certa,
  depois `get` pra ler a transcrição completa antes de responder.

## Comandos (scripts/meetings.sh)

- `meetings.sh save "<título>" "<data:YYYY-MM-DD>" [meeting_id]` — lê a
  transcrição completa do stdin, salva em `data/` e registra no índice.
- `meetings.sh list [desde:YYYY-MM-DD]` — lista reuniões salvas (uma linha
  JSON por reunião).
- `meetings.sh search "<termo>"` — busca reuniões cujo conteúdo contém o
  termo, retorna as entradas do índice que batem.
- `meetings.sh get "<arquivo-ou-trecho>"` — imprime a transcrição completa
  de uma reunião específica.

# Campus AI Assistant -- notes for Claude Code

Instructions for AI coding assistants working in this repo. The README is the user-facing
description; this file is how the project is worked on.

## What this project is

A bilingual (English/French) AI assistant for Al Akhawayn University (AUI) students. It answers
questions about academic policies, the course catalog and scholarships, always citing its
sources, and uses an agent to query structured course data (e.g. "what are the prerequisites for
ACC 2302?"). It is an unofficial student project, not an official AUI service (the UI says so).
AUI has confirmed they are fine with the project, so the catalog text can stay in the repo.

Live demo: https://campus-assistant.denmarkeast.cloudapp.azure.com

It is also a portfolio project for AI Software Engineer internship applications, so it must
demonstrate: RAG, AI agents, hybrid search, REST APIs, a TypeScript frontend, tests, Docker,
CI/CD, and evaluation.

## Working style (IMPORTANT, follow strictly)

- This is a learning project. Youness (the author) must be able to understand and defend every
  line in an interview.
- Work in small steps. One step per turn. Never scaffold large parts of the project at once.
- Before writing code: explain what the step does, why, and which concepts are involved.
- After writing code: explain the key lines, then say exactly what to run to verify it.
- Wait for Youness to confirm the step works before moving to the next one.
- When introducing a new concept (embeddings, BM25, LangGraph state, etc.), explain it in depth
  first.
- Prefer clear, explicit code over clever abstractions.
- Commit after every working step with a clear conventional commit message (feat:, fix:, test:,
  docs:, chore:), and push.
- Run the full test suite before each commit (CI was red between 9e01bee and cfec590).
- Measure before and after a change that can affect quality (retrieval eval, faithfulness eval).
  When a decision rule is agreed, record it before seeing the numbers.
- Rules that must hold are enforced in code, not only in the prompt: prompt-only rules ("at most
  two searches", answer language, bracket style) kept failing in testing.
- Every deploy or backup script uses `set -euo pipefail`, closes stdin on `docker compose run` and
  `docker exec`, and ends by printing proof the work happened (counts, size, checksum). Twice in A1.4
  a script reported success without doing the work: a clean exit alone proves nothing.
- Permission rules live in `.claude/settings.json`: any new Groq-calling module or deploy command needs a matching ask or deny rule for both PowerShell and Bash.

## Environment

- Windows, PowerShell 5.1. Python 3.12, Node 24, Docker Desktop (WSL2 backend), 16 GB RAM.
- The VM's SSH key has a passphrase and lives in the Windows ssh-agent, so use Windows'
  `C:\Windows\System32\OpenSSH\ssh.exe`, with no `-i`. Git Bash's `ssh` can't reach that agent.
- Give PowerShell commands, not bash, unless running inside a Docker container.
- PowerShell 5.1 mangles double quotes in arguments to native programs: write multi-line commit
  messages to a file and use `git commit -F <file>`.
- No NVIDIA GPU: keep ML workloads (embeddings) on CPU. Don't switch to GPU (ROCm) unprompted.
- The project lives outside OneDrive (long-path issues).
- If the Docker daemon isn't reachable: `docker desktop start`, wait for `docker desktop status`.
- Postgres (Docker) is on host port **15432**. 5432/5433 collide with native Postgres installs on
  this machine (a misleading "password authentication failed"), and ports in 49152-65535 can
  fall into Windows/Hyper-V dynamic exclusion ranges after a reboot. If a DB connection fails,
  rule out the network layer first: `Get-NetTCPConnection -LocalPort 15432 -State Listen`,
  `netsh interface ipv4 show excludedportrange protocol=tcp`, then `docker compose down` +
  `docker compose up -d db` (not just `restart`).
- npm 11.4.2 crashes adding some packages ("Cannot read properties of null (reading
  'edgesOut')"); `npx npm@11.20.0 install ...` works, and `npm ci` accepts the lockfile.

## Stack

- Backend: Python 3.12, FastAPI, Server-Sent Events.
- Agent: LangGraph (explicit `StateGraph`), LangChain tools.
- LLM: Groq `openai/gpt-oss-20b` (primary), Gemini (fallback), switched by `LLM_PROVIDER`.
  Free tiers have tight daily token limits: keep prompts lean, never loop on LLM calls without a
  cap. The evaluation and the live demo share the same Groq quota.
- Embeddings: `intfloat/multilingual-e5-small` (384 dims, 512 tokens), local CPU.
- Database: PostgreSQL 16 + pgvector (vectors), Postgres full-text search (keywords), normal
  tables for courses and prerequisites.
- Frontend: React + TypeScript (Vite), react-markdown (raw HTML disabled), vitest.
- Quality: pytest, ruff (pinned 0.16.9, same in CI), oxlint, a retrieval eval set and an answer
  faithfulness eval set.
- Infra: Docker Compose (db + api + frontend; Caddy in production), GitHub Actions CI.

## Architecture

1. Ingestion (`backend/app/ingestion/`): load public AUI documents (catalog PDF + scholarship
   pages, listed in `data/registry.toml`) -> clean -> chunk (each chunk starts with a "Section:"
   line: level + nearest heading) -> embed -> store in `document_chunks` with metadata.
   Courses and prerequisites are extracted into their own tables.
2. Retrieval (`backend/app/retrieval/`): vector + keyword search fused by reciprocal rank
   fusion (k=60). Each search fuses several phrasings: the agent's query, its English version
   (`query_en`), and on the first turn the student's question; the university's name is
   stripped from each.
3. Agent (`backend/app/agent/`): tools `search_documents` and `query_courses` (recursive
   prerequisite chains); at most 3 tool rounds, then a forced answer (with retry and fallback).
4. Generation: answer only from retrieved passages, cite them as `[N]`, say "I don't know" when
   the passages don't cover it. Citation numbers are per passage, once per request.
5. API (`backend/app/main.py`): `/chat` (SSE: token, tool_call, citations, done, error),
   `/health`, `/limits`, `/editions`, `/sources/{source}`. Request limits (`MAX_*` in `app/config.py`, the same
   numbers in `frontend/src/requestLimits.ts`, pinned by a test) run before the demo limits. Demo limits (daily cap, per-IP limit) in Postgres
   (`app/limits.py`). The cap's default is in `app/config.py`, `/limits` serves the value in force
   to the About page, and tests pin the README and `.env.example` to the default.
6. Frontend (`frontend/`): chat with live tool progress, citation chips and source cards, example questions
   replayed from saved answers (no API call), dark mode.
7. Evaluation (`backend/app/evaluation/`, `eval/`): retrieval eval (anchors, Hit@k, MRR) and the
   faithfulness pipeline (claim splitting, LLM judge with a verbatim quote check, hand labels,
   agreement). The judge rules are frozen for comparability between runs.

## Data rules

- Only public university documents. No personal student data.
- Secrets live in `.env` (gitignored); `.env.example` lists the variables.
- On the server, IP addresses are stored only as an HMAC (`IP_HASH_SECRET`), deleted after 2 days.
- Logs must hold no question text and no visitor IP: never print queries, messages or exception
  text in the request path (exception type only). `tests/test_log_privacy.py` enforces it; the
  README's Data section says what each container logs, so keep the two in step.

## Pilot threshold

Agreed 2026-11-05, before run 4, following the rule of recording a decision rule before seeing the
numbers. Students use the assistant only if run 4 meets all of these:

1. At most 6/26 main answers with an unsupported cited claim, and at most 4/13 in French.
2. Every failing claim hand-checked: zero that would change a deadline, amount, credit count or
   eligibility outcome.
3. At most 2/30 false refusals.
4. Zero answers without a search call and citations, other than greetings or questions about the
   assistant, reach the student across the off-topic and injection set.

## CSP enforcement rule

Agreed 2026-11-05, before the report-only policy went live and before looking at the live console,
following the same rule. The Content Security Policy is enforced (with the A1.3 deploy) once all of
these show zero violations in both Chrome and Firefox:

1. The first screen.
2. An example replay.
3. One live question (the only path that exercises `connect-src` via `/chat`).
4. The About page (fetches `/limits`).
5. The diagram zoom.
6. Dark mode.

`/api/docs` is exempt: B19 turns it off. Met and enforced on 2026-11-05 (`deploy/csp-check`, which
also covers WebKit and a source link). The enforced run is recorded under "Current status".

## A2 order and decisions

Decided 2026-11-06. A2 runs in the order A2.1, A2.2, A2.6b, A2.3, A2.4, A2.5, A2.6, A2.7, A2.8; step numbers don't change.
Reason: A2.6b (the answer-level gate) depends only on A2.2, it fixes the reported off-topic answers sooner, and A2.6 is
blocked on AUI (D8). Domain-aware retrieval and conflict handling between departments stay at B3. No LLM-based scope
classifier: the gate is structural and costs no tokens. Later steps' acceptance criteria are in `docs/architecture.md`
section 9.

## A2.1 retrieval rule

Agreed 2026-11-06, before the eval was run on any A2.1 code, following the rule of recording a decision rule before seeing the
numbers. After A2.1, `python -m app.evaluation.run_retrieval_eval` must match
`eval/results/retrieval/2026-11-05_a0_baseline.txt` line for line, on both the 14- and the 12-question set. If any rank
changes: stop and report, don't adjust. 0 LLM tokens: no faithfulness or Groq calls in this step.

## A2.6b rule

Set 2026-11-06 by Claude, with Youness's go-ahead to keep going, before any A2.6b code, following the rule of recording a
decision rule before seeing the numbers. The gate replaces an answer unless a tool ran and every marker in it is one a tool
returned. Before it deploys:

1. Offline, 0 LLM tokens, on saved answers: on run 3 it replaces exactly the 3 refusals `docs/architecture.md` section 2.4
   names, and on `answers_citation_check_2026-11-06.jsonl` only `add_drop_en`.
2. Through the real `/chat` streaming path, the off-topic and injection set: zero answers without a search call and valid
   citations reach the student, other than the code-written templates (pilot threshold item 4).
3. Through the same path, the 12 questions of the uncited answers check: at most 1/12 replaced by a template.

If any of these fails: stop and report, don't adjust. Items 2 and 3 cost about 70k tokens of the 200k a day the demo also uses.

Result, 2026-11-07, 66,788 tokens, `eval/results/gate/2026-11-07_gate_check.jsonl`: item 1 passed, item 2 **0/12** reached a
student uncited, item 3 **1/12** replaced (`w_grade_fr`), so the rule passed. Read by hand: `not_covered` got the scope template
and not the not-found template that `docs/architecture.md` section 9 expects, because the model didn't search; that criterion
isn't met and waits on Youness. `mixed` answered "1 + 1 = 2." next to a cited sentence, which an answer-level gate can't stop.
With the uncited answers check, 2/24 on these questions, a different one each time: about 2.5 of 30 false refusals, at the limit.

Decided 2026-11-07 by Claude, with Youness's go-ahead to decide: the scope template is accepted for an AUI question the model
doesn't search for, because the gate can only read that no tool ran. One automatic retry of an uncited answer is a candidate to
decide before run 4, after A2.7's prompt changes, not part of this deploy.

Follow-ups, set 2026-11-07 before they ran, because section 2.4 says to measure them before deciding: 6 follow-ups through `/chat`,
each with a saved answer as history (`eval/followup_eval_set.json`), about 15k tokens. A template on any of the 3 substantive
ones, which need a new search: stop and report, and don't deploy. The 3 conversational ones ("Thanks!") are the known cost in
section 2.4: a template on them is recorded and doesn't block.

Result, 2026-11-07, 20,966 tokens, `eval/results/gate/2026-11-07_followups.jsonl`: **not passed, so A2.6b isn't deployed.** Substantive
1/3 replaced (`followup_summer`, which the catalog covers), conversational 3/3 replaced, 0 reached a student uncited. On real
questions so far, 3/27 replaced. Read by hand: `followup_fr` says transferred credits count toward the GPA, cites only the
pass/fail rule, and a rough search of the catalog found no sentence saying so: a cited claim the gate can't judge (AG-4).

Checked by Youness on 2026-11-12, catalog pp. 30-31 and 110-111: `followup_fr` is wrong twice. No sentence says transferred credits
count toward the GPA, and it lists D+ and D as transferable where p. 30 says "a grade of 'D+' or below are not considered for
credit transfer". An unsupported cited claim (AG-4) touching an eligibility outcome, the kind D3 item 2 forbids. It's recorded
in `eval/known_failures.json` for A2.7/A2.8. The gate isn't meant to catch it, so it doesn't block A2.6b.

Retry rule, set 2026-11-12 by Youness, before the retry was measured, following the rule of recording a decision rule before
seeing the numbers. Deploying on the failed follow-up rule would be changing the rule after the numbers, and 3/27 real questions
replaced can't meet the pilot's 2/30, so the retry moved into A2.6b from A2.7. Built in `e3b6cbd`, `f4c0a2f`: on the gate's
`no_citation` only (never `no_tool`), one retry per question, enforced by the graph's shape (`gate -> retry -> retry_gate -> END`,
no edge back). Same tool results, no new search, no tools bound, plus a note to cite only the numbers given. The gate checks the
retried answer as before; if that fails, the not-found template stands. The retry's tokens are in the trace and the eval output.
Before A2.6b deploys:

1. Offline, 0 LLM tokens: the no-tool path is unchanged, so the off-topic set's outcome doesn't change. Proved by a test, not a
   re-run (`b360f78`): `tests/test_gate_node.py` replays the 12 off-topic outcomes of `2026-11-07_gate_check.jsonl` (all `no_tool`
   or passed) and gets the same text, with no retry and no extra model call.
2. Through the real `/chat` path, the 3 substantive follow-ups, with the same saved history as on 2026-11-07: 0/3 replaced by a
   template.
3. Through the same path, the 12 questions of the uncited answers check: at most 1/12 replaced.

If any of these fails: stop and report, don't adjust, don't deploy. The 3 conversational follow-ups stay the known cost, don't
block, and aren't re-run. Budget: Youness estimated about 40k; the same questions cost 43,090 (sample) and 17,017 (substantive
follow-ups) on 2026-11-07, so about 60-65k with retries. Check the day's usage first, run when the demo is quiet, and stop if
it would leave less than 60k for the day: the sample and the follow-ups run separately, each with `--cap` set from that check.

Result, 2026-11-12, 47,992 tokens, `eval/results/gate/2026-11-12_retry_sample.jsonl`: **item 3 not passed, so the follow-ups
weren't run and A2.6b isn't deployed.** Item 1 passed offline. Item 3: **2/12** replaced, limit 1. `transfer_credits_en` was
retried (2,492 tokens) and the retry cited nothing either; `academic_probation_fr` cited a number no tool returned
(`invented_marker`, not retried by design). Both passed on 2026-11-07, and `w_grade_fr`, replaced then, passed: the failures
move from run to run. 0 reached a student uncited. The demo had 0 questions in the 24 hours before the run. The records hold
only what the browser received, so the rejected texts, and what the retry wrote, aren't known.

Diagnosis, 2026-11-12, 32,980 tokens, `eval/results/gate/2026-11-12_diagnosis.jsonl` (`app.evaluation.run_gate_diagnosis`, which
keeps every attempt; it decides nothing and counts toward no rule). `transfer_credits_en` 3 times: the first answer cited
nothing 3/3 (4/4 today with the sample run). Twice it was the right answer (68 undergraduate, 12 graduate credits) ending "These
limits are stated in the academic catalog" instead of markers; once it was empty. The retry passed 2/3: the empty one became
"68 credits [2][3]", one became the same answer with [2] and [6], and the third repeated "stated in the academic catalog" with
no marker. `academic_probation_fr` 3 times: passed 3/3, so its `invented_marker` was a rare draw. So on this question the
templates are false refusals of correct answers, and the retry helps but isn't enough on its own.

Next steps, decided 2026-11-12 by Claude with Youness's go-ahead to decide, before any of them ran, following the rule of
recording a decision rule before seeing the numbers:

- **The main prompt isn't pulled forward.** The first answer leaving out markers is the main prompt's wording, which belongs to
  A2.7 (A2.2 kept wording out of A2.6b). A2.6b changes only the retry's own note. `transfer_credits_en`'s uncited first answers go
  into `eval/known_failures.json` as a citation failure A2.7 must fix.
- **Step 1, 0 tokens:** a stronger retry note, sent as the last message the model reads (nearest the answer) instead of the end
  of the system prompt, naming the failure seen: every fact ends with `[N]`, and pointing to "the catalog" in words instead of a
  number doesn't count. Offline tests as before; the main prompt still matches the fixture byte for byte.
- **Step 2, the retry on its own, about 25-30k tokens:** a harness re-runs the 3 diagnosis runs' saved search queries (local
  retrieval, 0 tokens) and calls only the retry, 10 times with the current note and 10 with the new one, round-robin over the 3
  search sets. The new note is kept only if at least 9/10 of its retries pass the gate and at least as many as the current
  note's. Each passing retry is read by hand: a marker on a passage that doesn't hold the figure it's cited for counts as a
  failure. Otherwise: stop and report.
- **Step 3, the retry rule again, with a larger sample:** 12 questions, one answer each, swapped 3 outcomes between two runs, so
  the sample is doubled. Through `/chat`: the 12 sample questions **twice each, at most 2/24 replaced** (the old rate of 1/12),
  and the 3 substantive follow-ups **twice each, 0/6 replaced**; 0 reaching a student uncited, as before. Item 1 stays proved
  offline. About 90k + 35k tokens, so it runs over two days, each checked against the 60k floor. If any item fails: stop and
  report, don't adjust, don't deploy.

Step 1 done 2026-11-13 (`6e8addb`): `CITATION_RETRY_LAST_NOTE`, sent last by `graph._retry_input`; the main prompt still matches
the fixture. Step 2 result, 2026-11-13, 47,912 tokens (the estimate of 25-30k was low: one retry is about 2-3k),
`eval/results/gate/2026-11-13_retry_note.jsonl` (`app.evaluation.run_retry_note_check`; the rebuilt searches gave the diagnosis'
markers): **new note 9/10 passed the gate, previous 7/10, so the new note is kept** and the previous one left the graph (it lives
in the harness, to re-run the comparison). Read by hand, the 9 passing retries put 68 on [2] (or [2][3]: [3] overlaps [2] and
ends with the same sentence) and 12 on [6], nothing else claimed: 9/10 stands. Both notes failed on pair 3, the same set (set 3).
Seen, not counted: the new note's answers are shorter (one or two sentences, no grade rules), and two of the previous note's
passing retries said the catalog sets no graduate limit, on set 1, which didn't retrieve [6]. Next: step 3.

Before step 3, set 2026-11-14 by Youness after reading `e3b6cbd` to `02bfd3f`, before step 3 ran, following the rule of recording
a decision rule before seeing the numbers:

- **If step 3 fails: no more iterations on the retry note.** The root cause is the main prompt's citation wording (A2.7), and
  A2.6b has taken a week and about 260k tokens of measurement (the uncited answers check included) against an estimate of 1.5
  days. If any step 3 item fails, A2.6b doesn't deploy on its own. It deploys together with A2.7's prompt changes (answer
  first, every fact ends with `[N]`, never "stated in the catalog"), and that combined change is measured once with step 3's
  exact rule (at most 2/24 replaced, 0/6 on the follow-ups, 0 uncited reaching a student) plus A2.7's own criteria. The
  catalog-year note waits for Q1 and doesn't block it. If this branch is taken, the order note in `docs/architecture.md`
  section 9 is updated.
- **Step 3 isn't fully independent of step 2.** The new note was chosen on `transfer_credits_en`'s search sets, and that
  question is one of step 3's 12: its result is reported with that caveat. 9/10 against 7/10 isn't proof the new note is
  better, because with n=10 the difference isn't significant. The rule asked for at least 9/10 and not worse, and that is
  what was shown.
- **Two things seen in step 2 are in `eval/known_failures.json` for A2.7/A2.8:** `retry_drops_context` (the new note's
  retries keep one or two sentences: answer quality, not citation) and `retry_no_graduate_limit` (the previous note's
  retries on set 1, which didn't retrieve [6], said the catalog sets no graduate limit: a wrong claim the gate passes). The
  retry can't search, so when the passage it needs is missing it can state a confident falsehood. A2.8's hand check looks at
  retried answers specifically.
- **main can't be deployed partially.** The gate is on main with no switch, so any deploy of HEAD ships it. A hotfix needed
  before A2.6b is accepted deploys from a branch cut at `8472f3b` (the deployed A2.2 commit), not from main: `deploy/DEPLOY.md`,
  A2.6b.

Step 3, sample part, 2026-11-14, 94,805 tokens recorded (about 105k used: errored records log 0),
`eval/results/gate/2026-11-14_step3_sample.jsonl`: **0/24 replaced (limit 2), 0 reached a student uncited: passed.** Retried
2/24, both passed the second gate: `transfer_credits_en` round 1 (its first answer uncited again, 5/5 since 11-12) and
`repeat_course_en` round 2 (a new one, cites [1] five times, not checked against the passage). `transfer_credits_en`'s pass
after the retry isn't independent evidence: the note was chosen on its searches. Its round 2 cited in the first answer. Three
questions first errored (`scholarship_work_hours_fr` 1, `acc2302_chain_en` 1, `transfer_credits_en` 2): the local Postgres
restarted mid-run, because the run started while Docker Desktop was still starting. Decided by Claude with Youness's go-ahead,
after the numbers and in the open: they never got an answer, so the 3 were asked again in their own rounds, once each, with
Docker and the database checked first. The errored
records are kept in `2026-11-14_step3_sample_errors.jsonl`. Seen there, not counted: the gate passed
`scholarship_work_hours_fr`'s answer with a real [11], `/chat` sent it, then `load_sources()` timed out on the database, so the
student would see a marker with no source card, then the error. Next: the 3 substantive follow-ups twice each (0/6), on
2026-11-15 after the floor check.

Step 3, follow-up part, 2026-11-15, 40,450 tokens, `eval/results/gate/2026-11-15_step3_followups.jsonl`: **0/6 replaced (limit 0),
0 reached a student uncited: passed, so step 3 passed and the A2.6b rule is met.** Floor check first: 0 demo questions in the
prior 24 hours, the last eval run ended 2026-11-14 03:33 UTC; local Postgres checked healthy before the run. Retried 2/6, both
`followup_summer` (its first answer uncited in both rounds; replaced on 2026-11-07), both passed the second gate. Read by hand:
both retried `followup_summer` answers state refund or deadline rules the catalog contradicts (round 1 turns "no refund ... up to
the 40th class day" into a refund window; round 2 says add/drop ends on the 40th class day, then the 4th one bullet earlier): AG-4
touching an amount and a deadline, the kind D3 item 2 forbids, in `eval/known_failures.json` (`retry_summer_refund_deadline`). As
with `followup_fr` on 2026-11-12, the gate isn't meant to catch it, so it doesn't block the rule, but it's a second case of the
retry stating a confident falsehood (after `retry_no_graduate_limit`). `followup_fr` said both times that the catalog doesn't say
whether transferred credits count toward the GPA, with no D+/D claim: the 2026-11-07 errors didn't recur. `followup_graduate`
said 12 credits [3] both times.

Deployed 2026-11-15 (`8011e99`), decided by Claude with Youness's go-ahead to decide, after the numbers: the rule was set before
them and passed, the deployed A2.2 already lets uncited answers reach students, and the retry's wrong claims are AG-4, which the
rule leaves to A2.7/A2.8. No rollback condition in `deploy/DEPLOY.md` (A2.6b) was met.

Retry risk rule, set 2026-11-18 by Youness after reading `1ea8e68` to `240fe46`, before anything was measured, following
the rule of recording a decision rule before seeing the numbers. The retry turns uncited answers into cited ones, and a wrong
answer with real markers looks more trustworthy to a student than an uncited one, and the gate can't tell them apart. A
template (a false refusal) is the safer failure: it costs against item 3's 2/30, while a wrong deadline breaks item 2 outright.

- **A2.8 (run 4):** every answer that went through the retry is listed separately and checked by hand against its passages.
  If any retried answer fails D3 item 2 (a deadline, amount, credit count or eligibility outcome), the retry is removed: a
  `no_citation` answer gets the not-found template directly. Then the false refusals are re-counted against item 3. One
  decision, not a new round of tuning.
- **A2.7 reports the retry rate:** how often the retry fires, per question and overall, in its measurement. If A2.7's prompt
  makes first answers cite, the retry should rarely fire.

Hand check of `repeat_course_en`'s retried answer (step 3 sample, round 2), 2026-11-18, 0 LLM tokens, by Claude: **fails, AG-4,
and D3 item 2 on an eligibility outcome**, in `eval/known_failures.json` (`retry_repeat_third_attempt`). Every sentence cites
[1]. The record keeps marker numbers, not passages, so which passage [1] was isn't known; local searches rebuilt from the
question plus three plausible agent queries put chunk 253 (letter grades), 282 (undergraduate repeat policy) or 786 (graduate
repeat policy) first. None of them holds every claim: 253 holds none of the repeat rules, 282 stops at "appeal to the" before
the third attempt, and 786 is the graduate rule (B- or lower), which contradicts "C- or lower" for this undergraduate. On
content, four claims match the catalog (p. 121: C- or lower may be repeated, highest grade counts in the CGPA, counted once for
credit). The fifth, "a repeat is normally allowed only once, unless you seek special permission for a third attempt", drops the
condition: the catalog allows an appeal to the dean only "if a required course is failed a second time". Of the four checked
problems it's the mildest, and a judgment call for Youness to confirm, as with `followup_fr`. Seen, not retried, so outside
the rule: round 1's first answer ends, uncited, "the new grade (whatever it turns out to be) will replace the C-", which
contradicts the highest-grade rule its own cited paragraph states (`repeat_course_new_grade_replaces`). Tally of hand-checked
retries: on `transfer_credits_en`, the question the note was tuned on, the new note 9/9 correct and the previous note 2 wrong
(`retry_no_graduate_limit`); on every other question, 3/3 wrong (`followup_summer` twice, `repeat_course_en`). The A2.8 rule
applies at run 4, so nothing changes now.

## A2.3 rule

Set 2026-11-15 by Claude, with Youness's go-ahead to decide, before any A2.3 code, following the rule of recording a decision
rule before seeing the numbers. A2.3 stores chunks, courses and prerequisites per edition, searches only active public editions,
and adds an activate/rollback command. With one active edition per document, as today, nothing a student sees may change.

**Design decision, same date:** the edition column stays `source`. It already holds the edition id in all three tables (the
registry says `id` "equals document_chunks.source", and the local database agrees: 3 editions, 3 sources), so section 3.2's new
`edition_id` column would be a second copy of it. `source` gets a foreign key to `document_editions(id)` instead, and keys that
are already `(source, ...)` (citation numbers, the RRF key, the chunk upsert) are already per edition. What does change:
`courses` keyed on `(source, code)`, `course_prerequisites` gains `source`, the prerequisite walk stays inside one edition, and
ingestion replaces one edition's rows, not every document's. `docs/architecture.md` section 3.2 is updated to match.

Sub-steps, one per turn: 0. this rule and a "before" capture of every course lookup; 1. the schema (in place, on a database that
already has data); 2. the shared active-and-public filter in every search and course lookup; 3. ingestion per edition; 4. the
`activate` command (rollback is the same command the other way) and the two-edition test; 5. how the generated scope text
follows the edition in force (decided in that turn, before its code); 6. deploy.

After A2.3, with the database seeded as today:

1. `python -m app.evaluation.run_retrieval_eval` matches `eval/results/retrieval/2026-11-05_a0_baseline.txt` line for line, on
   both the 14- and the 12-question set.
2. The model's input is unchanged: `tests/test_agent_text_pinned.py` passes against `agent_text_c907a33.json`.
3. Every course lookup is unchanged: `python -m app.evaluation.dump_course_lookups` (every course code, every referenced code
   without a course row, and two codes that don't exist, each with and without the prerequisite chain) matches
   `eval/results/courses/2026-11-15_a2_3_before.txt` byte for byte.
4. Content is unchanged: 1,161 chunks, 660 courses, 526 prerequisites, chunk texts byte-identical to `chunks.jsonl`, also after
   the in-place migration of a copy of the production backup.
5. A test with two editions of one document proves the superseded one never surfaces in search or course lookups, that
   `activate` flips them in one transaction and records who and when, and that rollback flips them back.

If any of these fails: stop and report, don't adjust. 0 LLM tokens.

Sub-step 0 done 2026-11-15 (`5e0d7e0`): the capture, 1,376 lookups, sha256 `93d5a841...`, the same on two runs. Sub-step 1
done 2026-11-15, the schema: `courses` keyed on `(source, code)`, `course_prerequisites.source` with its key and a foreign key
into the same edition's course, and foreign keys from chunks and courses to `document_editions`. The local database, holding
data, was converted in place by `app.db.migrate` (run twice): `deploy/backup/fingerprint-a2.3-content.sql`, which hashes the edges
on their old columns, gave the same output before, after, and after re-seeding courses; the lookup capture matched byte for byte;
the retrieval eval matched the A0 baseline line for line; a fresh database and the converted one have the same 68 lines of
constraints and columns. `tests/test_schema_editions.py` runs the conversion from the old shape inside a rolled-back transaction.
Two `verify_role` probes needed a real edition (an insert) or `CASCADE` (a truncate), because as the owner the new foreign keys
refused them before the privilege question was asked; as `campus_api` they are still denied by privilege. `fingerprint.sql`
orders courses and edges by edition first; its `course_prerequisites` hash changes once, because the row gains `source`, so a
restore drill of a dump from before A2.3 differs on that one line (noted at the deploy). Item 4 on a copy of the production backup
is still to do, at the deploy.

Sub-step 2 done 2026-11-15, the filter: `app/editions.py`'s `SOURCE_IN_FORCE` (a subquery on the registry: active edition,
public document) is in the WHERE clause of vector search, keyword search, the course lookup and the referenced-code check, and
the prerequisite walk reads edges and titles from the found course's edition only. A subquery and not a cached id list, so a
status change applies to the next request. `tests/test_editions_in_force.py` puts a superseded, an active and a non-public
edition side by side and checks only the active public one surfaces, that a status change applies at once, and that a withdrawn
edition isn't searched. Checked by mutation: with the filter replaced by `true` all 8 tests fail, and removing any one of the
walk's three edition conditions fails the chain test. Lookup capture byte for byte and retrieval eval line for line, both
unchanged: with no approximate vector index the scan is exact, so a filter that removes nothing can't reorder.

Sub-step 3 done 2026-11-15, ingestion per edition: `store.py --replace` and `--sections-only` touch only the editions in
`chunks.jsonl` (before, `--replace` deleted every document's chunks of the model), and an empty replace is refused.
`courses.py` replaces one edition's courses and edges in one transaction with `replace_course_rows` (before: all edges deleted,
outside a transaction, and a course a new extraction lost stayed answerable). Both print per-edition counts as proof. Tests in
`test_store_replace.py` and `test_seed_courses.py`, mutation-checked: unscoping each delete, or dropping the course replace's
transaction, fails them. On the real data, re-seeding and `--sections-only` left the content fingerprint and the lookup capture
unchanged. Not run on the real data: `--replace` itself, because re-embedding 1,161 chunks may not reproduce the vectors bit for
bit, which would change the fingerprint for a reason that isn't A2.3; its scope is covered by the tests.

Sub-step 4 done 2026-11-15, `python -m app.registry activate <edition> --by <who>`: in one transaction it locks the document's
editions, supersedes the active one, then activates the named one with `activated_by` and `activated_at` (that order because the
one-active index is checked row by row). The rollback is the same command with the previous edition. It refuses an unknown,
already active or withdrawn edition, an empty `--by`, an edition with no chunks (its document would vanish from search) and a
course-tables edition with no courses; each refusal says "Nothing changed" and exits 1. It prints the document's statuses read
back from the table. `tests/test_activate.py` (rule item 5): activation and rollback each change the next search and course
lookup, both editions keep their rows, and a failure injected between the two updates leaves the old edition in force.
Mutation-checked: without the transaction, that test fails. Run against the real local database, activating the edition already
in force is refused. No request-path code changed in this step.

Sub-step 5 decision, set 2026-11-15 by Claude with Youness's go-ahead to decide, before its code. Of the generated text, only the
interface's names the edition (`catalog_label`, `catalog_card_title` and the two sentences built from them: the composer note
"Answers are based on the Academic Catalog 2024–2025", the first screen, the About page and its limitations line); what the model
reads names document types, never a year. Status lives in the database, so text that depends on it is read at runtime: a new
`GET /editions` serves the editions in force (the same `IN_FORCE_EDITIONS_SQL` as the searches), and the interface takes the
catalog's label and card title from it, falling back to the generated build-time text while it loads or if the API doesn't
answer, as the About page does with `/limits`. Rejected: naming the edition in force in the registry file (status in the file; a
rollback would leave the interface claiming the newer year until a redeploy), generating for the newest edition (the same after a
rollback), and dropping the year (changes what students see today, against this rule). The generator keeps refusing two editions
of one document: accepting them needs `seed_courses` to take an edition and the one-course-tables-edition rule to become per
document, which belong to A2.6 with the second catalog. Done in two turns, 5a the endpoint, 5b the interface. Accepted if: with
one edition, every interface text renders exactly as before, once loaded and on the fallback (vitest); `scope.json` and the
model's input unchanged; `/editions` serves active public editions only, and in a two-edition test `activate` and its rollback
change what it serves; it isn't counted against the demo limits and logs nothing; the CSP check's first screen stays at zero
violations with the new request.

Sub-step 5a done 2026-11-15: `GET /editions` (`app/main.py`, query in `app/editions.py` on `IN_FORCE_EDITIONS_SQL`) serves
`{"editions": [{id, document_id, label, card_title, course_tables}]}`; a database failure gets a fixed 503 and logs nothing.
`tests/test_editions_api.py`: with the real data the catalog's card title and label equal `scope.json`'s; with two editions it
serves the active public one only, and `activate` and its rollback change that; not counted in `question_log`; the failure's text
reaches neither the response nor the logs. Mutation-checked: without the filter, two tests fail. The interface doesn't read it
yet (5b).

Sub-step 5b done 2026-11-15: `frontend/src/editions.ts` fetches `/editions` once per page (shared by every component), takes the
one catalog edition only if exactly one is in force (anything else: the built-in text), and swaps its year into the generated
sentences with `withEdition`. The composer note, the first screen, the About page and its limitations line use it.
`src/editions.test.tsx` (jsdom): with today's edition every text reads as before; with a newer one all four name it; on a failed
request the built-in text stays; one request per page; each generated sentence holds the built-in year exactly once.
`scope.test.tsx`, unchanged, still passes: it renders without effects, so it pins the fallback. Mutation-checked: a hook that
ignores the answer fails the newer-edition test. In the local app in Chrome (0 tokens): the real `/editions` answered 200 with the
CORS header and the page read as today; a newer edition served in the browser changed all four places; a 503 kept the built-in
text. The CSP check of the first screen with the new request runs at the deploy (sub-step 6).

## A2.4 rule

Set 2026-11-18 by Claude, with Youness's go-ahead ("go with your recommendations"), before any A2.4 code, following the rule
of recording a decision rule before seeing the numbers. A2.4 makes ingestion per edition and driven by the registry: one loader
interface (`PdfLoader`, `WebLoader`), sanitising, scans with recorded decisions, a dry run that runs every check and reports a
verdict, and ingest that writes only draft editions. With today's three editions nothing a student sees may change. 0 LLM tokens.

**Decisions, same date:** (1) a table too big for one chunk is refused by the dry run; section 4.2's parent-child retrieval waits
for B1/B3. (2) A non-English edition is refused until B3, which owns per-row French search: the `english` full-text configuration
would stem French silently wrong. (3) Ingest writes only draft editions; an active edition's rows are never replaced in place,
so A2.5's lorem ipsum fix is a new edition plus `activate`. (4) An optional edition field `layout = "aui_catalog"` switches on the
catalog-only rules (`LEVEL_HEADINGS`, `PAGE_HEADER_LINES`); other documents get plain chunking. Ingestion-only, not synced.
(5) PDF hidden text (tiny or background-coloured fonts) stays in B1, whose row already holds the hidden-text scan.

**Check methods, written before any is computed.** Values come from today's files once, in the sub-step that builds the check.

- Size: refuse a PDF over 20 MB or 1,000 pages, an HTML file over 2 MB (largest today 2.8 MB, 435 pages).
- Scanned or image-only: a page is near-empty when it holds fewer than 50 non-whitespace characters after its page-header lines
  are removed (`PAGE_HEADER_LINES` for `aui_catalog`; otherwise lines repeated on more than half the pages). Refuse when the
  share of near-empty pages is above the larger of 5% and twice the 2024-2025 catalog's share.
- Encoding: refuse above 1 per 10,000 characters of U+FFFD plus mojibake sequences (`Ã`, `â€`). Seen before this rule while
  checking the raw text on 2026-11-18: 0 U+FFFD in all three files; mojibake not yet counted.
- Headings: refuse below 80% of the previous edition's count for the same document; with no previous edition, report only.
- Courses (the `course_tables` edition): refuse below the previous edition's count, and list codes found in text but not
  extracted; with no previous edition, report only.
- Chunks over 512 tokens: refuse (the existing check).
- Table-like PDF pages (D6): a page is table-like when at least 10 of its non-empty lines have 3 words or fewer and they are at
  least 60% of its lines. Refuse when the share is above 1.25 times the 2024-2025 catalog's. Reported for every PDF.
- Sanitising, removed and counted: zero-width, bidi-control and BOM characters; HTML elements with `hidden`,
  `aria-hidden="true"`, or an inline style with `display:none`, `visibility:hidden` or `font-size:0`. Today's files hold none
  of either (checked 2026-11-18), so sanitising them changes nothing.
- Scans. **Refuse:** a Moroccan national ID (one or two capital letters then 5 or 6 digits, as one token); boilerplate (`lorem
  ipsum`, `dolor sit amet`). **Hold for a decision:** phone numbers (`+212` or a 0 then 5, 6 or 7, then 8 digits, separators
  allowed); email addresses; "student ID/number/no." followed by 4 or more digits; IBAN (`MA` + 26 digits) or a 24-digit RIB;
  an honorific (Mr, Mrs, Ms, Dr, Prof) followed by a capitalised word; instructions to a model in EN or FR ("ignore/disregard
  ... previous/prior/above instructions", "ignorez/oubliez ... instructions", "you are now", "system prompt"), role markers at a
  line start (`system:`, `assistant:`, `user:`) and chat tokens (`<|im_start|>`, `[INST]`, `<<SYS>>`). A hold needs a decision
  (allow, redact, refuse) in a committed `data/review/<edition>.toml`; a hold without one refuses. A pattern changed after
  seeing hits is changed in the open, with the reason.

**Sub-steps, one per turn:** 0. this rule, the fixtures and their questions; 1. loaders; 2. registry-driven ingest with its gates
(hash, size, visibility, language, format, no folder scans, `layout`); 3. sanitising and HTML tables; 4. scans and decisions;
5. the dry-run report, `parser_version`, `quality_report`, draft-only ingest; 6. download hardening (host allow-list from the
registry, no off-host redirects, timeout, size cap, hash printed); 7. the fixture check. Deployed with A2.5, since nothing
changes for students.

After A2.4, with today's three editions:

1. The dry run's chunks are byte-identical to `chunks.jsonl` (1,161), with identical metadata (pages, level, section, sections,
   language).
2. `python -m app.evaluation.run_retrieval_eval` matches `eval/results/retrieval/2026-11-05_a0_baseline.txt` line for line, on
   both the 14- and the 12-question set.
3. The model's input is unchanged: `tests/test_agent_text_pinned.py` passes against `agent_text_c907a33.json`.
4. Every course lookup matches `eval/results/courses/2026-11-15_a2_3_before.txt` byte for byte.
5. The only refusal on today's files is the lorem ipsum in `graduate_scholarships` (A2.5's). Holds get recorded decisions, listed
   in the commit.

On a scratch database (`campus_scratch` on the local container; the real editions' rows copied, not re-embedded; never the dev
database or the VM), with the three fixture documents in `backend/tests/fixtures/ingestion/` (dining, finance, a second
academic source; invented, and their questions and anchors written in sub-step 0, before any search ran on them):

6. Attribution: every fixture question's anchor is in the top 5, from its fixture's edition, with that edition's card title.
7. Coexistence: with the fixtures active, no question of the real 14- or 12-question set that was hit is lost; rank changes are
   reported.
8. Withdrawal: for each fixture in turn, ingested last, activated and then withdrawn, every search (fixture and real questions)
   returns exactly what it returned before that fixture was ingested (source, chunk index, score), and every other edition's
   chunk count is unchanged. With all three withdrawn, the real eval matches the A0 baseline line for line.
9. Refusals, each with a test, mutation-checked: unknown format, hash mismatch, non-public, non-English, encrypted PDF,
   near-empty (scanned) PDF, oversized file, national ID, instruction, boilerplate, off-host redirect, a table too big for one
   chunk, and no chunk holding part of a table without its header row.

If any of these fails: stop and report, don't adjust.

Sub-step 0 done 2026-11-18 (`ec3e7b2`): the fixtures and their questions. Sub-step 1 done 2026-11-18 (`f8596d8`):
`app/ingestion/loaders.py`. Sub-step 2 done 2026-11-18: `clean.py` reads only registered editions, each through
`app/ingestion/gates.py` (visibility, language, format, file present, size, sha256, PDF pages), checks all before writing
any, and reports other files in `data/raw` as ignored; `chunk.py` takes `ChunkSettings` from the edition (`layout`,
language, starting level) instead of catalog constants and a hardcoded `en`; the registry gained `layout` and
`read_documents(path, allowed_host)` + `registry_of`, so the fixture file reads on `fixtures.invalid` and joins the real
registry. On the real data `clean` and `chunk` rewrote the three texts and `chunks.jsonl` byte-identical. 23 mutations, all
caught. Sub-step 3 done 2026-11-18: `app/ingestion/sanitise.py` removes and counts the rule's 17 invisible code points and
hidden HTML elements (`clean` prints both counts: 0 and 0 on today's files); `WebLoader` turns each outermost HTML table into one
Markdown block, header row first (the `<thead>` row, else the first row), rows padded, `|` escaped, a caption above it; the
chunker joins a Markdown table into one unit (`join_tables`), so it is never split, and never carries it over as overlap. A
table over the token limit becomes one oversized chunk, which the dry run's token check refuses (step 5). Real data
byte-identical again; 20 mutations caught (two first broke syntax and were re-run as valid code). Sub-step 4, code done
2026-11-18: `app/ingestion/scan.py` with the rule's patterns and `data/review/<edition>.toml` decisions (allow, redact, refuse;
`value` is an fnmatch pattern; refused kinds can't be decided; unused decisions are reported); `python -m app.ingestion.scan
--all` changes nothing. 14 mutations caught. First run on today's files, read-only: catalog 86 holds (67 honorific + name, 40
distinct: president, trustees, deans, program leads; 14 emails, 11 distinct, all `@aui.ma`, one a named person's; 5 phones, one a
false positive on the IELTS/TOEFL score table, p. 39, kept as a hold, pattern unchanged), no ID, instruction, student or bank
number; `graduate_scholarships` refused for its "Lorem Ipsum" only (rule item 5 holds); `prestigious_scholarships` 0 hits.
Decided by Youness after reading every hit, 2026-11-18, `data/review/academic_catalog_2024_2025.toml`: allow all (`*@aui.ma`,
the five phone hits each with its reason, every honorific + name), so nothing a student sees changes. Re-scan: the catalog passes,
no unused decision, nothing redacted; `tests/test_scan.py` pins that where `data/raw` exists, and checks in CI that every
committed decisions file loads for a registered edition.

## A2.2 rule

Set 2026-11-06 by Claude, with Youness's go-ahead on A2.2, before any A2.2 code, following the rule of recording a decision rule
before seeing the numbers. A2.2 moves text, it doesn't change what the model is told. After A2.2:

1. The system prompt template and both tool schemas match `backend/tests/fixtures/agent_text_c907a33.json`, byte for byte.
2. `python -m app.evaluation.run_retrieval_eval` matches `eval/results/retrieval/2026-11-05_a0_baseline.txt`, line for line.

If either differs: stop and report, don't adjust. 0 LLM tokens: identical input to the model needs no new answers. Wording
changes belong to A2.7.

## Uncited answers check

Set 2026-11-06 by Claude, with Youness's go-ahead to decide, before the sample was run, following the rule of recording a
decision rule before seeing the numbers. `docs/architecture.md` section 2.4 calls the A2.6b gate safe because run 3's only
answers without citations were correct refusals. The deploy check of A2.1 saw real answers without citations, so that evidence
needs testing before A2.2 changes the prompt.

Sample, one attempt each, on the code deployed at `c907a33`: `transfer_credits_en`, `transfer_credits_fr`, `plagiarism_en`,
`add_drop_en`, `excused_absences_fr`, `course_load_en`, `academic_probation_fr`, `repeat_course_en`, `w_grade_fr`,
`scholarship_conditions_en`, `scholarship_work_hours_fr`, `acc2302_chain_en`. An answer counts as uncited if it called a tool,
has no valid marker, and isn't a refusal when read by hand. Errors are reported and don't count.

- At most 1/12 uncited: the evidence stands, and the order doesn't change.
- 2/12 or more: stop and report, don't adjust. Section 2.4's evidence no longer holds, so A2.6b can't ship on it: the gate would
  turn those answers into false refusals, which count against the pilot threshold's limit of 2/30.

Result, 2026-11-06: **1/12** (`add_drop_en`, a real answer of 2,162 characters), 0 errors, 45,473 tokens, so the order doesn't
change. `eval/results/faithfulness/answers_citation_check_2026-11-06.jsonl`. 1/12 is a small sample and isn't zero: at that
rate about 2.5 of 30 would become false refusals under the gate, against the limit of 2/30, so A2.6b has to count them.

## How to run

Full setup from a fresh clone is in the README ("Running it"). Day to day:

```powershell
docker compose up -d db                        # repo root
cd backend; .\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000      # API
cd frontend; npm run dev                       # UI on http://localhost:5173

cd backend; pytest -q; ruff check .; ruff format --check .
cd frontend; npm run lint; npm test; npm run build
python -m app.evaluation.run_retrieval_eval    # in backend\, database seeded
```

Deployment (Azure VM, Docker Compose + Caddy): `deploy/DEPLOY.md`. Updates are a `git archive`
copy of HEAD to the VM, then `bash deploy/update.sh`; SSH by the DNS name (that's the host key in
known_hosts).

## Current status (2026-11-15)

- **A2.3 (per-edition storage, the edition filter, `activate`) is accepted and deployed (`dade4da`, 2026-11-15)**, see "A2.3
  rule" and `deploy/DEPLOY.md` (A2.3). Rule items 1-5 held: retrieval eval and every course lookup unchanged, the model's input
  unchanged, content unchanged (also after the migration of a VM-local copy of production), and the two-edition tests. A newer
  edition is added as draft, ingested, then `python -m app.registry activate <edition> --by <who>`; rollback is the same command.
  The interface reads the catalog edition from `GET /editions`. Still one edition per document in the file until A2.6 (scope
  generator, course seeding). Next in the A2 order: A2.4.
- **A2.6b (answer-level gate and its one retry) is accepted and deployed (`8011e99`, 2026-11-15)**, after the retry rule's step 3
  passed (0/24 replaced on 2026-11-14, 0/6 on the follow-ups on 2026-11-15), see "A2.6b rule". Both retried follow-up answers got
  refund/deadline rules wrong (`retry_summer_refund_deadline`), for A2.7/A2.8. Next in the A2 order: A2.3. The gate
  (`app/agent/gate.py`) is the graph's last node. `/chat` holds the answer until it has run and sends it whole, so students no
  longer see text arrive word by word. See "A2.6b rule" for the measurement.
- **A2.2 (generated scope text) is accepted and deployed (`8472f3b`, 2026-11-06).** `python -m app.scope` writes `backend/app/scope.json` and `frontend/src/scope.json` from the registry: run it after
  changing the registry, and commit both. Tests pin both files to the registry and `frontend/index.html` to the text, but the
  description in `index.html` is copied by hand. The text comes from the file, not the database's status, so a document with
  two editions stops the generator until A2.3 decides. Measured: the model's input matches `c907a33` byte for byte
  (`tests/fixtures/agent_text_c907a33.json`), also inside the built API image; the retrieval eval is byte-identical to the A0
  baseline (`eval/results/retrieval/2026-11-06_a2_2.txt`); and the rendered interface is unchanged except "the catalog
  passages" became "the document passages" on the diagram. 0 LLM tokens.
- **A2.1 (registry) is accepted and deployed (`c907a33`, 2026-11-06).**
  `data/registry.toml` is the one list of documents. Only the CLI and ingestion read it, inside functions and never at
  import, because the API's image doesn't hold it: the API reads `documents` and `document_editions`, with SELECT only.
  `python -m app.registry sync` never changes an existing edition's status; `--initial` works only on empty tables, and
  plain sync refuses them. A one-shot `registry-sync` service mounts the one file read-only, and the API waits for it.
  `bash deploy/update.sh` stops on 0 rows. Measured: `eval/results/retrieval/2026-11-06_a2_1.txt` matches the A0 baseline
  line for line (91 lines), chunks byte-identical to `chunks.jsonl`, content fingerprints unchanged after re-seeding courses.
  On the VM the PDF link matches the old code's, and source card titles are unchanged. Seen in the deploy check, not
  measured: two answers to "How many credits can I transfer to AUI?" and one to a similar question came back with no source
  cards. The one inspected in full has no `[N]` markers in its text. This is AG-3, whose gate is A2.6b; see "Uncited answers check".
- **A1 is complete (A1.1-A1.5) and A0 is recorded.** Deployed: no images in answers (A1.1),
  browser headers with the CSP enforced (A1.2), request limits (A1.3), the API connecting as `campus_api`
  with migrations in a one-shot `python -m app.db.migrate` and a gate in `app.db.verify_role` (A1.4), and
  daily off-VM backups (A1.5). Migrations and ingestion still run as the owner superuser.
- `docs/architecture.md` is committed: A1 is deployed and Youness reviewed what it says about open findings
  (D4). Its data-protection detail and the questions for AUI are in `docs/private/`, gitignored.
- Dates: reassess Caddy 2.11.9 on 2026-11-19 (CD-2: the newest release at least two weeks old, after reading
  its changelog). Next restore drill due by 2026-12-06.
- A1.5: a systemd timer on the VM pipes `pg_dump` into `age` and pushes to Backblaze B2 (Object Lock,
  compliance, 30 days; lifecycle 45 + 1 under `db/`), with a Healthchecks.io ping and `/fail`. Runbook in
  `deploy/DEPLOY.md`. First scheduled backup ran 2026-11-06 03:32 UTC: `BACKUP OK` and `PING OK` in
  `journalctl -u campus-backup.service`, 2,678,146 bytes, retention to 2026-12-06, 526 prerequisites, 660
  courses and 1,161 chunks. Healthchecks.io shows OK.
- A1.3 limits: 64 KiB bodies in Caddy and in a pure ASGI middleware (`app/request_limits.py`); question
  1-2,000 characters, at most 20 messages, user 2,000 and assistant 6,000 characters, unknown fields
  refused. A rejected request gets a fixed 413 or 422, isn't counted and logs no body text. The UI has
  a counter at the composer, and `historyToSend()` drops whole turns to fit.
- Enforced CSP measured on 2026-11-05: zero violations in Chrome 156, Playwright's Firefox 157 and
  WebKit 27.2, and checked by hand on a real iPhone.
- Before the university proposal, deployed 2026-11-04: daily cap 35 (100 doesn't fit Groq's
  200k tokens/day), a personal-information notice under the composer (language = browser's), and
  logs without question text or visitor IPs (rotation on every container, Caddy log filter).
- Showcase work (Under the hood panel, About page, first screen) done and deployed (e77a80b,
  2026-10-30). Two examples (ACC 2302, transfer credits) were regenerated with their trace;
  the two French ones keep their 2026-10-19 answers and replay without a panel.
- All phases done and deployed. Repo is public, CI badge in the README. Faithfulness: run 3
  (after fixes A-C) 6/26 main answers with an unsupported cited claim vs. 17/47 at baseline
  (confidence intervals overlap); details in the README.
- Left: demo video; the Namecheap domain, waiting on Namecheap's verification. The VM's public
  IP is static (Standard SKU, 9.205.31.42), so an A record to it is safe. The Azure address stays
  the official link: the new hostname is added as a second site address in `deploy/Caddyfile`
  (no CORS change: the UI calls `/api` on its own origin); deploy only once it resolves.
- is-a.dev was checked (2026-10-23) and doesn't fit: its terms and PR template exclude AI
  chatbots and course-oriented sites, and it bans AI-assisted pull requests.
- Open problems (README "Known limitations" / "Future work"): everyday wording missing passages
  written in the catalog's vocabulary (candidate: a multilingual reranker), citation placement
  (Fix D), the undergraduate/graduate level filter, a re-ingest of the newer catalog editions.

A full development and decision log exists locally as `SESSION_LOG.md` (gitignored, not in the
public repo). Read the relevant part when history matters (why a decision was made, past
measurements, evaluation details).

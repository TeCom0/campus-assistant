# Campus Assistant: architecture and security design

**Status:** approved with changes on 2026-11-05 (decisions below; tier A split into A1 and A2). A0 and A1
are done and deployed. A2 is next.

**This repo is public.** So this document states what is still open without measured detail, and keeps a
measured value only for a finding that has been fixed: "was X on 2026-11-05, fixed <date> (<commit>)".

**Goal:** grow from a demo that answers from one catalog into an assistant that could serve the
whole university, with documents from many departments. Design for that future, build only what
is needed now, in priority order.

## How to read this document

Every claim about the current system carries its evidence type:

| Mark | Meaning |
| --- | --- |
| **[M]** | Measured on 2026-11-05: live site, production VM (read-only), GitHub or Azure settings, or a probe on the repo's data. |
| **[C]** | Read in the project's own records at commit `4e5300a`: code, configuration, README, evaluation files or the local session log. A path is given where useful. |
| **[R]** | Read in the external source named, listed in section 11 with what was and wasn't read. |
| **[K]** | Cited from general knowledge, not re-read for this document. Check before relying on it. |
| **UNSURE** | I don't know, or the evidence is thin. Never a guess presented as fact. |

Ratings: **L**ikelihood and **I**mpact are each Low, Med or High, judged for the system as it would
be at a student pilot, not just today's quiet demo. They are judgement, not measurement.

Steps like **A1.3** refer to the roadmap in section 9. **Q1 to Q12** are open questions for AUI, kept outside
this document.

---

## Summary

### The findings that matter most

| # | Finding | Evidence | Fix |
| --- | --- | --- | --- |
| 1 | **The Azure credit runs out around January 2027.** Microsoft then disables the services and the subscription. Encrypted off-VM backups have existed since 2026-11-06 (7812662); where the service runs next is still undecided. | Microsoft's page [R]. | D1 |
| 2 | **Some cited answers still contain an unsupported claim.** This is the largest real risk to students, and it now has a pilot threshold. | Figures are in the README's Evaluation section. | D3, A2.6-A2.8, B24 |
| 3 | **Model-written Markdown images rendered.** Was: a poisoned document or jailbreak could make a visitor's browser send text to an outside server with no click, with no CSP as a second layer, on 2026-11-05. Fixed 2026-11-05 (330a248, ce1d9a3). | Tested on the live site in three browsers [M]. | Done (A1.1, A1.2) |
| 4 | **No size limit on any `/chat` input.** Was: unbounded at Caddy and in the API on 2026-11-05. Fixed 2026-11-05 (b876aa2, ce1d9a3). | 413 and 422 from the live site [M]. | Done (A1.3) |
| 5 | **The API connected to Postgres as a superuser.** Was: `rolsuper = t` on 2026-11-05. Fixed 2026-11-05 (81b89ec). | Checked by a gate in CI and at each deploy [M]. | Done (A1.4) |
| 6 | **The per-IP limit will treat the whole campus as one visitor** if campus Wi-Fi shares an address: 5 questions per 10 minutes for everyone. | Limit logic [C]; UNSURE whether AUI uses NAT (Q9). | B25 |
| 7 | **The free Groq tier cannot serve a pilot, and no fallback is deployed.** Its limits suit light use only, and Gemini's free tier forbids personal data. | Provider rate limits [R]; deployed configuration; Gemini terms [R]. | D2, B18, B25 |
| 8 | **Superseded data would stay answerable.** Chunks and courses have no edition, and the course upsert keeps removed courses. | `courses.code` is the primary key; `replace_rows` deletes per model, not per document [C]. | A2.3 |
| 9 | **The software supply chain is largely unpinned.** CI and the VM install whatever is newest on the day, so what was tested isn't what runs. Was also: secret scanning off and Caddy two years old on 2026-11-05. Fixed 2026-11-06 (GitHub setting; 22835b1). | No Python lockfile [C]. | B21 |

### What already works and should be kept

- Raw HTML in answers is escaped; `javascript:` and `data:` URLs are stripped (tested [M]).
- All SQL in the request path is parameterised; `/sources/` can't be an open redirect because it
  looks targets up in a fixed list [C].
- TLS 1.0 and 1.1 are refused, 1.2 and 1.3 work, HTTP redirects to HTTPS [M]. Only 80, 443 and SSH
  are reachable, and SSH only from one address [M].
- Logs hold no question text or visitor IP, and a test enforces it [C]. IPs are stored only as an
  HMAC, for 2 days [C].
- SSH is key-only, security updates are automatic, and `.env` is mode 600 [M].
- A full-history gitleaks scan was clean on 2026-10-21 [C]. Dependency audits become routine in B21.
- The agent's tools can only read, and there is a code-enforced tool-round budget [C].
- Lighthouse on the first screen, simulated mobile: performance 97, accessibility 100, LCP 1.8 s,
  218 KiB [M]. This covers one screen and automated checks only; see section 8.

### Decisions taken on 2026-11-05

| # | Decision | Outcome |
| --- | --- | --- |
| D1 | Hosting after the Azure credit | Youness asks AUI and checks the balance at microsoftazuresponsorships.com/balance. If AUI hasn't answered by 2026-12-01, upgrade to pay-as-you-go ($37-45/month). |
| D2 | Groq plan for the pilot | **Paid Developer plan.** About $0.0005 per question at list price. An account action for Youness, not done yet. |
| D3 | Pilot threshold | **Accepted, with item 4 reworded** (section 2.4), and recorded in CLAUDE.md before run 4. The answer-level gate moves into A2 (A2.6b) so that item can be measured. |
| D4 | When to publish this document | Commit it **once A1 is deployed**, after a review of what it says about findings still open. Items in tier B stay open at that point, and the document names them without measured detail. |
| D5 | Prestigious-scholarships page | **Drop it** (A2.5). |
| D6 | PDF tables | **Tier B** (B1). HTML tables stay whole in A2.4, and a table-heavy PDF is refused until B1 is done. |
| D7 | Legal basis for sending questions to the model provider | Handled privately with AUI's legal contact; a data-protection review is a pilot exit criterion. |
| D8 | The 2025-2026 PDF | Ask AUI (Q7). A2.6 is blocked until then. |

---

## 1. Threat model

### 1.1 Components and trust boundaries

```
 Student's browser (untrusted input; renders untrusted model output)
        | TB1  internet, TLS
 Azure NSG -> Caddy (TLS, routing, headers)
        | TB2  private Compose network, plain HTTP
 API (FastAPI) -> Agent (LangGraph) -> Tools (search_documents, query_courses)
        | TB3  plain Postgres protocol       | TB4  internet, TLS, API key
 Postgres + pgvector                         Groq (US) [Gemini: not deployed]
        ^ TB5  a dump restored over SSH
 Ingestion, on the developer's laptop <- TB6 - AUI documents (untrusted content)

 GitHub + Actions (CI only; holds no deploy credentials or secrets)
        | TB7  laptop copies a `git archive` to the VM over SSH; VM builds images
 Azure VM (Docker host; holds every secret)
```

**The central idea for this project.** A model cannot reliably tell instructions from data. OWASP
itself says it is "unclear if there are fool-proof methods of prevention" for prompt injection
[R]. So the design assumes injection sometimes succeeds, and limits what a successful one can do.
Damage needs three things at once: private data, untrusted content, and a way to send data out
(Simon Willison's "lethal trifecta" [K]). The first two remain: the conversation and the documents.
**Removing the exit channel matters more than any prompt wording:** images have been off since
2026-11-05 (A1.1), with a CSP behind them (A1.2), and links now need a click until B19.

### 1.2 Browser

| ID | STRIDE | Threat | L | I | Current mitigation | Gap | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BR-1 | I, T | Model output contains a remote image; the browser fetches it without a click, carrying text the model put in the URL | Med | High | Images render as their alt text; CSP `img-src 'self'`; hostile-Markdown tests | Was: a live `<img>` rendered and no CSP existed, on 2026-11-05. Fixed 2026-11-05 (330a248, ce1d9a3) | Done (A1.1, A1.2) |
| BR-2 | S | A model-written link can look official and go anywhere | Med | Med | `rel="noreferrer"`, new tab [C] | Links aren't limited to known hosts | Link only registry hosts; others become plain text (B19, after A2.1) |
| BR-3 | E | XSS through model or document text | Low | High | HTML escaped, `javascript:` stripped; enforced CSP | Was: no second layer on 2026-11-05. Fixed 2026-11-05 (ce1d9a3) | Done (A1.2) |
| BR-4 | T | Clickjacking | Low | Low | CSP `frame-ancestors 'none'` | Was: no `frame-ancestors` on 2026-11-05. Fixed 2026-11-05 (ce1d9a3) | Done (A1.2) |
| BR-5 | I | A later user of a shared computer sees the conversation | Low | Low | Held in memory, gone on reload [C] | None | Keep this design |
| BR-6 | R | A student disputes what the assistant said; nothing records it | Med | Med | Questions aren't stored, by design | No way to investigate a report | Edition line in every answer, a "copy answer with sources" button, report link with student-chosen content (B24, B26) |

### 1.3 Caddy

| ID | STRIDE | Threat | L | I | Current mitigation | Gap | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CD-1 | D | Oversized request bodies reach the API | High | High | 64 KiB limit at Caddy and in the app | Was: no `request_body max_size` on 2026-11-05. Fixed 2026-11-05 (ce1d9a3, b876aa2) | Done (A1.3) |
| CD-2 | T, E | Known flaws in an old proxy | Med | Med | Current release, pinned by digest | Was: `caddy:2.8.4-alpine`, about two years old, on 2026-11-05. Fixed 2026-11-06: 2.11.7 (22835b1). Scanning stays in B21 | Done. Keep it current: the newest release at least two weeks old, after reading its changelog |
| CD-3 | I | Missing browser protections | Med | Med | HSTS, nosniff, Referrer-Policy, CSP, Permissions-Policy, COOP | Was: no CSP, frame policy or Permissions-Policy on 2026-11-05. Fixed 2026-11-05 (94ab416, ce1d9a3) | Done (A1.2) |
| CD-4 | S | TLS downgrade or certificate problems | Low | High | TLS 1.2+, automatic renewal | No alert if renewal fails | External check of certificate expiry (B27) |
| CD-5 | D | Connection floods, slow clients | Med | Med | Azure's platform protection (UNSURE of its depth on a Basic setup); timeouts for slow clients | Was: no server timeouts set on 2026-11-05. Fixed 2026-11-06 (22835b1). Caddy core still has no rate limiting [K] | Edge service if abuse appears (C) |
| CD-6 | R | Logs are deliberately minimal, so an attack is hard to reconstruct | Med | Low | Privacy-first log filter [C] | No counts of 4xx/5xx | Aggregate request metrics with no IP or content (B27) |

### 1.4 API

| ID | STRIDE | Threat | L | I | Current mitigation | Gap | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AP-1 | D | Huge `question` or `messages`: memory, tokeniser and full-text CPU, tokens | High | High | Limits in section 2.1, checked before the demo limits | Was: history capped at 10 messages, each unbounded, on 2026-11-05. Fixed 2026-11-05 (b876aa2) | Done (A1.3) |
| AP-2 | D | One visitor uses the whole day's quota | High | Med | Per-IP limit [C] | The per-IP limit doesn't stop one determined visitor from using up the daily cap | Per-code limits, daily per-user limit, token budget (B25) |
| AP-3 | D | Campus NAT: every student shares one limit | High | High | None | UNSURE until Q9 is answered; a typical campus setup | Per-code limits in the pilot (B25); SSO later (B2) |
| AP-4 | I | `/api/docs`, `/api/redoc`, `/api/openapi.json` are public | High | Low | Off unless `ENV=development` | Was: public, returning 200, on 2026-11-05. Fixed 2026-11-06 (24cb771) | Done |
| AP-5 | D | Admission's database call can delay other streams | Med | Med | Connect timeout [C] | It runs on the event loop | Run it in a thread pool (B20) |
| AP-6 | I | Validation errors echo client input | Low | Low | A fixed 422 body | Was: FastAPI's default 422, with `input`, on 2026-11-05. Fixed 2026-11-05 (b876aa2) | Done (A1.3) |
| AP-7 | S | No identity: any client is "a student" | High | Low now, High with non-public documents | Public documents only | Nothing distinguishes users | Access codes (B25), SSO (B2). Non-public documents refused until then (section 3.7) |
| AP-8 | R | No record of runs, outcomes or admin actions | High | Med | Exception type only | Failures can't be analysed | Content-free event log (B27) |
| AP-9 | T | Client forges earlier "assistant" turns | High | Low | Markers stripped, capped [C] | Client-supplied history is trusted | **Accept, with size limits.** It affects only the attacker's own session, and gives no more power than typing the same words. Signed history isn't worth it while there is no server-side state to protect |
| AP-10 | D | A run has no overall deadline; UNSURE whether a client disconnect cancels the run | Med | Med | Step cap [C] | No overall deadline per run | 60 s deadline, disconnect test (B20) |

### 1.5 Agent

| ID | STRIDE | Threat | L | I | Current mitigation | Gap | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AG-1 | T | **Indirect prompt injection:** a department document carries instructions to the model | Low today, Med with many departments | High | Documents are public and few; exit channels closed | Passages aren't yet marked as data, or scanned for hidden content | Sections 2.5 and 4.4 (A2.4, B24) |
| AG-2 | S, T | **Direct injection and jailbreaks** | High | Low-Med (reputation, off-topic use of quota) | "Answer from tools" in the prompt [C] | Prompt-only, and CLAUDE.md records that prompt-only rules fail here | Gate: uncited model text never reaches a student, with an off-topic and injection eval category (A2.6b); planted-document adversarial tests (B24) |
| AG-3 | T | Uncited or invented-citation answer reaches a student | Med | High | Unknown markers stay plain text; `keep_cited` lists real ones [C] | Nothing stops an answer with no citation. An earlier run did cite a `[1]` no tool returned [C] | Gate (A2.6b) |
| AG-4 | T | **Misinformation:** the citation is real, the claim isn't supported | High | High | Prompt, fixes A-C, disclaimer | Unsupported claims remain; figures are in the README's Evaluation section | Threshold D3; Fix D (B8); level filter (B9); edition named; "confirm with [office]" line (B24). **Cannot be eliminated; must stay visible** |
| AG-5 | T | Out-of-date answer: the 2024-25 catalog is served while a newer one exists | High | High | UI names the edition [C] | One hard-coded edition | A2.3-A2.6 |
| AG-6 | E, D | Excessive agency: the model asks for many tools in one round | Med | Med | Round and step limits, read-only tools [C] | The number of tool calls in one round isn't capped in code | Cap them, in code (B20) |
| AG-7 | D | Unbounded output and time per call | Med | Med | Provider's own limits | LLM calls have no explicit output limit or timeout | `max_tokens`, timeout, 1 retry, truncation treated as failure (B20) |
| AG-8 | I | System prompt leaks | High | Low | It's in the public repo | None | **Accept.** Rule: nothing secret ever goes in a prompt; a test checks for key patterns (B20) |
| AG-9 | I | One request's data bleeds into another | Low | Med | `ContextVar` per request [C] | No concurrency test | Parallel test with distinct citations (B20) |
| AG-10 | T | **Safety:** a student in distress, or asking for medical or legal advice, gets a confident machine answer | Med | High | None | No code path. Groq's terms say the service "should not be used for medical, legal, financial, or other professional advice" [R] | Fixed template with AUI-approved contacts (B24, Q11). UNSURE about recall; it won't catch everything |
| AG-11 | I | The assistant names individuals | Med | Med | None | Live sources name people | Drop the page (A2.5); personal-data scan (A2.4) |

### 1.6 Tools

| ID | STRIDE | Threat | L | I | Current mitigation | Gap | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TL-1 | E | SQL injection through tool arguments | Low | High | Parameterised everywhere (checked) [C]; a least-privilege role | Was: the API ran as a superuser, so one mistake would be total, on 2026-11-05. Fixed 2026-11-05 (81b89ec) | Done (A1.4) |
| TL-2 | D | Oversized or malformed arguments | Med | Low | Parameterised | No validation | `query` at most 300 chars; `code` must match `^[A-Z]{3} ?\d{4}$` (B20) |
| TL-3 | D | Searches open several short-lived connections | Med | Med | Closed after use [C]; a connection limit on the role | No pool yet | Calls cap (B20), pool later (B6) |
| TL-4 | T | `query_courses` returns courses from no particular edition; removed courses stay answerable | High after swap | High | None | `courses.code` is the primary key; upsert never deletes. Measured earlier: 84 courses absent from the 2025-26 text would survive [C] | Per-edition tables (A2.3) |
| TL-5 | S, I | SSRF or open redirect via `/sources` | Low | Med | Fixed target list, `page` is an integer [C] | `page` unbounded but only ever a URL fragment | Validate anyway (B20) |
| TL-6 | R | Which tool produced an answer | Low | Low | Trace event to the browser [C] | Not kept server-side | Counts only in the event log (B27) |

### 1.7 Postgres

| ID | STRIDE | Threat | L | I | Current mitigation | Gap | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DB-1 | E, T | API holds a superuser: read, change or destroy anything; superusers can also run server-side programs [K] | Low | High | `campus_api`: exactly the rights the code uses, proven by a gate | Was: `rolsuper = t`, `rolcreaterole = t` on 2026-11-05. Fixed 2026-11-05 (81b89ec) | Done (A1.4) |
| DB-2 | E | API needs DDL rights because it creates the schema at startup | High | Med | A one-shot migrate command, run by the owner | Was: `init_schema` at API startup on 2026-11-05. Fixed 2026-11-05 (cdcdc82) | Done (A1.4) |
| DB-3 | D | Runaway queries | Low | Med | Depth cap on recursion [C]; `statement_timeout = 5s` and a connection limit of 50 on the role | Was: `statement_timeout = 0` on 2026-11-05. Fixed 2026-11-06 (852333a) | Done |
| DB-4 | D | Data loss with no backup | Med | High | Daily, encrypted, off-VM, restore proven | Was: nothing automated or off-VM on 2026-11-05. Fixed 2026-11-06 (7812662) | Done (A1.5) |
| DB-5 | D | Disk fills up and the API fails | Med | High | Free space today | Disk use grows with deploys, and there's no alert yet | Prune on deploy, alert at 80% (B22, B27) |
| DB-6 | I | No TLS between API and DB | Low | Low | Private network on one host | Matters only if DB moves | **Accept now.** Required with a managed DB (B5) |
| DB-7 | I | HMAC of the IP is still personal data; old rows linger on a quiet site | Med | Low | 2-day delete on each accepted question; README is honest about it [C] | Deletion depends on traffic | Daily scheduled delete (B23) |
| DB-8 | R | Who changed which content, and when | Med | Med | Git history for code | No record for data | `document_editions` records who activated what and when (A2.3) |
| DB-9 | S, I | Local dev Compose published DB and API on all interfaces of the laptop | Med | Med | Bound to 127.0.0.1; production resets these ports | Was: published on all interfaces on 2026-11-05. Fixed 2026-11-06 (9cadd6d, 92f154c) | Done |

### 1.8 Ingestion

| ID | STRIDE | Threat | L | I | Current mitigation | Gap | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IN-1 | T | Poisoned document, including text invisible to a human reviewer | Med | High | Sources are few and known | No scan yet; extracted text can include content a reviewer wouldn't see | Scan and human review of the extracted text (A2.4) |
| IN-2 | I | Personal data enters the knowledge base | High | High | "Public documents only" rule | Personal data appears in live sources | Personal-data scan with per-document approval (A2.4), and Q3 |
| IN-3 | T | A bad load goes live; no quick way back | Med | High | Single-transaction replace [C] | `replace_rows` deletes **every** document of the model; no dry run; rollback means a dump restore | Editions, dry run, one-transaction activation (A2.3, A2.4) |
| IN-4 | S, T | Wrong file downloaded | Low | Med | TLS | No hash recorded; `load.py` follows redirects anywhere | Record SHA-256 at registration; host allow-list; no off-host redirects (A2.4) |
| IN-5 | D, E | A crafted file attacks the parser (PDF bomb, parser bug) | Low | Med | Runs only on the laptop | Parsing has no size limit or sandbox yet | Size and page limits (A2.4); container with no network and no secrets (B14) |
| IN-6 | I | A non-public document reaches the public repo or Groq | Med | High | `.gitignore` covers `data/raw` and `data/processed` [C] | No check in code. **Any ingested passage can be sent to Groq** | Refuse `visibility != public` in code (A2.4); tracked-data check in CI (B21) |
| IN-7 | D | Silent partial load: scanned PDF gives empty text, unknown file types are skipped | Med | High | Prints "skip" and continues (`clean.py:44-46`) | No failure | Loud failure and quality thresholds (A2.4) |
| IN-8 | R | Which file produced which chunks | Med | Med | `source`, `model_name` columns | No hash, date or parser version | Stored per edition (A2.3) |

### 1.9 Groq

| ID | STRIDE | Threat | L | I | Current mitigation | Gap | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GQ-1 | I | Questions and passages go to a US provider | High | Med | Notice asks for no personal data [C]. Groq doesn't retain by default; logs up to 30 days for troubleshooting or abuse; no training on inputs [R] | Zero Data Retention state unknown (an account setting I can't see) | Enable ZDR (B18); data-protection review |
| GQ-2 | D | Shared provider quota is a small, fixed budget | High | High | Daily question cap, kind limit messages [C] | The evaluation and the demo share it, and the cap counts questions, not tokens | Paid plan (D2), token budget (B25) |
| GQ-3 | T | Model changes or is retired | Med | Med | Listed as a production model [R] | An earlier model was deprecated in 2026 [C]; no regression check on a change | Retest on model change (A2.8 sets the pattern); track deprecations (B27 checklist) |
| GQ-4 | S | Stolen API key | Low | Med on free, High on paid | `.env` is private to the owner | No rotation procedure; UNSURE whether Groq offers a hard spend limit | Runbook (B28); own token budget in code (B25) |
| GQ-5 | R | Provider terms and who holds the contract need review before wider use | Med | Med | None | DPA not read | AUI should hold the contract at campus scale (Q6); read the DPA (B18) |
| GQ-6 | D | No second provider is deployed | High | Med | CLAUDE.md lists Gemini | Its free tier isn't suitable: Google says "Do not submit sensitive, confidential, or personal information to the Unpaid Services" [R] | Pilot: no automatic fallback, kind failure message. Correct CLAUDE.md (B18). Paid second provider (B7) |

Elevation of privilege is not a credible provider threat here: the provider's output is treated as
untrusted and it can call nothing on its own.

### 1.10 Azure VM

| ID | STRIDE | Threat | L | I | Current mitigation | Gap | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VM-1 | D | **Credit runs out; services and subscription are disabled.** The Microsoft page gives no timeframe for data deletion [R] | High | High | Budget alert; off-VM backups since 2026-11-06 (7812662) | Where the service runs next is undecided: due by 2026-12-01 | D1 |
| VM-2 | E, S | A stolen SSH key would give full control of the VM | Low | High | NSG limits SSH by source address; the key has a passphrase and lives in an agent | Was: the key had no passphrase on 2026-11-05. Fixed 2026-11-06 (set on the key, no commit). Narrower deploy access stays in B22 | Narrower deploy access (B22) |
| VM-3 | E | SSH defaults | Low | Med | Key only, root refused, forwarding off, named user, 3 tries | Was: root login by key, X11 and TCP forwarding on, 6 auth tries, on 2026-11-05. Fixed 2026-11-06 (9580d89) | Done |
| VM-4 | E | A container breakout or compromise goes further than needed | Low | High | API runs non-root | Not yet at the hardened baseline (section 6.2) | Section 6.2 (B22) |
| VM-5 | I | The NSG is the only network firewall | Low | Med | NSG default-deny | Single layer | **Accept** for now; review at B5 |
| VM-6 | T, E | Patches | Med | Med | Unattended upgrades | Kernel fixes wait for a manual reboot; images aren't rebuilt on a schedule | Reboot window, weekly rebuild (B21, B22) |
| VM-7 | D | Memory pressure on one container can affect the whole host | Med | High | Restart policy [C]; swap since 2026-11-06 | No container limits yet | Limits (B22), load test (B29) |
| VM-8 | I | Secrets in plain text on disk and visible through `docker inspect` | Low | High | Private files, only needed keys on the VM | No vault | Section 6.3: accept for pilot, Key Vault at B4 |
| VM-9 | T | What is actually running? A tar copy, built on the VM, with no commit marker | Med | Med | Git history | Tested and deployed versions can differ | Build from lockfile, expose commit in `/ready` (B21, B27) |
| VM-10 | R | Host activity isn't shipped anywhere | Low | Med | Local journald | Lost with the VM | Accept for pilot; ship at B10 |
| VM-11 | S | A custom domain dangling after the VM or IP is released | Low | Med | IP is static [C] | Not yet relevant | Checklist item when the Namecheap domain is added (B28) |

### 1.11 GitHub and CI

| ID | STRIDE | Threat | L | I | Current mitigation | Gap | Fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GH-1 | I | A secret pushed to a public repo | Med | High | Secret scanning and push protection | Was: both disabled on 2026-11-05. Fixed 2026-11-06 (GitHub setting, no commit). gitleaks in CI stays in B21 | gitleaks in CI (B21) |
| GH-2 | T | Compromised or vulnerable dependency | Med | High | `npm ci` lockfile [C]; Dependabot alerts | No Python lockfile yet; `httpx` is used directly but not declared [C] | Hashed lockfile, pip-audit, npm audit, Dependabot updates (B21) |
| GH-3 | E, T | Compromised GitHub Action | Low | Med | Default token is read-only; no repo secrets [C] | Tags, not SHAs; no `permissions:` block [C] | Pin by SHA, explicit `permissions: contents: read` (B21) |
| GH-4 | T | History rewritten or bad commit on `main` | Low | Med | Single author; force-push and deletion blocked since 2026-11-06 (GitHub setting) | CI isn't required before a push lands | Require CI (B21) |
| GH-5 | T | Base image changes silently or carries CVEs | Med | Med | Official images | Tags, not digests; no image scan [C] | Digests, Trivy (B21) |
| GH-6 | T | Embedding model swapped upstream | Low | Med | Downloaded once at build; `HF_HUB_OFFLINE=1` at runtime [C] | No revision pin | Pin revision, prefer safetensors (B21) |
| GH-7 | I | Past private notes in history | Low | Low | Nothing sensitive found in history | | Accept |
| GH-8 | S, R | Commits can't be proven authentic | Low | Low | Single author | Unsigned | Signed commits (C) |

GitHub is not in the runtime path, so an outage there delays work but doesn't stop the service.

### 1.12 STRIDE coverage

| Component | S | T | R | I | D | E |
| --- | --- | --- | --- | --- | --- | --- |
| Browser | BR-2 | BR-1, BR-4 | BR-6 | BR-1, BR-5 | Own tab only | BR-3 |
| Caddy | CD-4 | CD-2 | CD-6 | CD-3 | CD-1, CD-5 | CD-2 |
| API | AP-7 | AP-9 | AP-8 | AP-4, AP-6 | AP-1, 2, 3, 5, 10 | No admin routes exist |
| Agent | AG-2 | AG-1, 3, 4, 5, 10 | BR-6 | AG-8, 9, 11 | AG-6, AG-7 | AG-6 |
| Tools | TL-5 | TL-4 | TL-6 | TL-5 | TL-2, TL-3 | TL-1 |
| Postgres | DB-9 | DB-1 | DB-8 | DB-6, 7, 9 | DB-3, 4, 5 | DB-1, DB-2 |
| Ingestion | IN-4 | IN-1, 3, 4 | IN-8 | IN-2, IN-6 | IN-5, IN-7 | IN-5 |
| Groq | GQ-4 | GQ-3 | GQ-5 | GQ-1 | GQ-2, GQ-6 | Output untrusted |
| Azure VM | VM-2, VM-11 | VM-6, VM-9 | VM-10 | VM-8, VM-5 | VM-1, VM-7 | VM-2, 3, 4, 6 |
| GitHub/CI | GH-8 | GH-2, 3, 4, 5, 6 | GH-8 | GH-1, GH-7 | Not in runtime path | GH-3 |

### 1.13 OWASP Top 10:2025 (web applications) [R]

| Item | How it applies here | Threats | Status |
| --- | --- | --- | --- |
| A01 Broken Access Control | No roles or private data yet; the rule is that non-public documents are refused | AP-7, IN-6 | OK today; design in 3.7 |
| A02 Security Misconfiguration | Container defaults | VM-4 | **Gaps** |
| A03 Software Supply Chain Failures | No Python lockfile, some unpinned images and actions | GH-2, 3, 5, 6 | **Gaps** |
| A04 Cryptographic Failures | TLS good; HMAC-SHA256 with a per-deployment secret | CD-4, DB-6 | OK |
| A05 Injection | SQL parameterised, HTML escaped, with a least-privilege role and a CSP as second layers; prompt injection in the LLM table | TL-1, BR-3 | OK |
| A06 Insecure Design | Client-side history, per-IP identity, no groundedness gate | AP-2, AP-3, AP-9, AG-3 | **Gaps** |
| A07 Authentication Failures | No authentication yet; access codes must be hashed and rate limited | AP-7 | Planned (B25, B2) |
| A08 Software or Data Integrity Failures | No document hash or edition; no verified deploys | IN-3, IN-4, VM-9 | **Gaps** |
| A09 Security Logging and Alerting Failures | Private logs, but no events or alerts | AP-8, CD-6 | **Gaps** |
| A10 Mishandling of Exceptional Conditions | Stream failures close cleanly; no deadline; several undefined states | AP-10, section 2.6 | Partial |

### 1.14 OWASP Top 10 for LLM Applications 2025 [R]

| Item | How it applies here | Threats | Main fix |
| --- | --- | --- | --- |
| LLM01 Prompt Injection | Direct and through documents | AG-1, AG-2 | Close exits, gate, data framing, adversarial tests |
| LLM02 Sensitive Information Disclosure | Question text to a provider; names in documents; history | GQ-1, IN-2, AG-11, BR-1 | Scan, ZDR, data-protection review; images are off |
| LLM03 Supply Chain | Model revision, packages, images, provider | GH-2, 5, 6, GQ-3 | B21 |
| LLM04 Data and Model Poisoning | Poisoned documents; the embedding model | IN-1, GH-6 | B21, A2.4 |
| LLM05 Improper Output Handling | Markdown links; images are off | BR-2 | B19 |
| LLM06 Excessive Agency | Read-only tools and a least-privilege role, but uncapped calls | AG-6 | B20 |
| LLM07 System Prompt Leakage | The prompt is public and holds no secrets | AG-8 | Accept with a rule |
| LLM08 Vector and Embedding Weaknesses | Stale versions searched; no ACLs on vectors when non-public documents arrive | AG-5, TL-4, IN-6 | A2.3; section 3.7 |
| LLM09 Misinformation | The main residual risk | AG-3, 4, 5 | A2.7, A2.8, D3, B24, B8, B9 |
| LLM10 Unbounded Consumption | Output size, tool fan-out, one visitor and the cap; input size is limited | AP-2, AG-6, AG-7, GQ-2 | B20, B25 |

---

## 2. Application layer

### 2.1 Input validation and size limits

Principle: validate before the limit check, so a malformed request costs nothing and isn't counted.
Reject rather than truncate silently. The measured maximums are from the faithfulness runs, which
are test questions, so UNSURE how long real questions are; revisit after the first pilot week.

| Where | Rule | Reason |
| --- | --- | --- |
| Caddy, `/api/*` | `request_body max_size 64KiB`; returns 413. **`KiB`, not `KB`: Caddy reads `64KB` as 64,000 bytes** [M]. A community report said the limit can depend on handler order [R]. On Caddy 2.8.4, inside `handle_path` and at site level behaved the same [M]; a test runs the pinned image | First line of defence |
| App, pure ASGI middleware | The same 65,536 bytes, counting what actually arrives, so a chunked body with no `Content-Length` can't get around it [M]. It wraps `receive` and leaves `send` alone, so SSE streams through it, proven by a test | The dev and Compose paths have no Caddy; UNSURE whether uvicorn limits bodies (sources disagree) [R] |
| `POST /chat` body | JSON only; `extra="forbid"`. A 422 has a fixed body with no input in it | Unknown fields are a bug or a probe |
| `question` | 1-2,000 characters after trimming; no control characters except newline and tab | Longest test question is 115 [M] |
| `messages` | At most 20 items, or 422. Server still uses the last 10 | Silent discarding hides bugs |
| `messages[].content` | User 2,000; assistant 6,000 characters | Longest answer in 3 runs is 2,827 [M] |
| `GET /sources/{id}` | `^[a-z0-9_]{1,64}$`; `page` 1-5000 | Paths are logged, so bound them |
| `/health`, `/ready`, `/limits` | No parameters | |
| Docs routes | Off unless `ENV=development`, live since 2026-11-06 | AP-4 |
| Tool `query`, `query_en` | At most 300 characters | The model also writes these |
| Tool `code` | `^[A-Z]{3} ?\d{4}$` after upper-casing, else "not found" with no DB call | TL-2 |
| Tool calls | At most 2 per round, 3 rounds, enforced by trimming `tool_calls` in the agent node | AG-6. Prompt-only limits were ignored in testing (CLAUDE.md) |
| LLM call | `max_tokens` 2,000 (check against run 3: no truncation), 30 s timeout, 1 retry | AG-7. UNSURE of the SDK defaults; set them explicitly |
| Whole run | 60 s deadline; cancel on client disconnect, proven by a test | AP-10 |

Protects against: AP-1, CD-1, AG-6, AG-7, TL-2, AP-10. Follows: OWASP ASVS 5.0 input validation
[K], OWASP API Security Top 10 2023 API4 unrestricted resource consumption [K], LLM10 [R].

### 2.2 Output handling

Model output is untrusted. It is rendered as Markdown, never as HTML, with an explicit allow-list
instead of react-markdown's defaults, whose gaps were confirmed by test.

| Rule | Detail | Protects against |
| --- | --- | --- |
| Allow-list elements | Paragraphs, emphasis, lists, tables, code, line breaks, links. **No `img`**: shows the alt text | BR-1 (LLM05) |
| Links | Internal `#source-` chips; external only if the host is in the registry. Otherwise shown as plain text | BR-2 |
| Raw HTML | Stays disabled; only the `<br>` conversion remains [C] | BR-3 |
| CSP | Section 6.4. A second layer if a rule above fails | BR-1, BR-3 |
| Same rules everywhere | Every `<Markdown>` in the app, including the first screen's proof card (`EmptyState.tsx:33`) | Consistency |
| Tests | A hostile-Markdown table in vitest: image, reference image, autolink, phishing link, `javascript:`, `data:`, raw HTML | Regression |

Follows: OWASP LLM05 [R], OWASP XSS Prevention and CSP Cheat Sheets [K].

### 2.3 Tools: read-only and least privilege

The brief asks for a read-only database role. One nuance: the API cannot be fully read-only, because
the demo limits write to `question_log`. So the roles are:

| Role | Rights | Used by |
| --- | --- | --- |
| `campus_api` | `SELECT` on content tables; `SELECT, INSERT, DELETE` on `question_log`, `USAGE` on its sequence, no temporary tables, a 5 s statement timeout and a connection limit of 50 (A1.4, 852333a, `app/db/roles.sql`) | API |
| Bootstrap superuser (`POSTGRES_USER`, today `campus_assistant`) | Everything; owns every table | **Migrations and ingestion, for now** |

Decided 2026-11-05: **only `campus_api` exists after A1.4. Migrations and ingestion still run as the
owner, which is a superuser.** Why: the risk this step removes is a superuser connection held by the
running API, which faces the internet and runs model-chosen tool calls. Migrations and ingestion are
one-shot commands run by hand, and `CREATE EXTENSION vector` may need a superuser anyway. Splitting the
owner would also mean reassigning every table on a live volume, a riskier change with no exposed path to
protect today. The cost: a mistake in a migration or in ingestion has a superuser's reach. A non-superuser
`campus_owner` and a `campus_ingest` with write rights on content tables only (and nothing on
`question_log`) are worth adding when A2's ingestion CLI arrives, because it runs far more often.

The agent's tools don't get their own role in tier A: they run inside the API. A second role for
tools alone (`SELECT` on content only) is cheap and adds real separation from `question_log`. I
recommend adding it at B6, when pooling changes how connections are made. UNSURE it's worth doing
sooner: the worst case is a tool tampering with demo counters.

A check proves it, in CI and as the deploy's gate (`app/db/verify_role.py`): as `campus_api`, `INSERT` into
`document_chunks`, `CREATE TABLE`, `DROP`, `COPY ... PROGRAM` and others must each fail with SQLSTATE 42501,
each in its own rolled-back savepoint. The same check run as the owner must report problems. Protects against: DB-1, DB-2, DB-3, TL-1, LLM06 [R]. Follows: CIS PostgreSQL Benchmark
and PostgreSQL's role documentation [K].

### 2.4 Groundedness enforced in code

**What the gate can and cannot do.** Code can prove an answer *has* valid citations. It cannot prove
the citations *support* the claims. "No uncited factual answer reaches a student" is enforceable.
"No wrong answer reaches a student" is not; that remains the job of evaluation, the threshold (D3)
and visible caveats.

**The rule.** The only text without a citation that reaches a student is text written by us in code.

| Situation | What the student sees |
| --- | --- |
| No tool was called this turn (greeting, off-topic, jailbreak) | Scope template: what the assistant covers, generated from the registry, plus example questions |
| Tools ran; the answer has no valid marker | Not-found template: "I couldn't find this in the documents I have" plus the office to ask |
| Answer cites a number no tool returned this turn | Same not-found template; counted as a gate event |
| Valid citations | The answer, plus a code-written line naming the edition(s), see section 5.3 |
| Forced answer failed twice | Existing fallback (listing passages found) stays |
| Output truncated (`finish_reason = length`) | Not-found template with "please try a more specific question" |
| Safety match (AG-10) | Safety template, with no LLM call |

**What ships when.** The answer-level cases, holding the answer, and an off-topic and injection category in the
eval set are step A2.6b. The truncation and safety rows, and the rest of section 2.6, stay in B24. Greetings and questions
about the assistant get the code-written scope template, so they still work and carry no citation.

**Evidence that this is safe to ship** [M], on run 3's 34 answers: 31 have citations and 3 don't,
and all 3 are correct refusals. So an answer-level gate would replace 3 refusals with better
ones and touch no real answer. No answer in run 3 uses an invented marker, though an earlier run
did [C].

**Later evidence [M], 2026-11-06.** A sample of 12 main questions on the code at `c907a33` had 1 real answer with no marker
(`add_drop_en`; it cited 2 in run 3). In the A2.1 deploy check, 3 of 4 live answers had no source cards, and the one read in
full had no markers. So the gate will replace some real answers, and "touch no real answer" holds for run 3 only. At 1/12,
about 2.5 of 30 would become false refusals, against threshold item 3's limit of 2. UNSURE of the true rate: the sample is small.
A2.6b should count these before it ships.

**A known cost.** Follow-ups that need no search ("translate that to French", "thanks") hit the scope
template. Measure on a small multi-turn set before deciding whether to special-case them. UNSURE how
common they are.

**Why not per-sentence.** In run 3's cited answers, 97 of 143 paragraph or list blocks have no marker,
and 49 of those contain a digit (a rough split [M]). A per-block gate today would mangle most answers.
Revisit after Fix D (B8), measured.

**Number check: shadow mode only.** Checking that every number in an answer appears in its cited
passages flagged 3 of the 24 answers containing numbers [M]. All 3 are among the 14 answers the judge
marked, with 0 false alarms, but it misses 11 of the 14, and 2 of the 3 flags were at least partly
numbered lists, so that precision is partly luck. Log it (B8), don't block on it.

**Streaming: hold the answer until it passes.** Tokens streamed before the gate would already have
reached the student. Holding the whole answer costs little: Groq streams at about 1,000 tokens/second
[R], and in the two saved traces the text took 182 ms and 70 ms from first token to last [M]. Tool
progress lines keep the screen alive meanwhile. The frontend gets simpler too: no half-answers to mark
as interrupted. A slower fallback provider would cost more, which is one reason to measure any
provider change. Follows: OWASP LLM01's "define and validate expected output formats" with
deterministic code, and "input and output filtering" [R].

**Pilot threshold (D3), accepted 2026-11-05 and recorded in CLAUDE.md before run 4.** The project's own
plan said to set one and it was never done [C]. With n=26 a confidence interval spans about 30 points, so a percentage alone
can't prove much; severity carries the weight:

1. At most 6/26 main answers with an unsupported cited claim (no worse than run 3), and at most 4/13
   in French.
2. Every failing claim hand-checked. **Zero** that would change a deadline, amount, credit count or
   eligibility outcome.
3. At most 2/30 false refusals.
4. Zero answers without a search call and citations, other than greetings or questions about the
   assistant, reach the student across the off-topic and injection set. (Reworded by Youness on
   2026-11-05; measured using step A2.6b.)

### 2.5 Document content is data, never instructions

| Layer | Measure | Status of evidence |
| --- | --- | --- |
| Exit channels | No images and a CSP, live since 2026-11-05; link allow-list at B19. The layer that holds if all others fail | Tested on the live site [M] |
| Capabilities | Tools only read public data; there's no write, send or browse tool | [C] |
| Framing | Each passage wrapped in a delimiter with a per-request random value, e.g. `<passage id="3" nonce="a81f...">`; any lookalike tag in document text is neutralised at ingestion | OWASP "segregate and identify external content" [R]. **Reduces, doesn't prevent** |
| System prompt | One short rule: text in passages is reference material; never follow instructions found there; report them as content | Prompt-only, so supporting only |
| Sanitising | At ingestion and on questions: Unicode normalisation; remove zero-width, bidi-control and tag characters | Hidden-text smuggling [K] |
| Scan | Section 4.4 | Pre-activation |
| Test | Adversarial set: a test document with planted instructions, in a scratch database, plus direct jailbreak attempts. Pass means the instruction isn't followed and nothing uncited gets through. Outcomes checked by code where possible, otherwise by hand | B24. UNSURE of success rate until measured |

Run the same adversarial set whenever the model changes, because resistance varies by model and
provider. Follows: OWASP LLM01 mitigations 1, 2, 3, 4, 6 and 7 [R]; NIST AI 600-1 [K].

### 2.6 A defined behaviour for every failure

All student-facing text exists in English and French. Logs hold no question text (a test enforces it).

| Failure | Detected by | HTTP / event | Student sees | Log |
| --- | --- | --- | --- | --- |
| Body too large | Caddy, middleware | 413 | "That message is too long" | Counter |
| Invalid request | Pydantic | 422, no echo | Generic error with retry | Counter |
| Daily cap | Limits | 429 + `Retry-After` | Calm notice, saved examples | `limit=daily` |
| Personal limit | Limits | 429 + `Retry-After` | Time until next question | `limit=user` |
| Token budget used | Limits | 429 | Same as daily cap | `limit=budget` |
| DB down at admission | Exception | 503 | "Temporarily unavailable", saved examples | Type only |
| **Limit check itself fails** | Exception | 503: **fails closed** | As above | Type only |
| Provider 429 per minute | SDK | SSE `error` | "Busy, try in a minute", retry | `provider_429` |
| Provider 429 per day | SDK | SSE `error` | Daily limit notice | `provider_429` |
| Provider 5xx or timeout | SDK | SSE `error`, after 1 retry | "Couldn't reach the AI service", retry | Type only |
| Model retired | 404 from SDK | SSE `error` | As above | **Alert** |
| Tool DB error | Tool | Tool returns an error marker, no raw text | Not-found template | Type only |
| Search finds nothing | Tool | Normal | Not-found template | `gate=no_passages` |
| Empty active document set | Tool | Normal | Scope template | **Alert** |
| Round budget used | Graph | Forced answer | Answer or fallback | `forced=1` |
| Forced answer fails twice | Graph | Fallback [C] | Passages listed | `fallback=1` |
| Step limit or 60 s deadline | Graph, timer | SSE `error` | "Took too long", retry | Type only |
| Truncated output | `finish_reason` | Template | Not-found template, more specific | `truncated=1` |
| Gate rejects | Gate | Template | As in 2.4 | `gate=<reason>` |
| Client disconnects | Starlette | Run cancelled | Nothing | `cancelled=1` |
| Trace can't be built | `try` [C] | Answer still sent | No panel | Type only |
| `/sources` target down | HEAD check [C] | 302 to fallback page | Landing page | None |
| Source has no fallback | | 302 to URL | Whatever the site returns | None |
| Unknown source | Lookup | 404 | Plain "unknown source" | Counter |
| Connection dropped | Browser | None | "Connection dropped", retry [C] | None |
| Malformed SSE frame | `JSON.parse` throws in `parseSse` | None | Currently the connection-lost message; test it | None |
| Disk full | Alert at 80% | | Depends on the failure | **Alert** |
| TLS renewal fails | External check | | Nothing yet | **Alert** |

Follows: OWASP A10:2025 [R]; failing closed is NIST SP 800-53 SC-24 [K].

---

## 3. Data layer

### 3.1 Registry

Status must change without a redeploy to make rollback instant, so lifecycle state lives in Postgres
from the start. Descriptive metadata starts in a committed file, `data/registry.toml` (standard
library `tomllib`, no new dependency, comments allowed), which the CLI syncs to the database. All code
reads through one function, so moving to an admin page later replaces only the source of the metadata.

Two levels: a **document** is a lasting thing ("Academic Catalog"), an **edition** is one version.

```toml
[[document]]
id = "academic_catalog"
title = { en = "Academic Catalog", fr = "Catalogue académique" }
domain = "academic"            # academic, scholarships, finance, housing, dining, student_life...
owning_department = "Office of the Registrar"   # UNSURE: AUI to confirm (Q4)
audience = "all"               # all, undergraduate, graduate, staff
visibility = "public"          # public or non_public; non_public is refused for now
time_sensitive = true          # answers must name the edition

  [[document.edition]]
  id = "academic_catalog_2024_2025"   # equals document_chunks.source
  label = "2024-2025"
  card_title = "Academic Catalog 2024–2025"   # exactly what the source card shows
  effective_from = "2024-08-01"     # UNSURE: AUI to confirm
  review_by = "2027-08-01"
  retrieved_at = "2026-09-29"       # when we downloaded the file; required
  # last_updated: the publisher's stated revision date; left out when none is stated
  language = "en"
  format = "pdf"
  source_url = "https://aui.ma/hubfs/ACADEMIC%20CATALOG%202024-2025.pdf?hsLang=en"
  fallback_url = "https://aui.ma/academic-catalogs"
  sha256 = "..."
  course_tables = true              # the courses tables are extracted from this edition
```

| Field | Why it exists |
| --- | --- |
| `domain`, `owning_department` | Domain filter; who to ask; who approves; conflict display |
| `audience` | Future filter; level-specific answers |
| Edition `label`, `effective_from` | Named in answers |
| `review_by` | An expired document is flagged, section 5.3 |
| `status` (database) | `draft`, `active`, `superseded`, `withdrawn` |
| `language` | Which full-text configuration applies |
| `visibility` | Fail-closed gate |
| `sha256`, parser version, `activated_by`, `activated_at` | Integrity and audit (A08, IN-8, DB-8) |
| `card_title` | What a source card shows, explicit because title + label can't reproduce today's cards: the catalog's has an en dash, the web pages' have no edition label |
| `source_url`, `fallback_url`, `format` | Where a source card's link goes; the API needs them, and the file isn't in its image, so they are synced to the table |
| `retrieved_at`, `last_updated` | When we downloaded it, and the revision date the publisher states. A PDF's metadata date is not a stated revision, so it isn't used: "modified 2025-08-31" on a 2024-2025 catalog is a date a student would misread |
| `course_tables` | Which edition `app/ingestion/courses.py` extracts from |

**Who reads what.** The API image holds only `backend/app`, so the file isn't in it: the API reads the synced
tables, and only the CLI and ingestion read the file. Sync runs as the owner in a one-shot Compose service with one
read-only bind mount of `data/registry.toml`.

### 3.2 Per-edition storage

```sql
CREATE TABLE documents (
  id TEXT PRIMARY KEY, domain TEXT NOT NULL, owning_department TEXT,
  audience TEXT NOT NULL, visibility TEXT NOT NULL CHECK (visibility IN ('public','non_public')),
  time_sensitive BOOLEAN NOT NULL, title JSONB NOT NULL
);
CREATE TABLE document_editions (
  id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
  label TEXT NOT NULL, card_title TEXT NOT NULL, effective_from DATE, review_by DATE,
  retrieved_at DATE NOT NULL, last_updated DATE, language TEXT NOT NULL,
  format TEXT NOT NULL CHECK (format IN ('pdf','html')),
  source_url TEXT NOT NULL, fallback_url TEXT, course_tables BOOLEAN NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('draft','active','superseded','withdrawn')),
  sha256 TEXT NOT NULL, parser_version TEXT NOT NULL, quality_report JSONB NOT NULL,
  activated_by TEXT, activated_at TIMESTAMPTZ
);
-- At most one active edition per document, guaranteed by the database.
CREATE UNIQUE INDEX one_active_edition ON document_editions (document_id) WHERE status = 'active';

-- document_chunks gains edition_id; UNIQUE (edition_id, chunk_index, model_name).
-- courses: PRIMARY KEY (edition_id, code).
-- course_prerequisites: PRIMARY KEY (edition_id, course_code, prerequisite_code),
--   FOREIGN KEY (edition_id, course_code) REFERENCES courses.
```

**`owning_department` is nullable** (changed 2026-11-06). AUI hasn't confirmed the owners (Q4), and a sentinel such as
"Unconfirmed" is one forgotten check away from appearing in a code-written "confirm with [office]" line (B24). NULL
forces that code to handle the missing case.

**`parser_version` and `quality_report`** are `'unversioned'` and `{}` until A2.4 produces real values.

Things A2.3's per-edition columns break, to change in the same step (line numbers at commit `c1571e7`): citation
numbering keys (`(source, chunk_index)`, `tools.py:136`, and `tools.py:264`), the RRF key (`hybrid_search.py:112`), the
course lookups (`tools.py:234,241`), the recursive prerequisite query (`tools.py:322-340`, must stay inside one
edition), the chunk upsert, replace and metadata keys (`store.py:21,65,82,100`), the course edge reset
(`courses.py:133`), and the `source` link in saved examples. `CATALOG_SOURCE` and `SOURCES` go in A2.1.

**Activation and rollback.** One transaction: old edition to `superseded`, new one to `active`, with
actor and time recorded. Rollback is the same command the other way: no re-embedding, no deleted rows,
effective on the next request, because searches read the active set per request (one indexed query; a
cache isn't worth the staleness until measured otherwise). Keep the last superseded edition of each
document for rollback and delete older ones, which also protects filtered recall (section 5.5).

**Saved examples** replay answers from a specific edition. After the swap they must be regenerated or
say which edition they came from (A2.6). The first-screen counts, pinned by `about.test.ts`, change too.

### 3.3 Data minimisation

Keep what's already true: no accounts, no stored questions or answers. New features must not quietly
change that. In particular the proposed event log (B27) records **counts and outcomes only**, and any
future answer cache (B6) stores question text only under its own retention rule, considered as a
separate decision.

### 3.4 Retention: every place data lives

| Where | What | Retention today | Proposed |
| --- | --- | --- | --- |
| Browser | Conversation (memory), theme (localStorage) | Until reload | Same |
| Postgres `question_log` | Time, HMAC of IP | 2 days, deleted only on the next accepted question [C] | 2 days by a **daily job**; access-code hash replaces the IP hash in the pilot |
| Postgres content | Passages, courses | Until replaced | Active + last superseded; withdrawn editions deleted within 7 days |
| API memory | IP in memory for hashing; URL check cache | Per request, process life | Same |
| API, Caddy, nginx, Postgres logs | No question text or visitor IP [C][M] | 3 x 10 MB, no time limit; currently 4-8 KB each [M] | Same: acceptable while they hold no personal data. Paths are logged, so stay bounded |
| New event log | Route, status, timing, tokens, gate outcome, editions | None | 30 days, then deleted; a test extends `test_log_privacy.py` |
| Backups | See 3.5 | Daily, encrypted, off-VM, kept 45 days, **excluding `question_log`**, so backups hold no visitor data | Same |
| Laptop | Older local dumps | Indefinite | Review now that backups are verified |
| Groq | Prompts and outputs | None by default; up to 30 days when troubleshooting or investigating abuse [R] | **Zero Data Retention on** (open to "all customers" [R]); check the setting (B18) |
| Google (Gemini) | Nothing in production | Key not deployed [M] | Stays off until paid (B7) |
| Mistral | Answers and passages during evaluation | Per its terms; UNSURE of them | No student content: evaluation sets only |
| GitHub | Code, evaluation results, Actions logs | Public, permanent; logs by GitHub's default (UNSURE: 90 days [K]) | No student data, ever: enforced in CI (B21) |
| Azure | Billing, activity log | Azure defaults (UNSURE) | Check |
| Uptime monitor (new) | Health-endpoint results | Per vendor | Choose one with no visitor data involved |

### 3.5 Backups

| | Pilot | Campus-wide |
| --- | --- | --- |
| Content recovery point (RPO) | **Zero data lost in practice:** a dump is taken at each activation, and content changes only then | Same |
| Runtime recovery point | `question_log` is **not backed up**. Loss means limit counters reset, which is harmless | Add user data rules if accounts exist |
| Recovery time (RTO) | **4 hours**, working hours, by hand | **1 hour**, from scripted provisioning (B11) |
| Schedule | Daily content-only `pg_dump -Fc` from a systemd timer on the VM host, encrypted with `age`. A Healthchecks.io ping after each good backup, so silence raises an alert about 26 hours after the last one, and a `/fail` ping when a run fails, so the alert doesn't wait for that | Add a second region |
| Copies | **Backblaze B2, not Azure** (decided 2026-11-05 and 2026-11-06), bucket `campus-assistant-backups-7`, EU Central. Anything in the same subscription dies with it (VM-1). Object Lock in compliance mode for 30 days per version, kept 45 days. The lock is what stops a compromised VM destroying old backups: its key can hide files, and lifecycle rules delete hidden files (`deploy/DEPLOY.md`) | Off-site copy held by AUI |
| Encryption key | The VM holds only the `age` public key, so it can encrypt but never decrypt. **The private key is on the laptop, with one offline copy in Youness's password manager** (decided 2026-11-06): with the laptop as the only copy, losing it would make every backup unreadable | Key Vault |
| Also stored | `.env` values in a password manager; registry file in Git; source files with hashes | Key Vault |
| Proof | Restore drill into a scratch database: row counts and whole-row fingerprints, embeddings included, identical to production (A1.5). Then every month | Same |

The 4-hour RTO is a target, not a measurement. The manual runbook has never been timed from nothing:
**B23 includes the first timed rebuild.** Source documents must be kept too: if AUI withdraws a file
from its website, the chunks alone can't be re-chunked. Follows: NIST SP 800-34 contingency planning,
the 3-2-1 backup practice [K].

### 3.6 Data protection

A data-protection review with AUI is a pilot exit criterion.

### 3.7 Non-public documents: plan only, build nothing

**Now, enforced in code:** ingestion refuses `visibility != "public"`, and every search filters on it.

**Later, in order, all required first:** (1) contract and transfer terms with the LLM provider, since
passages go to it; (2) real authentication (SSO, B2), never access codes; (3) an audience on every
edition, with the user's groups passed by the server, never chosen by the model; (4) filter **in SQL,
before ranking**, on every search and course lookup, with an automated test that a user without
access gets no passage, trace or count from a restricted document; (5) separate storage for those
documents, outside Git and off the laptop; (6) stored-conversation rules revisited; (7) data-protection review.
Vector search needs special care because a shared approximate index can affect recall across tenants,
and pgvector's advice for tenant isolation is list partitioning or separate tables [R]. Protects
against: A01, LLM02, LLM08 [R].

---

## 4. Ingestion

### 4.1 One loader interface

```python
class Block:                      # the smallest unit a loader produces
    kind: Literal["text", "heading", "table"]
    text: str                     # for a table: Markdown, header row included
    locator: Locator              # page=117 | anchor="#renewal" | section="Repeat Policy"

class Loader(Protocol):
    formats: tuple[str, ...]
    def load(self, path: Path, edition: Edition) -> list[Block]: ...
```

The pipeline is: **register -> load -> sanitise -> chunk -> scan -> dry-run report -> embed -> draft ->
evaluate -> activate**. Only `PdfLoader` and `WebLoader` are implemented now. Any other format raises
`UnsupportedFormat`, naming the file and listing what is supported. Word, Excel and PowerPoint wait for
a real document, because their structure can only be designed against real examples.

### 4.2 Tables stay whole, with one honest qualification

"Never split across chunks" can't be absolute: a long table may not fit the 512-token embedding limit or
a sensible prompt. The rule that can always hold: **the text the model reads never contains part of a
table without its header row.**

| Table size | Behaviour |
| --- | --- |
| Fits within the chunk limit | One chunk |
| Bigger, up to a character budget | Whole table returned to the model when any of its rows match; embedded as row groups, each repeating the header ("parent-child" retrieval) |
| Bigger than that budget | Dry run stops and asks: split by a real column, or exclude. UNSURE of the budget until real department tables exist |

**Tier split (D6).** HTML tables are straightforward and are done in A2.4. PDF tables need a change of
extractor, because pypdf returns flat text with no table structure [C]. `pdfplumber` is the first
candidate (MIT licence [K]; avoid PyMuPDF's AGPL in this setup [K]); UNSURE until compared on real pages.
Run 3 attributes no failure to split tables [M], and changing the chunker during the catalog swap would
confound it, so this is **B1**, due before the first table-heavy PDF. Caveat: the eval has few table
questions, so "no failures" partly reflects what isn't tested. B1 starts by adding them. Until then the
dry run warns on table-like pages and refuses a document when they exceed a threshold set from the catalog:
about 85 of its 435 pages have a course-table header [M].

### 4.3 Failing loudly, and dry runs

`python -m app.ingestion.ingest <edition_id> --dry-run` changes nothing and reports:

| Check | Refuses when | Calibration |
| --- | --- | --- |
| File hash | Doesn't match the registry | |
| Encrypted or unreadable | Always | |
| **Scanned or image-only** | Too few characters per page on many pages, **after removing the running header**, which otherwise makes a blank page look like text. No OCR: fail, and say so | Threshold to be set from the catalog's real page sizes. 2025-26 has 9 blank pages, not visually checked [C] |
| Size, pages | Over limits | Largest today is 2.8 MB [M] |
| `visibility` | Not public | |
| Replacement characters, broken encoding | Above a threshold | Calibrate on the current files in A2.4 |
| Boilerplate | `lorem ipsum` and similar: refuses | Found in 2 chunks today [M] |
| Headings found | Sharply below the previous edition | 535 -> 413 on 2025-26 before the fix, 511 after [C] |
| Courses extracted | Below previous edition or a coverage ratio; lists codes in text but not extracted | 660 -> 696; 91 not extracted [C] |
| Chunk sizes vs. token limit | Over 512 tokens | Existing check [C] |
| Anchors | Reports which eval anchors survive | 8/10 on 2025-26 [C] |
| Page-header pattern | Warns on repeated lines | The cause of the heading drop |
| Personal data, instructions | Section 4.4 | |

Thresholds are set from the catalog, then reviewed after the first new document type. They are
starting values, not established facts.

Web loader rules: host allow-list from the registry, redirects only to allowed hosts, timeout, size limit,
keep the raw file with its hash, strip `script`, `style`, `nav` and elements hidden by CSS or attributes.

### 4.4 Scanning before activation

| Scan | Action |
| --- | --- |
| Instructions aimed at a model ("ignore previous instructions", role markers, chat tokens, in EN and FR) | Hold for human decision |
| Hidden content: PDF text with tiny font or matching background, CSS-hidden HTML, zero-width or bidi characters | Hold; removed by sanitising |
| Pattern personal data: national ID, student numbers, phone, personal email, bank details | **National ID: hard refusal.** Others: hold |
| Names | Heuristic only; per-document human decision |

A hit requires a recorded decision (allow, redact or refuse), stored with the edition; a role address
can go on an allow-list. **Scanning supports human review; it doesn't replace it.** Anyone
determined can word an instruction so no pattern matches, which is why section 2.5's other layers
exist. Stronger tools such as Microsoft Presidio (NER) are C, and UNSURE on French names. Follows: OWASP
LLM04 and LLM08 [R].

### 4.5 Quality gate

An edition goes `active` only if:

1. The dry run passes, with decisions recorded.
2. **It has evaluation questions:** at least 3 per new document, at least 1 in French, each with a
   verbatim anchor, in the retrieval eval, written before seeing search results.
3. **No previously hit question is lost**, or each loss is explained and accepted in writing. With 14
   questions, one question is 7 points, so a percentage threshold would be noise.
4. Results are reported per domain and language, with counts, not only percentages. Domains under 10
   questions say so. Follows the project's rule of agreeing decision rules before seeing numbers.

The retrieval eval (no LLM calls) runs for every new document. Faithfulness runs when answer behaviour
changes materially, because each run uses about a day of free-tier quota [C].

**Effect on the eval sets from dropping the prestigious page (D5).** `rhodes_scholarship_en` and
`mccall_macbain_en` lose their anchors [M]. Step 0 therefore records the baseline both ways: the 14-question
set (last recorded at 85.7% Hit@5, MRR 0.717 [C]; re-measured in A0) and the 12-question set without them. Those two
become expected-refusal questions. The README, About page and CV quote the old figure, so they need
updating with the new one when it's real.

---

## 5. Retrieval and agent

### 5.1 Domain filter

`search_documents` gains an optional `domain`, an enum generated from the registry; default: all active
documents. Risk: a model picking the wrong domain silently loses recall. So it is not sent to the model
until the eval shows benefit from a real second domain, and the search widens to all domains if the
filtered one returns nothing. Build with the first department document (B3): with one domain it does
nothing measurable.

### 5.2 Version precedence

Superseded and withdrawn editions are never searched. Every search and course lookup filters
`edition_id = ANY(active_ids)` and `visibility = 'public'`, in code, in one shared helper, with a test
that loads two editions and proves the old one can't surface.

**A policy risk to surface.** The catalog says a student "may fulfill the requirements of the catalog
in force at the time of admission" (2024-25 p. 117) [M]. So for degree requirements, the newest catalog
isn't always the one that applies to a given student. You've decided superseded editions are not
searched, which is the right default, so the mitigation is a code-written note on catalog answers:
"Based on the 2025-2026 catalog. Your degree requirements may follow the catalog of your admission
year; confirm with your advisor." Ask AUI (Q1) whether that's accurate wording.

### 5.3 Answer format

| Rule | How it's enforced |
| --- | --- |
| Name the edition or date for catalog and time-sensitive content | **In code**: a line built from the citations and the registry, so it can't be forgotten |
| Bottom line first | Prompt, plus a reviewed sample in run 4. Can't be enforced in code |
| Expired `review_by` | Code-written note: "This document's review date has passed; check with [office]" |
| "Confirm with [office]" | Code-written, from `owning_department` |
| Course "not found" | Names the edition searched, in code |

### 5.4 Conflicts between departments

Conflicts should be surfaced, not silently resolved. Honest limit: **no reliable deterministic way to
detect that two passages conflict exists**, so this is a best effort until AUI defines authority (Q2, Q4).

1. Each passage header gives its department and date, so the model can see the difference.
2. The prompt says: if sources disagree, say so, cite both, name both offices, and don't choose.
3. Seeded conflict questions in the eval, per domain pair, with a scratch document (B3).
4. Authority rules from AUI, if they give any, shown as "the [office] is responsible for this topic".

Can't be tested today, because there's only one department's data. No build before B3.

### 5.5 Vector indexing and filtered recall at tens of thousands of chunks

**Today:** 1,161 chunks, exact scan, no vector index [M], pgvector 0.8.7 [M]. Exact search has perfect
recall, and pgvector's README gives no row-count threshold for changing [R]. Don't index until measured.

**Trigger:** p95 of the vector query above 50 ms, or more than 30,000 active chunks. Both numbers are my
estimates, to be replaced by the benchmark. UNSURE of exact-scan speed on this VM at 50,000 rows.

**Filtering is the subtle part.** "With approximate indexes, filtering is applied *after* the index is
scanned. If a condition matches 10% of rows, with HNSW and the default `hnsw.ef_search` of 40, only 4
rows will match on average" [R]. The search needs 20 candidates per list, so this would silently reduce
recall exactly when a domain filter is added.

| Plan | Detail |
| --- | --- |
| Index | HNSW, cosine, defaults (`m=16`, `ef_construction=64`) unless recall is low [R] |
| Filter | `SET LOCAL hnsw.iterative_scan = strict_order` (from 0.8.0 [R]); `max_scan_tuples` 20,000 by default [R] |
| Keep active share high | Keep only the last superseded edition, section 3.2 |
| Narrow filters | B-tree on `edition_id`; "exact indexes work well for conditions that match a low percentage of rows" [R]. Let the planner choose; check with `EXPLAIN` |
| Many domains or tenants | Partial indexes or list partitioning [R]; required for tenant isolation (3.7) |
| Build | After loading; set `maintenance_work_mem` without exhausting a 3.8 GiB host [R]. Build in `CONCURRENTLY` mode (UNSURE of the time; measure) |
| Keyword side | GIN index exists; fine at this scale [K] |

**Benchmark (B12):** in a scratch database, synthesise 10k, 30k and 100k chunks by duplicating and perturbing
real vectors, with 10%, 50% and 90% filters. Measure p50/p95 and **filtered recall@20 against exact**
(`SET LOCAL enable_indexscan = off` [R]) on the real eval queries, plus Hit@5 end to end. Accept at
recall@20 of at least 0.95. Memory is roughly 1.5 KB per vector before the graph, so about 100-150 MB at
50k (my estimate), which fits but should be checked next to the API's 1 GiB.

**French documents.** `to_tsvector('english', ...)` is hard-coded (`schema.sql:23`), and French department
documents are likely. Before the first one (B3): generate the column per row from `language`, search both
configurations, add French-document eval questions. The embedding model handles both already.

---

## 6. Infrastructure and operations

Baselines: CIS Ubuntu Linux 24.04, CIS Docker, CIS PostgreSQL, NIST SP 800-190 [K]. These are referenced
as guidance. No formal benchmark scan has been run; adding `docker-bench-security` and `lynis` reports is
part of B22, and each exception should be written down rather than assumed.

### 6.1 VM

Target configuration; B22 tracks progress.

| Setting | Target | Protects against |
| --- | --- | --- |
| `PermitRootLogin` | `no`. Was `without-password` on 2026-11-05, fixed 2026-11-06 (9580d89) | VM-3 |
| `X11Forwarding`, `AllowTcpForwarding` | `no`. Were both `yes` on 2026-11-05, fixed 2026-11-06 (9580d89) | VM-3 |
| `MaxAuthTries`, `AllowUsers` | 3, named users. Were 6 and not set on 2026-11-05, fixed 2026-11-06 (9580d89) | VM-3 |
| SSH key | Passphrase, ideally a FIDO2 `sk-` key. Had no passphrase on 2026-11-05, fixed 2026-11-06 (set on the key, no commit) | VM-2 |
| Admin vs. deploy | A separate user helps only if deploy goes through a narrow command, since docker access is root-equivalent. UNSURE it's worth it for one person | VM-2 |
| NSG | 80, 443 open; 22 from one /32. Azure Bastion or just-in-time at B | VM-5 |
| Host firewall | The NSG, accepted and documented. Docker's published ports bypass UFW anyway [K] | VM-5 |
| Automatic updates | On, with a reboot window Sunday 04:00 UTC. Downtime about 40 s, measured earlier [C] | VM-6 |
| Docker engine | Its origin in unattended upgrades, or a monthly manual update | VM-6 |
| Swap | 2 GiB, low swappiness. Was none on 2026-11-05, fixed 2026-11-06 (9580d89) | VM-7 |
| Build cache | `docker builder prune` on deploy | DB-5 |
| fail2ban | Not needed while SSH is limited to one address | Noted |
| Disk encryption | Azure platform default [K]. Accept | |
| Boot diagnostics | On, so a failed boot can be debugged | Recovery |

### 6.2 Containers

| Control | Caddy | Frontend | API | Postgres |
| --- | --- | --- | --- | --- |
| Non-root | Yes, with capability to bind low ports, or high port | `nginxinc/nginx-unprivileged` on 8080 | **Already** | Entrypoint drops to `postgres` [K] |
| `read_only: true` + `tmpfs` | Yes | Yes | Yes, with `/tmp` tmpfs. UNSURE about torch and HF caches: test | No: it needs its data dir |
| `cap_drop: [ALL]` | Plus `NET_BIND_SERVICE` if needed | Yes | Yes | No: test a minimal set, UNSURE which |
| `no-new-privileges` | Yes | Yes | Yes | Yes |
| Memory limit | Set after the load test | Set after the load test | Set after the load test | Set after the load test |
| `pids_limit` | 100 | 50 | 300 | 200 |
| Health check | Add | Add | `/health` | Exists [C] |
| Published ports (production) | 80, 443 | None | None | None |
| Network | Split: Caddy reaches frontend and API; only API reaches DB | Edge only | Edge + data | Data only |

Docker's `restart: unless-stopped` doesn't restart a merely unhealthy container [K], so an API that's up but
broken stays broken until the external alert fires. Accept at pilot.

### 6.3 Secrets

| Option | Protects | Cost | When |
| --- | --- | --- | --- |
| `.env`, mode 600 (today) | Other local users | None | Pilot, with separate DB passwords per role and a rotation runbook |
| Compose file-based secrets | Values out of `docker inspect` and the process environment | Small code change | **B4** with Key Vault; little gain alone, since root still reads them |
| Azure Key Vault + managed identity | Central audit, rotation, no secret at rest on VM disk | Small monthly cost (UNSURE); ties the design to Azure | **B4**, once hosting (Q6) is decided |

A vault doesn't help if the VM is compromised: an attacker with root reads whatever the app can read. The
benefit is audit and rotation, which matter more with more people. So it isn't tier A. Follows: OWASP Secrets
Management Cheat Sheet [K]; A04 and A07 [R].

**Rotation:**

| Secret | Procedure | When |
| --- | --- | --- |
| Groq API key | Create new, update `.env`, `up -d api`, verify, revoke old | Incident; yearly; when anyone with access leaves |
| DB role passwords | `ALTER ROLE`, update `.env`, restart API | Incident; yearly |
| `IP_HASH_SECRET` / code-hash key | New value, restart. Only resets limit counters | Incident; yearly |
| Access codes | Revoke the row; issue a new code | Leak, or end of each pilot phase |
| SSH key | Add new, test, remove old from `authorized_keys`; update NSG if needed | Incident; laptop change |
| Backup encryption key | New key for new backups; keep the old one until old backups expire | Incident |
| GitHub, Azure credentials | Provider's console; 2FA required | Incident |

Calendar-based rotation of everything isn't useful for one operator; compromise-driven rotation plus a yearly
check is a reasonable start. Follows NIST SP 800-57 lifecycle thinking [K]. UNSURE whether AUI's policy
demands more.

### 6.4 Security headers and TLS

Live since 2026-11-05 (ce1d9a3). Was: no CSP, frame control or `Permissions-Policy` on 2026-11-05.

```
Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self';
  img-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'none';
  form-action 'none'; frame-ancestors 'none'
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cross-Origin-Opener-Policy: same-origin
```

HSTS `max-age=31536000`, `nosniff` and `Referrer-Policy: strict-origin-when-cross-origin` stay. TLS 1.2 and 1.3 only.

- Enforced under the rule recorded in `CLAUDE.md`: zero violations in Chrome, Firefox and WebKit on the listed pages, rerun after each Caddy upgrade with `deploy/csp-check`.
- HSTS `includeSubDomains` and preload: not for a shared Azure name. Consider on the custom domain only (C).
- TLS: Caddy's defaults already match Mozilla's "intermediate" guidance [K]. No change.
- Caching: add `public, max-age=31536000, immutable` on `/assets/*` and `no-cache` on `index.html`. A mobile and cost improvement, not a security one.
- Add `/.well-known/security.txt` (RFC 9116 [K]) and `SECURITY.md`.

Follows: OWASP Secure Headers Project, OWASP CSP Cheat Sheet, Mozilla Web Security Guidelines [K]. Protects against:
BR-1 to BR-4, CD-3.

### 6.5 Scanning in CI

| Tool | Scans | Fails the build when | Exception process |
| --- | --- | --- | --- |
| `gitleaks` | Commit range, weekly full history | Any finding | Allow-list entry with a reason, in the repo |
| GitHub secret scanning + push protection | Pushes | Blocks the push | Reviewed by hand. On since 2026-11-06 |
| `pip-audit` on the lockfile | Python | High or critical with a fix available; **any** fixable in a runtime path | Dated `--ignore-vuln` entry, reason, expiry at most 30 days |
| `npm audit --omit=dev` | Production JS | High or critical | Same. Full audit shown but not blocking |
| `Trivy image` | Built API and frontend images, Caddy and Postgres images | High or critical with a fix, OS and libraries | `.trivyignore` with reason and expiry. Unfixed CVEs: reported, not blocking, or the build would be red for reasons nobody can fix |
| `Trivy config` | Dockerfiles, Compose | High misconfiguration | Reasoned ignore |
| Dependabot | Python, npm, Actions, Docker | Opens PRs, weekly, grouped | Reviewed like any change; CI must pass |
| Tracked-data check | New files under `data/`; known-pattern names | Any non-allow-listed data file | Reviewed by hand |
| Weekly scheduled run | Same as above, on `main` | New CVE with no code change | Opens an issue |
| `ruff --select S` (bandit rules) | Python | New high-confidence issue | Inline `noqa` with reason |
| CodeQL | Python, TypeScript | High severity | Free on public repos [K]; B13 |

**Lockfile.** `uv pip compile` or `pip-compile --generate-hashes` for a CPU-only Linux target. The Dockerfile
and CI install with `--require-hashes` from the same file, so CI tests what's deployed. UNSURE how cleanly
torch's CPU index combines with hashes; expect some work. Declare `httpx`. Generate an SBOM with Trivy or Syft (B13).

**Actions:** pinned by commit SHA, with Dependabot to bump them, and `permissions: contents: read` at the top.
**Images:** pinned by digest, bumped by Dependabot. **Model:** `revision=<commit>` for the embedding model.
**Branch rules:** require the CI checks, block force-push and deletion. A review requirement makes no sense for
one person. Follows: NIST SSDF SP 800-218, SLSA, OpenSSF Scorecard [K]; A03 [R]; LLM03 [R].

### 6.6 Privacy-preserving logging, metrics and alerting

One JSON line per request, a closed set of fields, **no free text**:

```json
{"ts":"...","route":"/chat","status":200,"ms":3120,"first_progress_ms":420,"answer_ready_ms":3050,
 "llm_calls":2,"tokens_in":2036,"tokens_out":243,"tool_calls":1,"gate":"passed","fallback":false,
 "lang":"en","editions":["academic_catalog_2025_2026"],"commit":"abc1234","error_type":null}
```

Extend `test_log_privacy.py`: logged fields come from a closed list, and a marker question must appear in
no log. Pilot metrics come from `jq` over the log, in a small daily summary: no extra services on a 4 GB VM.

| Alert | Condition | Channel |
| --- | --- | --- |
| Site down | External check on `/ready` fails twice | Email to at least two people once AUI is involved |
| Certificate | Under 14 days left | Same |
| Budget | Azure 50/80/100%; Groq spend, tokens today over 80% | Same |
| Disk | Over 80% | Same |
| Errors | 5xx over 5% in 15 min, or gate rejects spike | Daily job at pilot; B10 for real-time |
| Backup | Last successful backup older than 26 h | Same |
| Review dates | `review_by` under 30 days | Weekly issue |
| Model | Provider deprecation notice for the pinned model | Monthly manual check |

**Health checks.** `/health`: process alive (keep). New `/ready`: DB reachable, embedding model loaded, at least
one active edition, and the commit. No provider call, to keep it free. Both return only status. B10 adds
Grafana or Azure Monitor once there's more than one instance. UNSURE which, and depends on hosting. Follows:
A09 [R]; OWASP Logging Cheat Sheet [K].

### 6.7 Incident response

Follows NIST SP 800-61r3's prepare, detect, respond, recover cycle [K]. Written as `docs/runbook.md` in B28.

| Severity | Examples | Respond within |
| --- | --- | --- |
| **S1** | Secret leaked, VM compromised, personal or non-public data exposed, harmful answer spreading | Immediately, same day |
| **S2** | Service down, wrong answer on a deadline or amount, quota abuse | Within a working day |
| **S3** | Single wrong answer, UI bug | Next planned work |

**Kill switches that already exist or are cheap:**

| Need | Action | Time |
| --- | --- | --- |
| Stop all live answers, keep saved examples | `DAILY_QUESTION_CAP=0`, restart API (limit 0 was tested [C]) | 1 min |
| Stop provider traffic | Revoke the Groq key | 1 min |
| Bad document | Roll back the edition (A2.3) | Under 1 min |
| Take site down | `docker compose stop caddy` | 1 min |
| Lock out everything | Remove the NSG rules | 2 min |

**Steps:** (1) Record the time and what's known, outside the affected system. (2) Contain with a switch above.
(3) Preserve logs before any rebuild: recreating a container deletes its log [C]. (4) Rotate anything possibly
exposed. (5) If personal data may be involved, tell AUI's contact (Q8) and let them decide what follows. (6) Recover
from a known commit and a verified backup, on a new VM if compromise is possible. (7) Write a short review: cause,
fix, added test.

**A wrong-answer report is an incident too:** find the document and edition, reproduce it, add it to the eval set,
decide fix or rollback, and tell the reporter if known.

---

## 7. Scalability and performance

### 7.1 What breaks first, in order

**Baseline per question** [M], run 3: about 4,800 tokens on average, 2.6 LLM calls. Real latency from two saved traces: 2.8 and 3.5 s. **Run 3's 25 s median includes the
evaluation's own throttling, so it isn't real latency.** The two traces are from a development machine. So
production latency hasn't actually been measured under any load.

**Assumption for the campus estimate:** 2,500 students (UNSURE: AUI to confirm), 20% active daily, 3 questions each
= **1,500 questions a day**, 7.1 million tokens. Busiest hour 15% = about 4 a minute; bursts of 3x = about 11 a
minute, 54,000 tokens a minute. These are assumptions to replace with pilot data.

| # | What breaks | At about | Evidence | Path past it | Step |
| --- | --- | --- | --- | --- | --- |
| 1 | **Groq free tier** | Light use, per the provider's published free-tier limits | [R] | Developer plan: 250k TPM, 1k RPM listed [R]. About 52 questions a minute. 1,500/day costs about **$0.72/day, $22/month** at $0.075/$0.30 per M tokens [R] | B25 |
| 2 | **Per-IP limits** behind NAT | The second student on campus Wi-Fi | [C], Q9 | Access codes, then SSO | B25, B2 |
| 3 | **The Azure credit** | About January 2027 | [R] | Pay or move | D1 |
| 4 | **Connection churn and blocked event loop** | UNSURE; load test | No connection pool; admission runs on the event loop | `psycopg_pool`, off-loop admission, tool cap | B20, B6 |
| 5 | **Embedding on CPU** | UNSURE: 1 to 3 phrasings per search, on burstable CPU. Sustained load may use up its credits [K] | Not measured on the VM | Measure; cache query embeddings per process; ONNX-quantised model; larger non-burstable VM | B29, B6 |
| 6 | **Memory** | A second API process | Each one loads its own embedding model | Separate embedding service, then scale the API separately | B6 |
| 7 | **Single VM** | Any host or zone failure | One VM | Two instances behind a balancer plus managed Postgres, **only if the availability target needs it** | B5 |
| 8 | **Global advisory lock** | High admission rates | Serialises all checks [C] | Per-user locks, or atomic upsert per user | B2 |
| 9 | **Exact vector scan** | Tens of thousands of chunks | Section 5.5 | HNSW | B12 |

An interesting result of this table: at the assumed load, and 3-4 s per question, the **average concurrency is
under 1**, with bursts of a few. The real constraints are provider quota, identity and availability, not
raw throughput. An exam-week spike of 10x (110 a minute, about 520k TPM) would exceed the listed Developer limit,
so it would need a higher plan or a queue. UNSURE: load test will show whether the VM agrees with this arithmetic.

### 7.2 Design paths

| Topic | Today | Design |
| --- | --- | --- |
| Stateless API | Already nearly so: history in the client, limits in Postgres, per-request state in `ContextVar`s [C] | Keep. `_HASH_KEY` must be set, not random, with more than one process. Per-process URL cache is harmless |
| Connection pooling | One connection per query | `psycopg_pool` in the API (B6). PgBouncer only with several API hosts; check prepared-statement and `register_vector` compatibility (UNSURE) |
| Caching | None | (a) Query-embedding LRU per process: cheap, no personal risk. (b) Answer cache by normalised first-turn question and active edition set: stores question text, so a separate decision. Count repeats via HMAC first, to see if worth having. (c) Invalidate on any activation |
| Provider abstraction | `LLM_PROVIDER` at startup; `groq.RateLimitError` and `tool_use_failed` handling are Groq-specific in `main.py` and `graph.py` [C] | One interface with normalised errors. Circuit breaker: after N failures, skip for M seconds. **The fallback must meet the same legal and data rules**, and has to pass the eval first: prompts were tuned for one model, and faithfulness varies by model |
| Per-user limits | Per IP | Pilot: per access code (daily and per 10 minutes). Campus: per SSO identity. Keep a global token budget. Count tokens, not only questions |
| Cost controls | Azure budget alert | Global daily token budget in code, enforced before each LLM call; `max_tokens`; prompt size watched in the eval; evaluation on a separate key, so it can't eat the service's quota |
| Queue under pressure | None | At B: a small concurrency limit, with a "busy" message, rather than failing everything |

### 7.3 Targets

Measured externally and from the event log. **Provisional until the load test and first pilot week** give real numbers.

| Indicator | Pilot | Campus-wide |
| --- | --- | --- |
| Availability, monthly, of `/ready` | 99% (7.2 h of allowed downtime) | 99.5% (3.6 h) |
| First progress shown (p95) | 2 s | 1.5 s |
| Answer ready: p50 / p95 | 5 s / 15 s | 4 s / 10 s |
| Non-LLM endpoints (p95) | 300 ms | 200 ms |
| Failed answers (excluding limits) | Under 2% | Under 1% |
| Concurrent questions handled inside targets | 5 | 20 |
| RTO / RPO | Section 3.5 | Section 3.5 |

99.9% would need redundant hosts and a redundant provider, which isn't justified for a tool whose failure means "ask
the Registrar". UNSURE about Azure's single-VM SLA figure on Standard SSD (from memory, about 99.5% [K]), so 99.5% on one VM
is tight; B5 decides based on the pilot's real record.

### 7.4 Load test

**Never against production, and never using Groq quota.**

| Item | Design |
| --- | --- |
| Environment | A temporary B2s VM built from the same steps, deleted afterward; less than $1 of compute |
| LLM | A small stub server with the OpenAI-compatible shape, returning realistic tool calls and answers with delays from the traces. Real embeddings and Postgres |
| Tool | `k6` (or Locust if Python is easier to defend) |
| Profiles | Ramp 1, 3, 5, 10, 20, 30 concurrent, 5 min each. Soak at 5 for 30 min. Spike 0 to 30. Limits bypassed by config in the test environment only |
| Watch | Latencies, errors, CPU steal and credits, memory, Postgres connections, event-loop lag, disk |
| Also | Oversized bodies, client disconnects mid-run (does the run stop?), DB restart mid-test |
| Pass | Section 7.3's pilot column; no memory growth over the soak; clean failures past the limit |
| Provider check | Separately, with the paid plan: 20 real questions, for real latency. Costs about 1 cent |

---

## 8. Usability and accessibility

### 8.1 WCAG 2.2 AA review

WCAG 2.2 is the current W3C Recommendation, with 9 new criteria since 2.1 and 4.1.1 Parsing removed [R].

**What this review is:** code reading plus Lighthouse on the first screen, which scored 100, with **10 manual checks
not run** [M]. Automated tools find only a part of real problems [K]. **No screen reader or keyboard session has
been done for this document.** So "Fail" means the code shows the problem, "Pass" means evidence is good so far, and
"Verify" means it must be tested. Conclusive review requires a real pass with NVDA and VoiceOver (B26), and ideally a
disabled student (B15).

| Criterion | Level | Status | Evidence and fix |
| --- | --- | --- | --- |
| 1.1.1 Non-text content | A | Pass | Charts have labels; icons have `aria-label` or `aria-hidden` [C] |
| 1.3.1 Info and relationships | A | **Fail (minor)** | Questions are plain `<p>`; a thread has no heading once started. Use a list of turns and an `h1` |
| 1.4.3 Contrast | AA | Pass (calculated) | All text token pairs are 5.3:1 or better in both themes [M]. Verify states such as pending chips and disabled send |
| 1.4.4, 1.4.10 Resize, reflow | AA | Verify | 390 px worked; 320 px and 200% zoom unchecked; tables scroll sideways, allowed [C] |
| 1.4.11 Non-text contrast | AA | **Likely fail** | Composer and card borders are 1.3:1 [M]. Raise the composer border to 3:1 |
| 1.4.12 Text spacing | AA | Verify | |
| 2.1.1 Keyboard | A | Verify | Native elements; Enter sends and Shift+Enter breaks a line [C] |
| 2.3.3 / reduced motion | AAA, good practice | Pass | Handled in CSS and JS [C] |
| 2.4.1 Bypass blocks | A | Verify | `main`, `nav` landmarks exist; add a skip link |
| 2.4.2 Page titled | A | Pass | Changes per view [C] |
| 2.4.3 Focus order | A | **Fail** | A chip scrolls to its card without moving focus; hash navigation doesn't move focus to the new view [C] |
| 2.4.4 Link purpose | A | **Fail** | A chip's only name is "1". Use `aria-label="Source 1: Academic Catalog, page 117"` |
| 2.4.7 Focus visible | AA | Pass | `:focus-visible` globally; composer has `:focus-within` [C]. Verify in dark mode |
| 2.4.11 Focus not obscured | AA, new | **Likely fail** | Sticky top bar and tall composer; only cards have `scroll-margin`. Add `scroll-padding` |
| 2.5.7 Dragging | AA, new | Pass | No dragging |
| 2.5.8 Target size | AA, new | Pass, mostly | Icons 32 px, send 34 px. Chips fall under the inline exception but are tiny: 10.5 px text. Enlarge on touch screens |
| 3.1.1 Language of page | A | Pass in English | `lang="en"` fixed. Must follow the chosen language (B26) |
| 3.1.2 Language of parts | AA | **Fail** | French answers and questions have no `lang` [C]. Set from `detected_language` |
| 3.2.6 Consistent help | A, new | Pass | "Check with the Registrar" is in a constant place. Keep as offices get named |
| 3.3.1, 3.3.3 Errors | A, AA | Verify | New length errors must be specific and suggest a fix |
| 3.3.7 Redundant entry | A, new | Pass | Nothing re-entered. Keep the access code remembered |
| 3.3.8 Accessible authentication | AA, new | Design rule | Access code must allow paste; SSO later must not rely on memory puzzles |
| 4.1.2 Name, role, value | A | **Fail (minor)** | `aria-label` on a role-less skeleton `div` isn't reliably exposed [C] |
| 4.1.3 Status messages | AA | **Fail** | Errors and limits are announced [C], but **"answering" and "answer ready" are not**. A screen-reader user gets no signal that the answer arrived. Add one polite live region announcing state changes, not tokens |

**Note on the buffered answer:** section 2.4 helps here, because a complete answer appears at once, and is announced once.

### 8.2 Keyboard and screen readers: acceptance script (B26)

1. Reach and send a question using only the keyboard.
2. Hear "Searching", then "Answer ready"; move to the answer in one action.
3. Move from a chip to its source and back, hearing what each is.
4. Open a source, understand it opens in a new tab.
5. Hit an error, a refusal and a limit: each read out, each with a next step.
6. Do all of it in French.
7. Repeat with NVDA + Firefox, VoiceOver + iOS Safari, and TalkBack + Android Chrome if possible.

### 8.3 Mobile performance

Measured on simulated mobile, Lighthouse 13.6 [M]: FCP 1.5 s, LCP 1.8 s, TBT 50 ms, CLS 0, Speed Index 3.9 s,
218 KiB; server response 70 ms. Live chat state isn't covered, and this is simulation. An earlier Lighthouse version
flagged illegible font sizes, and the CSS has 30 sizes at 11 px or below [M].

| Action | Why |
| --- | --- |
| Minimum 12 px; 13 px for source text on phones | Legibility; 10.5 px chips and labels |
| Long-lived caching for hashed assets | Repeat visits on mobile data |
| Reduce from five font files | Largest assets after the JS |
| Investigate Speed Index 3.9 s vs. LCP 1.8 s | Possibly entrance animation; UNSURE |
| Test a real low-end Android on campus Wi-Fi and on mobile data | Simulation isn't reality |
| Budgets in CI: JS under 170 KB, total under 300 KiB | Prevent drift. Set after measuring current JS (138 KB transferred [M]) |

### 8.4 Clear states, in both languages

Today French exists for limit messages, the privacy notice and code fallbacks [C]; everything else is English:
"Sources", "Open at page", "Ask again", "Your question", the connection messages, the disclaimers, the first screen.

**A19:** one small dictionary, no i18n library, a language toggle next to the theme button. Default from
`navigator.language`, stored like the theme. **The answer language still follows the question**, as now.

| State | English | Français | Next step offered |
| --- | --- | --- | --- |
| Thinking | Searching the documents... | Recherche dans les documents... | Progress lines |
| Not in documents | I couldn't find this in the documents I have. | Je n'ai pas trouvé cette information dans mes documents. | Office to ask, rephrase |
| Out of scope | I answer questions about [generated scope]. | Je réponds aux questions sur [portée générée]. | Examples |
| Personal limit | You've reached your limit. You can ask again at 14:30. | Vous avez atteint votre limite. Vous pourrez reposer une question à 14 h 30. | Saved examples |
| Daily limit | Today's limit is reached. Please come back tomorrow. | La limite du jour est atteinte. Revenez demain. | Saved examples, office |
| Busy | The assistant is busy. Try again in a minute. | L'assistant est très sollicité. Réessayez dans une minute. | Retry |
| Connection | The connection dropped. | La connexion a été interrompue. | Retry |
| Too long | That's too long: please keep it under 2,000 characters. | Message trop long : 2 000 caractères maximum. | Counter from 1,800 |
| Safety | [AUI-approved message and contacts] | [message et contacts approuvés par l'AUI] | Contacts |

Exact wording to be reviewed by a native French reader, and by AUI for safety text.

### 8.5 Citations non-technical students understand

| Today | Proposed | Why |
| --- | --- | --- |
| `[1]` tiny chip | Slightly larger chip, with a clear name for screen readers | Touch and legibility |
| Card: "Academic Catalog 2024-2025 · p. 117 · Undergraduate Studies > Repeat Policy" | Keep; say "page", not "p." on cards | Plain |
| "Open at page" **on every link, including web pages with no pages** (`AssistantTurn.tsx:121`) | "Open at page 117" for PDFs, "Open the page" for web | A real small bug |
| No explanation | One line above sources: "Where this answer comes from. Check the original for anything important." | Sets the right habit |
| Grouped `[2, 4]` stay plain text [C] | Normalise to `[2] [4]` in code | Every citation clickable |
| "Hit@5", "prerequisite links", "AI agent" on the first screen | **Pilot mode:** say what it covers, how to use it, what it can't do. Technical showcase stays in About and "Under the hood" | The first screen currently speaks to recruiters, not students |
| Disclaimer in small print | Keep the unofficial note plus an honest, plain accuracy line | Run 3 says it matters |
| Nothing after an answer | "Report a problem" link: student chooses to send it | BR-6; the only learning channel, since nothing is stored |

---

## 9. Prioritised roadmap

**Effort is a rough estimate for one person with AI assistance, following this project's one-step-per-turn method.**
Treat it as plus or minus 50%. Days are working days.

### Tier A: required before a student pilot (about 13 days)

Split on 2026-11-05. **A1 was urgent security, deployed first; A0 and A1 are done. A2 is next.** Each step is done one at a time, with tests,
and confirmed before the next. A0 was recorded early, on 2026-11-05, while A1 was in progress. That's harmless, because
no A1 step changes the documents or the search, and the eval is re-run after A1.4 as a check.

#### A1: urgent security (about 3 days)

| Step | What | Protects against | Depends on | Days |
| --- | --- | --- | --- | --- |
| **A1.1** | No images in rendered answers, in every Markdown renderer, with hostile-Markdown tests | BR-1 | None | 0.25 |
| **A1.2** | Content Security Policy, report-only first and then enforced (deployed separately, see below), plus the other missing headers | BR-1, BR-3, BR-4, CD-3 | None | 0.5 |
| **A1.3** | Request size limits on `/chat`, in Caddy and in the API. **Field limits from section 2.1, moved here from B20 because they cap LLM tokens**, checked before the rate limit, so a rejected request isn't counted. A fixed 422 with no input in it (AP-6, also moved from B20). In the UI, a counter at the composer and a history that fits the limits, dropping whole turns | CD-1, AP-1, AP-6 | None | 0.5 |
| **A1.4** | Least-privilege role for the API: read content, write only `question_log`. Schema creation moves out of API startup, because the role can't run DDL. A test proves the rights. A written rollback plan comes first. The retrieval eval is re-run afterwards and compared with the A0 baseline | DB-1, DB-2, TL-1 | None | 1 |
| **A1.5** | Automated off-VM backups: daily, encrypted, content only, with a restore into a scratch database to prove they work | DB-4, VM-1 | Storage location decided at this step; **it must not be on Azure** | 0.75 |

**Deploy order, each one checked on the live site:**

1. A1.1 and A1.2 with the CSP in report-only mode.
2. CSP enforced, and A1.3.
3. A1.4 alone, with its written rollback plan.
4. A1.5 once its storage is chosen.

All deployed by 2026-11-06.

#### A0: baseline

| Step | What | Depends on | Days |
| --- | --- | --- | --- |
| **A0** | Retrieval baseline on both the 14- and 12-question sets, recorded with the DB state. 0 LLM tokens. **Done**: `eval/results/retrieval/2026-11-05_a0_baseline.md` | None | 0.25 |

#### A2: pilot readiness (about 9.5 days)

| Step | What | Protects against | Depends on | Days |
| --- | --- | --- | --- | --- |
| **A2.1** | Registry: `data/registry.toml`, tables, one read function; replaces the lists in `load.py`, `sources.py`, `tools.py`, `chunk.py`, `courses.py`. **Retrieval unchanged** | Foundation | A0, A1.4 | 0.5 |
| **A2.2** | Generated scope and UI text: prompt, tool description, UI note, meta description, first screen; committed JSON pinned by a test. Also `frontend/src/about.ts:61`, `components/AboutPage.tsx:19`, `components/ArchitectureDiagram.tsx:120,249`, the tool and prompt text at `tools.py:110,119,256` and `graph.py:26-28`. Deletes the dead `generation.py` prompt: nothing imports it, and it reads like the live one. **Retrieval unchanged** | AG-5 | A2.1 | 0.5 |
| **A2.6b** | Answer-level gate: any answer without a search call and valid citations is replaced by code-written text, so greetings and questions about the assistant still work. The answer is held until checked, because text already streamed can't be replaced. A cited course lookup counts as a search call. Adds an off-topic and injection category to the eval set; see its acceptance criteria below | AG-2, AG-3 | A2.2 | 1.5 |
| **A2.3** | Version precedence: per-edition chunks, courses, prerequisites; filter on active; activate and rollback CLI; test with two editions. The list of what it breaks is in section 3.2. **Retrieval unchanged** | AG-5, TL-4, IN-3, IN-8, DB-8 | A2.1 | 1.5 |
| **A2.4** | Per-document ingestion: loader interface, PDF and web loaders, HTML tables intact, refusals, dry run, sanitising, scans, `visibility` gate; see its findings and acceptance criteria below | IN-1 to 7, AG-1, AG-11 | A2.3 | 2 |
| **A2.5** | Drop the prestigious page and remove "Lorem Ipsum" through the new pipeline. Eval sets updated. Production dump is content-only | AG-11, IN-2 | A2.4 | 0.5 |
| **A2.6** | 2025-2026 catalog through the pipeline: page-header fix (`PAGE_HEADER_LINES`, `chunk.py:50`, byte-identical until this step), eval questions and anchors written first, saved examples regenerated or labelled, counts updated. Then the retrieval eval, with its decision rule recorded first: no previously hit question lost unless explained, rollback if not | AG-5 | A2.4, D8 | 1.25 |
| **A2.7** | Scope and bottom-line-first prompt changes; catalog-year note; see its acceptance criteria below | AG-4, section 5.2 | A2.2, A2.6b, Q1 | 0.5 |
| **A2.8** | Faithfulness run 4, single run; hand-check failures; apply threshold D3. If it fails, the pilot waits. The reviewed sample excludes fallback answers, using the flag at `graph.py:205` | AG-4 | A2.7, D3 | 1 |

**A2.1 is built and pushed, and deploys once accepted.** Retrieval eval identical to the A0 baseline, line for line:
`eval/results/retrieval/2026-11-06_a2_1.txt`.

**Order, decided 2026-11-06:** A2.1, A2.2, A2.6b, A2.3, A2.4, A2.5, A2.6, A2.7, A2.8. Step numbers don't change. Students
testing the demo reported that it answered "What is 1 + 1?" and that answers make them read several paragraphs first.
A2.6b depends only on A2.2, it fixes the off-topic answers sooner, and A2.6 is blocked on AUI (D8).

**Also decided 2026-11-06.** Domain-aware retrieval stays at B3 (section 5.1), and conflict handling between departments
stays at B3 (section 5.4). There is no LLM-based scope classifier: the gate is structural and costs no tokens.

**Acceptance criteria, set before any results:**

- **A2.6b.** The off-topic set includes "What is 1 + 1?", "What is the capital of France?", "What programs does AUI
  offer?", "What is AUI's add/drop policy?", a mixed general + AUI question, and an AUI question the documents don't cover
  (expected: the not-found template).
- **A2.4.** Scratch-database fixture documents (one dining, one finance, a second academic) prove that they coexist, that
  attribution stays correct, and that withdrawing one leaves the other documents' chunk counts and retrieval ranks
  unchanged. Embeddings only, 0 LLM tokens.
- **A2.7.** Full detail is kept when the student explicitly asks for it.

**Findings from the audit of 2026-11-06, carried into later steps** (line numbers here and in the table above are at
commit `c1571e7`):

- **A2.4.** Three assumptions of the single-document pipeline go: the catalog's part headings are applied to every
  document (`chunk.py:32-36`); English is hardcoded (`chunk.py:64`, `schema.sql:23`, `keyword_search.py:33,36`); folder
  scans turn any stray file into a source (`clean.py:36`, `chunk.py:319`). Ingestion must refuse files that aren't in the
  registry.
- **A2.7.** The forced-answer rule must say "answer the student's question", not "the last message": the forced
  conversation ends with the search results, not the question (`graph.py:172`). Leave the fallback's wording alone, because
  `history.py:38` matches it by prefix. Regenerated examples change the first screen's proof card (`answerFormat.ts:27-30`).

Effort is re-estimated from the original tier A figures and carries the same plus or minus 50%.

**What moved to tier B, and what that means.** These were tier A in the first version of this document. Moving them
is a decision, so their consequences for a pilot should stay visible:

| Moved | Consequence until it's done |
| --- | --- |
| **B24** failure modes, passage framing, edition and office lines, safety template, planted-document tests | No safety path exists for a student in distress. Passages aren't marked as data, so a planted instruction has a better chance of working, though A1.1 and A1.2 limit what it can do. The answer-level gate itself is now A2.6b |
| **B25** access codes, per-user limits, token budget | **Per-IP limits apply to a pilot, pending AUI's answer to Q9.** If campus Wi-Fi shares an address, all students share 5 questions per 10 minutes. The question cap is the only cost control on the paid plan, so it must stay finite |
| **B28** runbook, `SECURITY.md`, `security.txt` | No written incident procedure during the pilot |
| **B26** French UI and accessibility fixes | Screen-reader users get no signal that an answer arrived; the interface stays mostly English |
| **B20** tool-call cap, `max_tokens`, timeouts, deadline | Consumption is limited at the input by A1.3's size and field limits, not at the output |
| **B21, B22** supply chain, VM hardening | No Python lockfile or image scanning; containers aren't at the hardened baseline |
| **B19** link allow-list | Model-written links can still go anywhere, though they need a click. CSP doesn't stop a click |

**Pilot exit criteria:** A1 and A2 done; threshold D3 passed; restore proven; AUI's written agreement; a named person
watching the service during the pilot. A data-protection review with AUI is a pilot exit criterion.

### Tier B: required before a campus-wide launch

Triggers matter: some are due **before the first department document**, even during the pilot.

| Step | What | Protects against | Trigger / depends on | Days |
| --- | --- | --- | --- | --- |
| B1 | Table-aware PDF: eval questions on tables first, extractor comparison, parent-child retrieval, hidden-text scan | IN-1, wrong table answers | **Before first table-heavy PDF.** A2.4 | 2-3 |
| B2 | AUI SSO; per-user limits; per-user locks; retire codes | AP-3, AP-7 | AUI IT (Q9). B25 | 2-4 |
| B3 | First department document: domain filter, conflict prompts and tests, per-row French search, French eval, DOCX or XLSX loader if needed | Section 5, AG-4 | **First department document.** Q2, Q4 | 3-5 |
| B4 | Key Vault and managed identity; Compose secrets | VM-8 | Hosting decided | 0.5-1 |
| B5 | Availability decision: managed Postgres and/or second API, TLS to DB, Bastion. From the pilot's record | VM-7, DB-6 | Pilot data | 2-5 |
| B6 | Connection pool, tool-only DB role, embedding cache, separate embedding service if needed, optional answer cache | TL-3, section 7 | B29 | 2-3 |
| B7 | Second provider: normalised errors, circuit breaker, passes the eval and adversarial set | GQ-2, GQ-3, GQ-6 | Q5, Q6 | 2-3 |
| B8 | Fix D: citation placement (largest cause), number check in shadow mode, evaluate a per-block gate | AG-4 | Run 4 | 2-3 |
| B9 | Undergraduate/graduate level filter; multilingual reranker evaluation | AG-4 | Run 4 | 2-3 |
| B10 | Metrics and alerting with real-time paging; shipped host logs; published status page | A09, VM-10 | B5 | 1-2 |
| B11 | Provisioning as code (Bicep or Terraform, cloud-init), staging environment, CI deployment with signed images | VM-9, RTO 1 h | Hosting decided | 2-3 |
| B12 | Vector benchmark, HNSW at the trigger, filtered-recall test in CI | Section 5.5 | Corpus growth | 1-2 |
| B13 | SBOM, CodeQL, OpenSSF Scorecard | A03, A08 | B21 | 0.5 |
| B14 | Sandboxed ingestion container; ingestion away from the laptop | IN-5, IN-6 | Non-public or many documents | 1 |
| B15 | External WCAG 2.2 AA audit with disabled students, fixes | Section 8 | B26 | Fixes vary |
| B16 | Admin page and DB-only registry; department review workflow, review reminders; retrieval eval per domain as routine | Governance | Many documents | 3-5 |
| B17 | Independent security review or penetration test; formal contracts with providers | All | Before launch | External |
| | ***Moved from tier A on 2026-11-05*** | | | |
| B18 | Groq Zero Data Retention on, read Groq's DPA; correct CLAUDE.md on the fallback and DEPLOY.md ("the repo is private") | GQ-1, GQ-5, GQ-6 | D2 | 0.25 |
| B19 | Link allow-list in answers; cache headers. Docs routes went off on 2026-11-06 (24cb771) | BR-2 | A2.1 | 0.25 |
| B20 | API and agent limits: the rest of section 2.1 (`/sources` parameters, tool arguments and calls, not the `/chat` body and field limits, which moved to A1.3), `max_tokens`, timeouts, deadline, disconnect test, off-loop admission, concurrency test. Statement timeout, connection limit and Caddy timeouts went live on 2026-11-06 (852333a, 22835b1) | AP-5, 10, AG-6 to 9, TL-2, TL-5 | None | 1 |
| B21 | Supply chain: hashed lockfile, audit jobs, Trivy, gitleaks, Dependabot updates, required CI, SHA pins, digests, model revision, tracked-data check. Secret scanning, push protection, Dependabot alerts, the force-push rule and the Caddy upgrade were done on 2026-11-06 | GH-1 to 6, VM-6, VM-9, IN-6 | None | 1 |
| B22 | VM and containers: the rest of sections 6.1 and 6.2, prune on deploy, `docker-bench` and `lynis` reports. SSH hardening, swap, key passphrase and dev port binding were done on 2026-11-06 | VM-2, 4, 5, 6, 7, DB-5 | B21 | 0.75 |
| B23 | First timed rebuild from nothing; scheduled `question_log` cleanup | DB-7, RTO | A1.5 | 0.25 |
| B24 | Rest of the gate: truncation case, failure modes (2.6), passage framing, edition and office lines, safety template, planted-document adversarial tests | AG-1, AG-4, AG-10, BR-6 | A2.6b, A2.3, Q11 | 1.5 |
| B25 | Access codes (hashed, rate limited, revocable), per-code limits, daily token budget, separate evaluation key | AP-2, AP-3, AP-7, GQ-2, GQ-4 | D2. Reconsider on AUI's answer to Q9 | 1 |
| B26 | French UI, must-fix accessibility (the Fail rows), first-screen pilot mode, citation changes, report link; screen-reader script | Section 8 | B24 | 1.5 |
| B27 | Event log + privacy test, `/ready` with commit, external uptime and certificate check, daily summary, disk and backup alerts | AP-8, CD-4, CD-6, DB-5, VM-9 | B20 | 0.75 |
| B28 | `docs/runbook.md` (incidents, rotation), `SECURITY.md`, `security.txt`, and whatever notice the data-protection review requires before the pilot | Pilot exit criteria (tier A), section 6.7, GQ-1, VM-11 | Q5, Q8 | 0.5 |
| B29 | Load test with the stub; targets confirmed or revised; container limits from results | VM-7, section 7 | B20, B22 | 0.75 |

### Tier C: later

Non-public documents and access control (section 3.7; a project in itself). Named-entity personal-data scanning. Edge WAF and
DDoS service, if abuse appears. Multi-region. Self-hosted or EU-hosted model. Conversation accounts or saved history. HSTS
preload on a custom domain. Signed commits, SLSA provenance. Arabic. Analytics on anonymous question topics, if AUI wants it.

---

## 10. Open questions for AUI

Kept outside this document, and referred to here as Q1 to Q12.

---

## 11. Sources and their limits

### Read directly for this document

| Source | Used for | Limits |
| --- | --- | --- |
| owasp.org Top 10:2025 (top10.owasp.org/2025) | 1.13 | The page states no release date |
| genai.owasp.org: LLM Top 10 2025, LLM01 | 1.14, 2.5 | |
| console.groq.com: your-data, rate-limits, models, services agreement | Groq facts | Agreement: first part verbatim, the rest summarised. Rate-limits page doesn't clearly label which plan its table covers; session measurements support it being the free plan. DPA **not** read |
| aistudio.google.com/docs/terms | Gemini terms | Effective 2026-03-23 |
| learn.microsoft.com, Azure for Students disabled page | VM-1 | No data-deletion timeframe given |
| github.com/pgvector/pgvector README | 5.5 | Tag list not read; "latest" is what the README references |
| w3.org: WCAG 2.2, What's New | 8.1 | First part of the standard read directly |
| github.com/caddyserver/caddy/releases | CD-2 | CVE IDs for 2.11.1-2.11.6 came from a summary; not relied on |

### Read, secondary, weak

A Caddy community thread on `request_body`, search summaries on uvicorn limits.

### Cited from general knowledge [K], not re-read

OWASP ASVS 5.0, API Security Top 10 2023, Secure Headers, CSP, Logging, Secrets and XSS cheat sheets. NIST SP 800-34, 800-53, 800-57,
800-61r3, 800-190, 800-218, AI 600-1. CIS Benchmarks for Ubuntu 24.04, Docker and PostgreSQL. SLSA, OpenSSF Scorecard. RFC 9116. Mozilla
Web Security Guidelines. Simon Willison's "lethal trifecta". The Azure SLA figure. Library licences. Docker and UFW behaviour.

### Evidence gathered on 2026-11-05, and what was done to gather it

All read-only. Nothing changed in the repo (except this new file), database, VM, GitHub or Azure.

- **Live site:** HTTP headers, public paths, TLS versions, four TCP ports, Lighthouse. No `/chat` calls, so no quota used.
- **VM, over SSH:** OS and package state, `sshd -T`, `ufw status`, listening ports, `docker ps/inspect/stats/image ls`, `pip freeze` in
  the API container, Postgres settings and row counts. **`.env` values were not read:** only its permissions and variable names.
- **Azure and GitHub:** NSG rules, VM settings, backup vault and snapshot counts, budget; repo security settings; `npm audit`.
- **Local:** `pip-audit` on the deployed package list; hostile-Markdown render test; probes of the processed text, chunks and run 3 files.
- **Not done:** Trivy image scans, a new gitleaks scan, a CIS benchmark tool, any screen-reader session, any load test, testing on a real
  phone, adversarial tests against the live model.

**Probe limits:** the personal-data and instruction searches were short regular expressions, giving lower bounds. Block counts came from a
rough text split. The history search for alumni names checked one full name; the tracked-file search checked seven surnames.

---

## 12. What happens next

1. A2, one step at a time with tests, ending with run 4 against the threshold.
2. The data-protection review with AUI, before any student uses the service.

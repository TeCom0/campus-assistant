# Deploying the demo

One small Linux VM runs the same `docker-compose.yml` as development, plus the
production overrides in `docker-compose.prod.yml`: Caddy in front (automatic
HTTPS, the UI and the API on one origin with the API under `/api`), Postgres
and the API on the private Compose network only.

Commands below run from the repo root on your machine (PowerShell or Git Bash)
unless marked **on the VM**. Replace `<vm>` with `azureuser@<the VM's IP>` and
`<domain>` with the domain name.

## 1. The VM

- Ubuntu 24.04 LTS, **Standard_B2s** (2 vCPUs, 4 GiB RAM), 30 GiB Standard SSD.
  The API uses ~1.1 GiB once the embedding model is loaded; building its image
  (CPU torch) needs headroom, which 2 GiB doesn't leave.
- Login by SSH key only (no password).
- Inbound ports: 80 and 443 from anywhere; 22 from your own IP only.

On **Azure for Students** (found 2026-10-20):

- A fresh subscription has the Compute, Network and Storage resource providers
  unregistered, and `az vm list-skus` / `list-usage` then return misleading or
  empty results. Register them first (free, creates nothing):
  `az provider register -n Microsoft.Compute` (same for `Microsoft.Network`,
  `Microsoft.Storage`), and wait for `Registered`.
- A policy limits deployments to a few regions (`az policy assignment list`;
  on 2026-10-20: austriaeast, francecentral, polandcentral, denmarkeast,
  spaincentral), and a size can still be `NotAvailableForSubscription` inside
  them -- check with `az vm list-skus --location <region> --size Standard_B2s
  --all` (an empty `restrictions` list = usable). On 2026-10-20 B2s was usable
  only in **denmarkeast**.
- Pass `--subscription <id>` on every command if the account also has another
  (e.g. Pay-As-You-Go) subscription.
- Cost (Denmark East, 24/7): ~$37-45/month (VM ~$31-39, E4 disk $2.40, static
  IP $3.65). A monthly budget with email alerts guards the credit.

## 2. DNS

Without a custom domain yet, use Azure's free DNS label on the public IP
(`az vm create ... --public-ip-address-dns-name campus-assistant` gives
`campus-assistant.<region>.cloudapp.azure.com`); Caddy gets a Let's Encrypt
certificate for it like for any domain.

With a custom domain, at its DNS host (Namecheap: Domain List > Manage > Advanced DNS), add an
**A record** for the host you want (`@` for the bare domain, or e.g. `campus`)
pointing to the VM's public IP. Check it before step 5, because Caddy needs it
to get the certificate:

    nslookup <domain>

## 3. Docker on the VM

**On the VM:**

    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER   # then log out and back in
    docker compose version          # needs >= 2.24 (for !reset in the overrides)

## 4. The code and the secrets

The repo is private, so the VM gets a copy of one commit, not a clone with
credentials:

    git archive --format=tar HEAD | ssh <vm> "mkdir -p ~/campus && tar -x -C ~/campus"

The `.env` on the server is written there and never committed. **On the VM**,
create it with new database credentials and the app's settings:

    cd ~/campus
    umask 077
    cat > .env <<EOF
    POSTGRES_USER=campus_assistant
    POSTGRES_PASSWORD=$(openssl rand -hex 24)
    POSTGRES_DB=campus_assistant
    POSTGRES_PORT=5432
    CAMPUS_API_PASSWORD=$(openssl rand -hex 24)
    LLM_PROVIDER=groq
    DOMAIN=<domain>
    IP_HASH_SECRET=$(openssl rand -hex 32)
    EOF
    chmod 600 .env

Then add the Groq key from your machine without printing it (only that line is
copied; the Gemini and Mistral keys stay off the server):

    grep '^GROQ_API_KEY=' .env | ssh <vm> "cat >> ~/campus/.env"

## 5. The database

The server gets the loaded database as a dump (chunks with their embeddings,
courses, prerequisites), so nothing is re-chunked or re-embedded there.

On your machine:

    docker compose exec -T db sh -c 'pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -Fc -f /tmp/deploy.dump'
    docker compose cp db:/tmp/deploy.dump ./deploy.dump
    scp deploy.dump <vm>:~/campus/
    rm deploy.dump

**On the VM:**

    cd ~/campus
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d db
    docker compose cp deploy.dump db:/tmp/deploy.dump
    docker compose exec db sh -c 'pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --no-owner /tmp/deploy.dump'
    docker compose exec db sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB -At -c "select count(*) from document_chunks"'
    rm deploy.dump

The count should match your local database (1161 on 2026-10-19).

## 6. Start

**On the VM:**

    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f caddy   # watch the certificate arrive

Then check `https://<domain>/` (the UI), `https://<domain>/api/health`, and an
example question (it makes no API call). The smoke test (Ship plan step 6) asks
one English, one French, one prerequisite and one unanswerable question, on
desktop and phone.

## Updating

Copy the new commit as in step 4 (the `.env` and the database volume stay),
then run the `up -d --build` line again. Caddy keeps its certificates in the
`caddy_data` volume; don't delete it, or Let's Encrypt's rate limits apply.

If SSH times out, check whether your own public IP changed (home connections
often get a new one) and update the rule:

    az network nsg rule update -g campus-assistant-rg --nsg-name campus-nsg -n allow-ssh-from-me --source-address-prefixes <new IP>/32

## Post-deploy checklist: CSP enforced + A1.3

1. CSP check (`deploy/csp-check`) in Chrome, Firefox and Playwright's WebKit: zero violations on the
   paths in `CLAUDE.md` ("CSP enforcement rule") plus a source link, and the
   deliberate control still fires. Screenshots only in a separate pass after
   counting: in WebKit, `page.screenshot()` itself fires a violation, whatever
   its `caret` setting. Each browser spends one live question.
2. With curl: 413 for an oversized body, 422 for a 2,001-character question,
   422 for 21 messages. None of them counts toward the demo limits.
3. By hand on a real iPhone: the first screen, an example replay, a source link.
   Playwright's WebKit on Windows is not iOS Safari, and it doesn't display the
   PDF a source link opens. **Done:** Youness tested it with the CSP enforced.

## A1.4: the API's own database role (`campus_api`)

Written and agreed on 2026-11-05, before any of its code. `C` below stands for
`docker compose -f docker-compose.yml -f docker-compose.prod.yml`. Never `down`,
never `-v`, on this project: nothing here touches the volumes.

### Rule, fixed before the numbers

Before the API restarts, any failure means **stop**. The API hasn't been touched,
so there is nothing to roll back:

- the backup's checksum, row counts or test restore don't match;
- the retrieval eval, run **on the laptop** as `campus_api`, differs from
  `eval/results/retrieval/2026-11-05_a0_baseline.txt` (ranks identical expected);
- `migrate` or `verify_role` fails, or `question_log`'s count differs before and
  after `verify_role`.

After the API restarts, **roll back** on any one of these:

1. the live question isn't answered;
2. any permission error in the API log;
3. `question_log` doesn't go up by exactly 1.

The eval doesn't run on the VM: it would load a second copy of the embedding model
next to Postgres on 4 GB of RAM with no swap, which risks the OOM killer. Production's
content fingerprints matched the laptop's on 2026-11-05.

### Steps

1. **Backup.** Content only: `question_log` rows hold IP hashes the README promises
   to remove after about 2 days, and losing them only resets the limit counters.

       docker exec campus-db-1 sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --exclude-table-data=question_log -f /tmp/pre-a14.dump'
       docker cp campus-db-1:/tmp/pre-a14.dump ~/pre-a14.dump
       docker exec campus-db-1 rm /tmp/pre-a14.dump

   Copy it to the laptop, compare `sha256sum`, and restore it into a throwaway
   container to compare row counts. Delete `~/pre-a14.dump` on the VM only once
   A1.4 is accepted.
2. **Keep the running image, for the rollback:**

       docker tag campus-api:latest campus-api:pre-a14

3. **Copy the commit** as in step 4 above, then add the password on the VM. It's
   written only to `.env` and never printed. Don't run `docker compose config`,
   which prints values.

       cd ~/campus; umask 077
       grep -q '^CAMPUS_API_PASSWORD=' .env || printf 'CAMPUS_API_PASSWORD=%s\n' "$(openssl rand -hex 24)" >> .env

4. **Build, migrate, and pass the gate,** all with the old API still serving:

       $C build api migrate
       $C run --rm migrate
       $C run --rm --no-deps api python -m app.db.verify_role

   Count `question_log` before and after `verify_role`: the two must be equal.

   Run these by hand or from a file on the VM, with `-T` and `</dev/null` on
   `run`. Don't pipe a script through `ssh ... bash -s`: on 2026-11-05 the script
   stopped silently after the first `run`, exit 0, with the gate never run. So look
   for verify_role's `ok:` line, not the exit code. If this step has to be repeated,
   **don't repeat step 2**: `latest` is the new build by then, and tagging it again
   would overwrite the rollback image.
5. **Switch:** `$C up -d --no-deps api`. Nothing else restarts.
6. **Check the rule above:** `question_log` count, one live question, the count
   again, and the API log.

### Rollback

`<prev>` is the last commit before A1.4's code: `da982cf`.

    # Laptop
    git archive --format=tar <prev> | ssh <vm> "tar -x -C ~/campus"
    # VM
    cd ~/campus
    docker tag campus-api:pre-a14 campus-api:latest
    $C up -d --no-deps --no-build --force-recreate api
    docker exec campus-api-1 printenv POSTGRES_USER    # expect the owner's name

Rehearsed on 2026-11-05 on a scratch Compose project restored from the dump: 12 s
from the first command to `/health` on the laptop. Expect about 30 s on the VM, where
an API restart took 29 s, plus the copy. If the tag were lost, `$C build api` first.

The previous commit has no `campus_api` override, so its API reads the owner's
credentials from `.env` by itself. There is no `DATABASE_URL` variable to switch:
`app/config.py` builds it from the `POSTGRES_*` values. The database doesn't change
and `.env` keeps an unused variable.

**What stays behind:** the `campus_api` role, its grants, and the rights revoked
from `PUBLIC`. It's harmless: the database port isn't published in production, the
role is unused and can do only what it was granted, and the owner is a superuser,
so the revokes don't affect it. To remove it if A1.4 is abandoned:
`DROP OWNED BY campus_api; DROP ROLE campus_api;`

The dump is needed only if data were actually lost, and no A1.4 statement drops or
rewrites data.

## A1.5: off-VM backups (Backblaze B2)

Written and agreed on 2026-11-06, before any of its code. A systemd timer on the VM
host dumps the content tables daily, encrypts them with `age`, and pushes the result
to the bucket `campus-assistant-backups-7`. It isn't on Azure, because anything in
the same subscription dies with it. Scripts are in `deploy/backup/`.

**In a backup:** the content tables with their embeddings. **Not in it:** `question_log`
rows (losing them only resets the limit counters), `.env`, and Caddy's certificates.

### Where each secret lives

| Secret | Where | Who can read it |
| --- | --- | --- |
| `age` private key | `C:\dev\backup-keys\campus-backup.age-key` on the laptop, plus one offline copy in Youness's password manager. Never in the repo or on the VM | The VM can encrypt but never decrypt |
| `age` public key | `/etc/campus-backup/age-recipient.txt` on the VM | Not secret |
| B2 application key | `/etc/campus-backup/b2.env`, root-only, mode 600 | Never printed, never in a chat |
| Healthchecks.io ping URL | `/etc/campus-backup/healthcheck-url`, root-only, mode 600 | Never printed |
| B2 master key | Never on the VM. Used at most once on the laptop, see "If Write Only isn't enough" | Never on disk |

The password manager copy is deliberate: with the key only on the laptop, losing the
laptop would make every backup permanently unreadable.

### Why Object Lock is what matters

`writeFiles` also covers hiding files (`b2_hide_file` is on its list), and lifecycle
rules delete hidden files. So the key's missing `deleteFiles` is not what protects old
backups from a compromised VM. **Object Lock is:** a locked version can't be deleted
before its retention ends, whoever asks. Backblaze's lifecycle page: "if the file version
to which the rule applies has Object Lock enabled, then the deletion does not occur."
A version hidden early can still be downloaded by its file ID.

The lock lasts 30 days per version. It doesn't help if backups silently stop, because
lifecycle goes by age, not by count. That's why versions stay 45 days, not 31, and why
the dead man's switch exists.

### Rules, fixed before the numbers

- **A backup counts** only if the script reaches `BACKUP OK`, having checked that B2's
  reported size and SHA-1 match the local file, and that the retention B2 reports is
  `compliance` and at least 29 days ahead.
- **The key passes** only with `writeFiles`, `listBuckets`, `readFileRetentions` and
  `readBucketRetentions`, and without `deleteFiles`, `bypassGovernance` or
  `writeFileRetentions`, restricted to this bucket, with no name prefix or expiry. The
  bucket's default retention must read `compliance`, 30 days.
- **A restore drill passes** only if row counts and whole-row md5 fingerprints (embeddings
  included) are identical to production for `document_chunks`, `courses` and
  `course_prerequisites`, with 0 rows in `question_log`. Anything else fails.
- **Deletion must be refused twice:** with the VM's key (proves the key has no such right),
  and by hand in the console (proves the lock itself).

### 1. On the laptop: the key pair

`age` v1.3.2, `age-v1.3.2-windows-amd64.zip`, sha256
`f48d8f8f9ebe903ab5027ed067652f2cc1db94bc206976430133b905dcd8e8c7`.

Unzipped to `C:\dev\backup-tools\age\`, which holds no secret.

    New-Item -ItemType Directory -Force C:\dev\backup-keys
    C:\dev\backup-tools\age\age-keygen.exe -o C:\dev\backup-keys\campus-backup.age-key
    icacls C:\dev\backup-keys\campus-backup.age-key /inheritance:r /grant:r "${env:USERNAME}:R"

It prints the public key (`age1...`), which isn't secret. Copy the file's contents into
the password manager, and don't paste them anywhere else.

### 2. In the B2 console

**Lifecycle:** Buckets > `campus-assistant-backups-7` > Lifecycle Settings > Use custom
lifecycle rules. File Path `db/`, days from uploading to hiding `45`, days from hiding to
deleting `1`.

**Application key:** Application Keys > Add a New Application Key.

| Setting | Value |
| --- | --- |
| Name of Key | `campus-backup-vm` |
| Allow access to Bucket(s) | `campus-assistant-backups-7` only |
| Type of Access | Write Only |
| Allow List All Bucket Names | not ticked |
| File name prefix | empty |
| Duration | empty |

The secret is shown once. It goes only into `b2.env` below.

### 3. In Healthchecks.io

Create a check with a simple schedule, Period 1 day and Grace Time 26 hours. The ping
URL goes only into `healthcheck-url` below. Grace is added to the period, so this alerts
about 50 hours after the last good backup.

### 4. On the VM: tools and config

Pinned by exact version and checksum: `b2-linux` v5.0.2, sha256
`8210f07b8d12363ef747847c4fcb04c60550909238177a1e5112abe4f204ca45`, and
`age-v1.3.2-linux-amd64.tar.gz`, sha256
`cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10`.
`deploy/backup/install.sh` downloads and checks them, and installs the script and timer.

Fill in the secrets by hand. These commands create root-only files, and nothing here
prints them:

    sudo install -d -m 700 -o root -g root /etc/campus-backup
    sudo install -m 600 -o root -g root /dev/null /etc/campus-backup/b2.env
    sudo nano /etc/campus-backup/b2.env
    # B2_APPLICATION_KEY_ID=...
    # B2_APPLICATION_KEY=...
    sudo install -m 600 -o root -g root /dev/null /etc/campus-backup/healthcheck-url
    sudo nano /etc/campus-backup/healthcheck-url
    # https://hc-ping.com/...
    sudo install -m 644 -o root -g root /dev/null /etc/campus-backup/age-recipient.txt
    sudo nano /etc/campus-backup/age-recipient.txt
    # age1...

Never run `b2 account authorize` or `b2 account get`: measured on 2026-11-06, `authorize`
prints the key and writes it to `~/.b2_account_info`. With the key in environment
variables, other commands use in-memory account info and write nothing.

### 5. Check, then first backup

    sudo /usr/local/lib/campus-backup/b2_check.py        # capabilities, restriction, retention
    sudo /usr/local/sbin/campus-backup --check           # refuses if anything is missing
    sudo systemctl start campus-backup.service
    systemctl status campus-backup.service               # last result
    journalctl -u campus-backup.service -n 25            # the proof lines
    systemctl list-timers campus-backup.timer

### If Write Only isn't enough

Backblaze doesn't publish what the console's access types grant, so `b2_check.py`
measures it. If only `readFileRetentions` or `readBucketRetentions` is missing, delete
that key in the console and create one with exactly the rights needed, on the laptop,
in **your own PowerShell window, not through a tool that records output**. It prompts for
the master key so it never enters the shell history, which `$env:X = "..."` would.

`b2-windows.exe` v5.0.2, sha256
`d6e5b1c0918c2755fc8c14eb5b5aa698c36b43d3fdc18fca13ea163d829bbbbb`.

    $id = Read-Host 'Master key ID'
    $secure = Read-Host 'Master application key' -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    $env:B2_APPLICATION_KEY_ID = $id
    $env:B2_APPLICATION_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    try {
        .\b2-windows.exe key create --bucket campus-assistant-backups-7 campus-backup-vm listBuckets,writeFiles,readBucketRetentions,readFileRetentions
    } finally {
        Remove-Item Env:B2_APPLICATION_KEY, Env:B2_APPLICATION_KEY_ID -ErrorAction SilentlyContinue
        Remove-Variable id, secure, bstr -ErrorAction SilentlyContinue
    }
    Test-Path "$HOME\.b2_account_info"

It prints `<new key ID> <new key>`: copy both into `b2.env`, then `Clear-Host`. **Don't
run `b2 account authorize`.**

Measured on 2026-11-06 with this binary against a local fake server, using a marker as
the key: `key create` wrote no account file and left the marker nowhere in the home
folder, while `account authorize`, the control, wrote the file and printed the marker.
So `Test-Path` should say `False` if the file wasn't there before. If it says `True`
and you didn't have one, or you want it gone anyway:

    .\b2-windows.exe account clear
    Test-Path "$HOME\.b2_account_info"

### Restore drill, monthly

1. Download the latest `db/` object from the B2 console, and compare its sha256 with
   `journalctl -u campus-backup.service`.
2. `deploy/backup/restore-drill.sh <file>` decrypts it, restores it into a scratch project
   (`-p a15drill`), and compares it with production by the rule above.
3. In a real restore, use `pg_restore --no-owner --no-privileges` and then
   `python -m app.db.migrate`: dumps hold grants to `campus_api`, which a fresh database
   doesn't have yet.

Clean up with `docker compose -p a15drill -f deploy/backup/drill-compose.yml down -v`, and
only ever with that explicit project name.

## Deployed (2026-10-20)

Azure for Students, Denmark East, Standard_B2s, at
https://campus-assistant.denmarkeast.cloudapp.azure.com (resource group
`campus-assistant-rg`, VM `campus-vm`, NSG `campus-nsg`, SSH key
`~/.ssh/campus_azure`). Let's Encrypt certificate obtained in ~5 s; HTTP
redirects to HTTPS; only 80/443 reachable; the database dump was restored with
`question_log` data excluded (1161 chunks, 660 courses, 526 prerequisites). A
VM reboot brought the site back by itself in 40 s (`restart: unless-stopped`).

## Checked locally (2026-10-19)

The production stack ran on this machine with `DOMAIN=localhost` (Caddy's local
certificate) on ports 8081/8443: UI served, `/api/health` ok, source links
redirect to the PDF page, HSTS and nosniff headers set, the API and Postgres not
reachable from outside, and an answer streamed through Caddy (the first event
arrived 0.7 s before the last).

# Deploying the demo

One small Linux VM runs the same `docker-compose.yml` as development, plus the
production overrides in `docker-compose.prod.yml`: Caddy in front (automatic
HTTPS, the UI and the API on one origin with the API under `/api`), Postgres
and the API on the private Compose network only.

Commands below run from the repo root on your machine (PowerShell or Git Bash)
unless marked **on the VM**. Replace `<vm>` with `azureuser@<the VM's IP>` and
`<domain>` with the domain name.

## 1. The VM

- Ubuntu 24.04 LTS, **Standard_B2s** (2 vCPUs, 4 GiB RAM), 30 GiB disk. The API
  uses ~0.4 GiB idle and more once the embedding model is loaded; building its
  image (CPU torch) needs headroom, which 2 GiB doesn't leave.
- Login by SSH key only (no password).
- Inbound ports: 80 and 443 from anywhere; 22 from your own IP only.

## 2. DNS

At the domain's DNS host (Namecheap: Domain List > Manage > Advanced DNS), add an
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

## Checked locally (2026-10-19)

The production stack ran on this machine with `DOMAIN=localhost` (Caddy's local
certificate) on ports 8081/8443: UI served, `/api/health` ok, source links
redirect to the PDF page, HSTS and nosniff headers set, the API and Postgres not
reachable from outside, and an answer streamed through Caddy (the first event
arrived 0.7 s before the last).

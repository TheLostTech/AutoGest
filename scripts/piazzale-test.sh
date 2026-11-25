#!/bin/zsh
# Ambiente di prova per l'app Android in piazzale.
# - server sul Mac con dati suoi (.dati-test, separati da .demo-data), porta 3215
# - collegamento https (Cloudflare) per i telefoni, Mac tenuto sveglio finché è aperto
# - accesso unico: l'app entra da sola (porta /demo) come "Collaudo", con tutti i ruoli e tutti i moduli
# Si può lanciare più volte: riapre solo quello che manca. Alla fine stampa il QR da inquadrare con l'app.
# Uso:  zsh scripts/piazzale-test.sh            Ricompilare dopo modifiche al codice:  zsh scripts/piazzale-test.sh aggiorna
#       zsh scripts/piazzale-test.sh chiudi     (spegne server e collegamento; i dati restano in .dati-test)
cd "${0:A:h}/.." || exit 1
PORT=3215
DATI="$PWD/.dati-test"
LOG="$DATI/tunnel.log"
TUNNEL="cloudflared tunnel --no-autoupdate --url http://localhost:$PORT"
mkdir -p "$DATI"

server_pid() { lsof -nP -t -iTCP:$PORT -sTCP:LISTEN 2>/dev/null | head -1; }
ferma_server() {
  local p=$(server_pid)
  [[ -n "$p" ]] || return 0
  kill "$p"; for i in {1..15}; do [[ -z "$(server_pid)" ]] && return 0; sleep 1; done
  kill -9 "$(server_pid)" 2>/dev/null; sleep 1
}

if [[ "$1" == "chiudi" ]]; then
  ferma_server && echo "Server di prova spento."
  pkill -f "$TUNNEL" && echo "Collegamento https chiuso."
  exit 0
fi

# 1. Collegamento https. Se quello aperto non risponde, se ne apre uno nuovo (con un indirizzo nuovo:
#    nell'app si cambia inquadrando il QR qui sotto).
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" 2>/dev/null | tail -1)
if [[ -n "$URL" ]] && pgrep -f "$TUNNEL" >/dev/null && [[ -n "$(server_pid)" ]]; then
  echo "Controllo il collegamento $URL …"
  OK=""
  for i in {1..10}; do [[ "$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$URL/scopri")" == 200 ]] && OK=1 && break; sleep 3; done
  if [[ -z "$OK" ]]; then
    echo "Non risponde: lo riapro con un indirizzo nuovo."
    pkill -f "$TUNNEL"
    for i in {1..10}; do pgrep -f "$TUNNEL" >/dev/null || break; sleep 1; done
    pkill -9 -f "$TUNNEL" 2>/dev/null; sleep 1
  fi
fi
if ! pgrep -f "$TUNNEL" >/dev/null; then
  command -v cloudflared >/dev/null || { echo "Manca cloudflared: brew install cloudflared"; exit 1; }
  : > "$LOG"
  nohup ${=TUNNEL} > "$LOG" 2>&1 &
  for i in {1..40}; do grep -q "Registered tunnel connection" "$LOG" 2>/dev/null && break; sleep 1; done
fi
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" 2>/dev/null | tail -1)
[[ -n "$URL" ]] || { echo "Collegamento https non aperto: guarda $LOG"; exit 1; }

# 2. Server. Il login accetta solo l'indirizzo dato all'avvio: se il collegamento è cambiato, si riavvia.
if [[ "$1" == "aggiorna" || ! -f .next/BUILD_ID ]]; then
  ferma_server
  echo "Preparo il gestionale (1-2 minuti)…"
  npx next build > "$DATI/build.log" 2>&1 || { echo "Compilazione non riuscita: guarda $DATI/build.log"; exit 1; }
fi
if [[ -n "$(server_pid)" && "$(cat "$DATI/indirizzo" 2>/dev/null)" != "$URL" ]]; then
  echo "Indirizzo cambiato: riavvio il server."
  ferma_server
fi
if [[ -z "$(server_pid)" ]]; then
  echo "$URL" > "$DATI/indirizzo"
  DATI_DIR="$DATI" DEMO_PUBBLICA=1 DEMO_UTENTI=1 INDIRIZZO_GESTIONALE="$URL" PIAZZALE_SENZA_BOTID=1 \
    nohup npx next start -p $PORT > "$DATI/server.log" 2>&1 &
  for i in {1..60}; do curl -s -o /dev/null "http://localhost:$PORT/scopri" && break; sleep 1; done
fi
curl -s -o /dev/null "http://localhost:$PORT/scopri" || { echo "Il server non parte: guarda $DATI/server.log"; exit 1; }

# 3. Accesso unico con le credenziali massime: l'utente della porta /demo (la responsabile della demo)
#    diventa "Collaudo" con tutti e sei i ruoli. Si rifà a ogni avvio, senza effetti se già fatto.
PRONTO=""
for i in {1..30}; do
  node -e '
    const db = new (require("better-sqlite3"))(process.argv[1]);
    const u = db.prepare("select id from user where email = ?").get("sara@demo.autodemolizione.test");
    if (!u) process.exit(3);
    db.prepare("update member set role = ? where userId = ?").run("accettazione,smontatore,magazziniere,responsabile,vendite,consulente", u.id);
    db.prepare("update user set name = ? where id = ?").run("Collaudo", u.id);
  ' "$DATI/piattaforma.sqlite" 2>/dev/null && PRONTO=1 && break
  sleep 1
done
[[ -n "$PRONTO" ]] || { echo "Utente di collaudo non trovato: guarda $DATI/server.log"; exit 1; }

# 4. Mac sveglio finché il collegamento è aperto (con il coperchio chiuso va comunque in stop)
TPID=$(pgrep -f "$TUNNEL" | head -1)
if [[ -n "$TPID" ]] && ! pgrep -f "caffeinate -ims -w $TPID" >/dev/null; then
  nohup caffeinate -ims -w "$TPID" >/dev/null 2>&1 &
fi

echo ""
echo "Ambiente di prova aperto: $URL"
echo "Nell'app Piazzale: se non si apre da sola, tocca «Inquadra il QR» e inquadra questo:"
node -e 'require("qrcode").toString(process.argv[1], { type: "terminal", small: true }, (e, s) => console.log(s))' "$URL"
echo "Dal Mac: http://localhost:$PORT   ·   Dati: $DATI   ·   Per chiudere: zsh scripts/piazzale-test.sh chiudi"

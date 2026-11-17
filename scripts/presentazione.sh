#!/bin/zsh
# Apre il gestionale per una presentazione: server sul Mac, collegamento https (Cloudflare) per i telefoni,
# Mac tenuto sveglio finché il collegamento è aperto. Si può lanciare più volte: riapre solo quello che manca.
# Uso:  zsh scripts/presentazione.sh        Chiudere:  zsh scripts/presentazione.sh chiudi
cd "${0:A:h}/.." || exit 1
PORT=3211
LOG=.demo-data/tunnel.log
mkdir -p .demo-data

if [[ "$1" == "chiudi" ]]; then
  pkill -f "cloudflared tunnel --no-autoupdate --url http://localhost:$PORT" && echo "Collegamento https chiuso."
  exit 0
fi

# 1. Server del gestionale
if ! lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  [[ -f .next/BUILD_ID ]] || { echo "Preparo il gestionale (1-2 minuti)…"; npx next build >/dev/null || exit 1; }
  nohup npx next start -p $PORT > .demo-data/server.log 2>&1 &
  for i in {1..30}; do curl -s -o /dev/null "http://localhost:$PORT" && break; sleep 1; done
fi
curl -s -o /dev/null "http://localhost:$PORT" || { echo "Il server non parte: guarda .demo-data/server.log"; exit 1; }

# 2. Collegamento https. Dopo uno stop del Mac (coperchio chiuso) di solito si riaggancia da solo;
#    se dopo 30 secondi non risponde ancora, si chiude e se ne apre uno nuovo (con un indirizzo nuovo).
OLD=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' $LOG 2>/dev/null | tail -1)
if [[ -n "$OLD" ]] && pgrep -f "cloudflared tunnel --no-autoupdate --url http://localhost:$PORT" >/dev/null; then
  echo "Controllo il collegamento $OLD …"
  OK=""
  for i in {1..10}; do [[ "$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$OLD/api/indirizzo")" == 200 ]] && OK=1 && break; sleep 3; done
  if [[ -z "$OK" ]]; then
    echo "Non risponde: lo riapro con un indirizzo nuovo."
    pkill -f "cloudflared tunnel --no-autoupdate --url http://localhost:$PORT"
    # cloudflared si spegne con calma (fino a 30 secondi): si aspetta, poi si chiude d'autorità
    for i in {1..10}; do pgrep -f "cloudflared tunnel --no-autoupdate --url http://localhost:$PORT" >/dev/null || break; sleep 1; done
    pkill -9 -f "cloudflared tunnel --no-autoupdate --url http://localhost:$PORT" 2>/dev/null
    sleep 1
    : > $LOG
  fi
fi
if ! pgrep -f "cloudflared tunnel --no-autoupdate --url http://localhost:$PORT" >/dev/null; then
  command -v cloudflared >/dev/null || { echo "Manca cloudflared: brew install cloudflared"; exit 1; }
  nohup cloudflared tunnel --no-autoupdate --url "http://localhost:$PORT" > $LOG 2>&1 &
  for i in {1..40}; do grep -q "Registered tunnel connection" $LOG 2>/dev/null && break; sleep 1; done
fi
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' $LOG 2>/dev/null | tail -1)

# 3. Mac sveglio finché il collegamento è aperto (con il coperchio chiuso va comunque in stop)
TPID=$(pgrep -f "cloudflared tunnel --no-autoupdate --url http://localhost:$PORT" | head -1)
if [[ -n "$TPID" ]] && ! pgrep -f "caffeinate -ims -w $TPID" >/dev/null; then
  nohup caffeinate -ims -w "$TPID" >/dev/null 2>&1 &
fi

LAN=$(ipconfig getifaddr en0 2>/dev/null)
echo ""
echo "Gestionale aperto."
echo "  Dal telefono (con fotocamera):  ${URL:-indirizzo non trovato, guarda $LOG}"
echo "  Dal Mac:                        http://localhost:$PORT"
[[ -n "$LAN" ]] && echo "  Stessa rete, senza fotocamera:  http://$LAN:$PORT"
echo "Il primo accesso a un indirizzo nuovo può richiedere un minuto. Per chiudere: zsh scripts/presentazione.sh chiudi"

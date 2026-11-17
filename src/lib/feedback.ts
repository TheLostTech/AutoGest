// Riscontro di un'azione riuscita: vibrazione (Android) e bip (tutti, dopo il primo tocco sulla pagina).
// iPhone non vibra dal browser: lì contano il bip e il lampo sullo schermo.

let ctx: AudioContext | undefined;

// Da chiamare dentro un tocco (es. "Attiva fotocamera"): iPhone sblocca l'audio solo così
export function unlockAudio() {
  try {
    ctx ??= new AudioContext();
    if (ctx.state === "suspended") void ctx.resume();
  } catch {
    /* audio non disponibile */
  }
}

export function beep(tone: "ok" | "warn" = "ok") {
  if (!ctx || ctx.state !== "running") return;
  const t = ctx.currentTime;
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = "square";
  o.frequency.setValueAtTime(tone === "ok" ? 1760 : 440, t);
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(0.08, t + 0.008);
  g.gain.exponentialRampToValueAtTime(0.0001, t + (tone === "ok" ? 0.09 : 0.22));
  o.connect(g).connect(ctx.destination);
  o.start(t);
  o.stop(t + 0.25);
}

export function buzz(pattern: number | number[]) {
  try {
    // Prima del primo tocco sulla pagina il browser la blocca comunque (e scrive un errore)
    if (navigator.userActivation && !navigator.userActivation.hasBeenActive) return;
    navigator.vibrate?.(pattern);
  } catch {
    /* non supportato */
  }
}

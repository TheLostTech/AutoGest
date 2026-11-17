"use client";

import { useEffect } from "react";
import { buzz } from "@/lib/feedback";

const PRESSABLE = 'button:not(:disabled), a[href], [role="button"]:not([aria-disabled="true"]), summary, label:has(input[type="checkbox"], input[type="radio"], input[type="file"])';
const MIN_MS = 130;

// Ogni tocco su pulsanti e collegamenti si vede subito e resta visibile almeno un attimo,
// anche con un tocco rapido o col guanto (lo stile è in globals.css, [data-pressed]).
export function PressFeedback() {
  useEffect(() => {
    let el: HTMLElement | null = null;
    let since = 0;
    const timers = new WeakMap<HTMLElement, ReturnType<typeof setTimeout>>();

    const release = (now = false) => {
      const cur = el;
      if (!cur) return;
      el = null;
      const wait = now ? 0 : Math.max(0, MIN_MS - (performance.now() - since));
      timers.set(cur, setTimeout(() => cur.removeAttribute("data-pressed"), wait));
    };

    const down = (e: PointerEvent) => {
      if (e.button !== 0) return;
      const target = (e.target as Element | null)?.closest?.<HTMLElement>(PRESSABLE);
      if (!target) return;
      release(true);
      clearTimeout(timers.get(target));
      el = target;
      since = performance.now();
      target.setAttribute("data-pressed", "");
      if (e.pointerType === "touch") buzz(8);
    };
    const up = () => release();
    const cancel = () => release(true); // il dito ha iniziato a scorrere la pagina: niente pressione

    document.addEventListener("pointerdown", down, true);
    document.addEventListener("pointerup", up, true);
    document.addEventListener("pointercancel", cancel, true);
    // Senza un ascoltatore touchstart, Safari su iPhone non mostra lo stato :active
    const noop = () => {};
    document.addEventListener("touchstart", noop, { passive: true });
    return () => {
      document.removeEventListener("pointerdown", down, true);
      document.removeEventListener("pointerup", up, true);
      document.removeEventListener("pointercancel", cancel, true);
      document.removeEventListener("touchstart", noop);
    };
  }, []);
  return null;
}

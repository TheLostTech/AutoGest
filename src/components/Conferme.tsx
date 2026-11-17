"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { CircleCheck } from "lucide-react";
import { useStore } from "@/lib/store";
import type { AuditEvent } from "@/lib/types";
import { buzz } from "@/lib/feedback";

// Pagine che mostrano già il loro esito, grande e accanto all'azione: lì niente conferma a comparsa
const OWN_FEEDBACK = [/^\/scansione/, /^\/ricambi\/[^/]+$/, /^\/negozio/, /^\/(etichetta|etichette-scaffale|documento|certificato)\b/];

interface Toast {
  key: number;
  title: string;
  detail?: string;
  more: number;
}

// Conferma a comparsa di ogni azione registrata da questo dispositivo (creazione, invio, stampa, spostamento…).
// Si basa sul registro operazioni: ogni azione del gestionale ci scrive una riga.
export function Conferme() {
  const path = usePathname();
  const pathRef = useRef(path);
  useEffect(() => {
    pathRef.current = path;
  }, [path]);
  const [toast, setToast] = useState<Toast | null>(null);

  useEffect(() => {
    let n = 0;
    return useStore.subscribe((s, prev) => {
      const a = s.audit;
      const b = prev.audit;
      if (a === b || a.length <= b.length) return;
      // Righe arrivate da un altro dispositivo: l'elenco è sostituito, non allungato
      if (b.length && a[b.length - 1] !== b[b.length - 1]) return;
      if (OWN_FEEDBACK.some((r) => r.test(pathRef.current))) return;
      const nuovi: AuditEvent[] = a.slice(b.length);
      const first = nuovi[0];
      setToast({
        key: ++n,
        title: first.action,
        detail: [first.entityId, first.detail].filter(Boolean).join(" · "),
        more: nuovi.length - 1,
      });
      buzz(20);
    });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3200);
    return () => clearTimeout(t);
  }, [toast]);

  return (
    <div
      className="no-print pointer-events-none fixed inset-x-0 z-50 flex justify-center px-4 bottom-[calc(env(safe-area-inset-bottom)+76px)] md:inset-x-auto md:bottom-6 md:right-6 md:justify-end"
      role="status"
      aria-live="polite"
    >
      {toast && (
        <div key={toast.key} className="toast-in pointer-events-auto flex max-w-md items-start gap-3 rounded-md bg-ink px-4 py-3 text-white shadow-[0_12px_32px_-12px_rgb(17_20_24/0.6)]">
          <CircleCheck className="mt-0.5 size-5 shrink-0 text-[#5fd38a]" aria-hidden />
          <div className="min-w-0">
            <p className="text-[15px] font-semibold leading-snug">{toast.title}</p>
            {(toast.detail || toast.more > 0) && (
              <p className="mt-0.5 line-clamp-2 text-[13px] text-white/75">
                {toast.detail}
                {toast.more > 0 && ` · e altre ${toast.more} ${toast.more === 1 ? "operazione" : "operazioni"}`}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

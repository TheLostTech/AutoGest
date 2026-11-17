import { PRODUTTORE } from "@/lib/config";

// Marchio Lostar: due barre nel colore del testo e una gialla
export function LostarMark({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 26 32" className={className} aria-hidden>
      <rect x="0" y="0" width="6" height="32" fill="currentColor" />
      <rect x="10" y="0" width="6" height="32" fill="currentColor" />
      <rect x="20" y="0" width="6" height="32" fill="#F4B500" />
    </svg>
  );
}

export function LostarCredit({ className = "" }: { className?: string }) {
  return (
    <a
      href={PRODUTTORE.sito}
      target="_blank"
      rel="noopener"
      className={`inline-flex items-center gap-2 text-[12px] font-semibold uppercase tracking-[0.12em] code ${className}`}
    >
      <LostarMark className="h-3.5 w-3" />
      <span>
        <span className="font-medium normal-case tracking-normal opacity-80">by </span>
        {PRODUTTORE.nome}
      </span>
    </a>
  );
}

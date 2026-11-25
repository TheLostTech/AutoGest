"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Search, X } from "lucide-react";
import { TYPE_GROUPS, miniRender, typeById } from "@/lib/catalog";
import { cercaCategorie, cercaTipologie } from "@/lib/cerca";

// Le tipologie sono quasi 250: al posto della tendina, una finestra con la ricerca in cima.
// Valori: "" nessuna, l'id di una tipologia, oppure "cat:<Categoria>" quando `categorie` è attivo (filtro del magazzino).
const CATEGORIE = TYPE_GROUPS.map(([c]) => c);

interface Voce {
  value: string;
  titolo: string;
  sub?: string;
  img?: string;
  gruppo?: string; // intestazione sopra la voce
}

export function TypePicker({
  value,
  onChange,
  vuoto = "Scegli…",
  categorie = false,
  conteggi,
  className = "",
  label = "Tipologia",
}: {
  value: string;
  onChange: (value: string) => void;
  vuoto?: string; // testo per "nessuna scelta"; nel filtro è "Tutte le tipologie" e si può sceglierlo
  categorie?: boolean;
  conteggi?: Map<string, number>; // pezzi per tipologia e per "cat:…", mostrati accanto
  className?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  const scelta = value.startsWith("cat:")
    ? `Tutto ${value.slice(4)}`
    : value
      ? typeById(value).name
      : "";

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`field flex items-center justify-between gap-2 text-left ${className}`}
        aria-haspopup="dialog"
        aria-label={`${label}: ${scelta || vuoto}`}
      >
        <span className={`truncate ${scelta ? "" : "text-ink-3"}`}>
          {scelta || vuoto}
        </span>
        <ChevronDown className="size-5 shrink-0 text-ink-3" aria-hidden />
      </button>
      {/* Fuori dal <label> di Field: un clic sullo sfondo altrimenti riaprirebbe la finestra appena chiusa */}
      {/* Si crea solo da aperta: l'apertura avviene sempre nel browser, mai durante il rendering sul server */}
      {open &&
        createPortal(
          <dialog
            ref={ref}
            onClose={() => setOpen(false)}
            onClick={(e) => e.target === e.currentTarget && setOpen(false)}
            aria-label={label}
            className="m-0 mx-auto mt-0 h-dvh max-h-dvh w-full max-w-full bg-transparent p-0 backdrop:bg-ink/50 md:mt-[10vh] md:h-auto md:max-h-[80vh] md:max-w-[560px]"
          >
            <Elenco
              value={value}
              vuoto={vuoto}
              categorie={categorie}
              conteggi={conteggi}
              label={label}
              onClose={() => setOpen(false)}
              onPick={(v) => {
                onChange(v);
                setOpen(false);
              }}
            />
          </dialog>,
          document.body,
        )}
    </>
  );
}

function Elenco({
  value,
  vuoto,
  categorie,
  conteggi,
  label,
  onClose,
  onPick,
}: {
  value: string;
  vuoto: string;
  categorie: boolean;
  conteggi?: Map<string, number>;
  label: string;
  onClose: () => void;
  onPick: (v: string) => void;
}) {
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const lista = useRef<HTMLUListElement>(null);
  const conta = (k: string) =>
    conteggi ? ` · ${conteggi.get(k) ?? 0} in magazzino` : "";
  const img = (src?: string) => (src ? miniRender(src) : undefined);

  const voci: Voce[] = [];
  if (q.trim()) {
    if (categorie)
      for (const c of cercaCategorie(q, CATEGORIE))
        voci.push({
          value: `cat:${c}`,
          titolo: `Tutto ${c}`,
          sub: `Categoria${conta(`cat:${c}`)}`,
          gruppo: "Categorie",
        });
    cercaTipologie(q).forEach((t, i) =>
      voci.push({
        value: t.id,
        titolo: t.name,
        sub: `${t.category}${conta(t.id)}`,
        img: img(t.render),
        gruppo: i === 0 ? "Tipologie" : undefined,
      }),
    );
  } else {
    if (categorie) voci.push({ value: "", titolo: vuoto });
    for (const [c, tipi] of TYPE_GROUPS) {
      if (categorie)
        voci.push({
          value: `cat:${c}`,
          titolo: `Tutto ${c}`,
          sub: conta(`cat:${c}`).replace(" · ", ""),
          gruppo: c,
        });
      tipi.forEach((t, i) =>
        voci.push({
          value: t.id,
          titolo: t.name,
          sub: conteggi ? conta(t.id).replace(" · ", "") : undefined,
          img: img(t.render),
          gruppo: !categorie && i === 0 ? c : undefined,
        }),
      );
    }
  }
  const cur = Math.min(sel, Math.max(0, voci.length - 1));

  // La voce evidenziata con le frecce resta visibile
  useEffect(() => {
    lista.current
      ?.querySelector<HTMLElement>(`[data-i="${cur}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [cur]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-label shadow-[0_30px_80px_-24px_rgb(17_20_24/0.55)] md:h-auto md:max-h-[80vh] md:rounded-md">
      <div className="flex items-center gap-3 border-b-2 border-band px-4">
        <Search
          className="size-6 shrink-0 text-band"
          strokeWidth={2.2}
          aria-hidden
        />
        <input
          autoFocus
          className="h-16 min-w-0 flex-1 bg-transparent text-[20px] font-medium text-ink placeholder:font-normal placeholder:text-ink-3 focus-visible:outline-none"
          placeholder="Cerca: bobina, freni, faro…"
          value={q}
          enterKeyHint="done"
          onChange={(e) => {
            setQ(e.target.value);
            setSel(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setSel(Math.min(cur + 1, voci.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setSel(Math.max(cur - 1, 0));
            } else if (e.key === "Enter" && voci[cur]) {
              e.preventDefault();
              onPick(voci[cur].value);
            }
          }}
          aria-label={`Cerca ${label.toLowerCase()}`}
        />
        {q && (
          <button
            type="button"
            onClick={() => setQ("")}
            className="code shrink-0 rounded px-2 py-1 text-[13px] font-semibold uppercase tracking-wide text-ink-3 hover:text-ink"
          >
            Svuota
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          className="grid size-10 shrink-0 place-items-center rounded-full text-ink-3 hover:bg-carton hover:text-ink"
          aria-label="Chiudi"
        >
          <X className="size-5" aria-hidden />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {voci.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="font-semibold">Nessuna tipologia per «{q}»</p>
            <p className="mt-1 text-sm text-ink-2">
              Prova con una parola sola, per esempio «faro» o «motore».
            </p>
          </div>
        ) : (
          <ul ref={lista} className="py-1.5" role="listbox" aria-label={label}>
            {voci.map((v, i) => {
              const on = i === cur;
              const scelto = v.value === value;
              return (
                <li
                  key={`${v.value}|${i}`}
                  role="option"
                  aria-selected={scelto}
                >
                  {v.gruppo && (
                    <p className="code px-4 pb-1 pt-3 text-[13px] font-bold uppercase tracking-wide text-ink-3">
                      {v.gruppo}
                    </p>
                  )}
                  <button
                    type="button"
                    data-i={i}
                    onClick={() => onPick(v.value)}
                    onMouseEnter={() => setSel(i)}
                    className={`flex min-h-12 w-full items-center gap-3 border-l-4 px-3 py-1.5 text-left ${on ? "border-band bg-band-tint" : "border-transparent"}`}
                  >
                    {v.img ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={v.img}
                        alt=""
                        loading="lazy"
                        className="size-9 shrink-0 rounded bg-carton object-contain"
                      />
                    ) : (
                      <span className="size-9 shrink-0" aria-hidden />
                    )}
                    <span className="min-w-0 flex-1">
                      <span
                        className={`block truncate ${v.value.startsWith("cat:") || !v.value ? "font-bold" : "font-semibold"}`}
                      >
                        {v.titolo}
                      </span>
                      {v.sub && (
                        <span className="block truncate text-sm text-ink-2">
                          {v.sub}
                        </span>
                      )}
                    </span>
                    {scelto && (
                      <span className="code shrink-0 text-[12px] font-semibold uppercase tracking-wide text-band">
                        Scelta
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

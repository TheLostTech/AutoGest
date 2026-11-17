"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ExternalLink, FileKey, Loader2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { ACCESSO, completo, MODO, SERVIZI, type Campo, type Servizio, type StatoServizio } from "@/lib/collegamenti";
import { Button, Notice, PageTitle, Panel } from "@/components/ui";

type Stati = Record<string, StatoServizio>;

const GRUPPI: { id: Servizio["gruppo"]; titolo: string; sub: string }[] = [
  { id: "legge", titolo: "Obbligatori per legge", sub: "Si pagano comunque, con o senza gestionale. Per entrare serve lo SPID del titolare." },
  { id: "consumo", titolo: "A consumo, con registrazione normale", sub: "Account con email e partita IVA: si paga quello che si usa." },
];

export default function Collegamenti() {
  const role = useStore((s) => s.role);
  const [stati, setStati] = useState<Stati | null>(null);
  const [errore, setErrore] = useState("");
  const [aperto, setAperto] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/collegamenti", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error())))
      .then((d: Stati) => setStati(d))
      .catch(() => setErrore("Non riesco a leggere i collegamenti dal server dell'azienda."));
  }, []);

  if (role !== "responsabile") {
    return (
      <div className="mx-auto max-w-4xl">
        <PageTitle title="Collegamenti" />
        <Notice tone="warn">Le credenziali dei servizi esterni le gestisce solo il responsabile.</Notice>
      </div>
    );
  }

  const conDati = SERVIZI.filter((s) => s.campi.length);
  const pronti = stati ? conDati.filter((s) => completo(s, stati[s.id])).length : 0;

  return (
    <div className="mx-auto max-w-4xl">
      <PageTitle
        title="Collegamenti"
        sub="Inserisci credenziali e chiavi dei servizi esterni. Restano cifrate sul server dell'azienda: dopo il salvataggio password e chiavi non si rivedono, si possono solo sostituire."
      />
      <div className="mb-6 space-y-3">
        <Notice tone="info">
          <b>Prototipo:</b> i dati si salvano ma nessun collegamento è ancora attivo. Visura, RVFU, RENTRI e gli altri servizi restano simulati finché non li integriamo uno per uno.
        </Notice>
        {stati && (
          <p className="code text-[13px] font-semibold uppercase tracking-[0.12em] text-ink-3">
            {pronti} di {conDati.length} servizi con i dati completi
          </p>
        )}
      </div>

      {errore && <Notice tone="danger">{errore}</Notice>}
      {!stati && !errore && (
        <p className="flex items-center gap-2 text-ink-2">
          <Loader2 className="size-5 animate-spin" aria-hidden /> Carico i collegamenti…
        </p>
      )}

      {stati &&
        GRUPPI.map((g) => (
          <section key={g.id} className="mb-8">
            <h2 className="text-[20px] font-bold text-ink">{g.titolo}</h2>
            <p className="mb-3 text-[15px] text-ink-2">{g.sub}</p>
            <Panel>
              <ul className="divide-y divide-hair-soft">
                {SERVIZI.filter((s) => s.gruppo === g.id).map((s) => (
                  <ServizioRiga
                    key={s.id}
                    s={s}
                    st={stati[s.id]}
                    open={aperto === s.id}
                    onToggle={() => setAperto(aperto === s.id ? null : s.id)}
                    onSaved={(st) => setStati((cur) => {
                      const next = { ...cur };
                      if (st) next[s.id] = st;
                      else delete next[s.id];
                      return next;
                    })}
                  />
                ))}
              </ul>
            </Panel>
          </section>
        ))}

      <p className="max-w-[70ch] text-[13px] text-ink-3">
        Lo SPID non si salva: è personale e ogni accesso lo fa il titolare. PIN e codici OTP della firma digitale si inseriscono a ogni firma. Costi e fonti in docs/INTEGRAZIONI.md.
      </p>
    </div>
  );
}

function Stato({ s, st }: { s: Servizio; st?: StatoServizio }) {
  const [txt, cls] = !s.campi.length
    ? ["Solo dal portale", "bg-hair-soft text-ink-2"]
    : completo(s, st)
      ? ["Dati completi", "bg-ok-bg text-ok"]
      : st
        ? ["Da completare", "bg-warn-bg text-warn"]
        : ["Da configurare", "border border-dashed border-hair text-ink-2"];
  return <span className={`inline-flex h-7 shrink-0 items-center rounded-full px-2.5 text-[13px] font-semibold ${cls}`}>{txt}</span>;
}

function ServizioRiga({ s, st, open, onToggle, onSaved }: { s: Servizio; st?: StatoServizio; open: boolean; onToggle: () => void; onSaved: (st: StatoServizio | null) => void }) {
  return (
    <li>
      <button onClick={onToggle} aria-expanded={open} className="flex w-full items-start gap-3 px-4 py-3.5 text-left hover:bg-carton/60">
        <span className="min-w-0 flex-1">
          <span className="block font-semibold text-ink">{s.nome}</span>
          <span className="block text-[14px] text-ink-2">{s.uso}</span>
          <span className="mt-1.5 flex flex-wrap gap-1.5 text-[12px] font-semibold">
            <span className="rounded bg-band-tint px-2 py-0.5 text-band-deep">{ACCESSO[s.accesso].label}</span>
            <span className="rounded bg-carton px-2 py-0.5 text-ink-2">{MODO[s.modo]}</span>
          </span>
        </span>
        <Stato s={s} st={st} />
        <ChevronDown className={`mt-1 size-5 shrink-0 text-ink-3 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden />
      </button>
      {open && (
        <div className="space-y-4 border-t border-hair-soft bg-carton/40 px-4 py-4">
          <dl className="grid gap-x-4 gap-y-1 text-[14px] sm:grid-cols-[110px_1fr]">
            <dt className="font-semibold text-ink-3">Costo</dt>
            <dd className="text-ink">{s.costo}</dd>
            <dt className="font-semibold text-ink-3">Accesso</dt>
            <dd className="text-ink">{ACCESSO[s.accesso].spiega}</dd>
          </dl>
          <p className="max-w-[70ch] text-[14px] text-ink-2">{s.nota}</p>
          {s.link && (
            <a href={s.link.href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-band underline-offset-2 hover:underline">
              {s.link.label} <ExternalLink className="size-4" aria-hidden />
            </a>
          )}
          {s.campi.length > 0 ? (
            <Modulo key={st?.aggiornato ?? "nuovo"} s={s} st={st} onSaved={onSaved} />
          ) : (
            <p className="text-[14px] font-semibold text-ink-2">Niente da salvare qui: si usa dal portale.</p>
          )}
        </div>
      )}
    </li>
  );
}

const toBase64 = async (f: File) => {
  const b = new Uint8Array(await f.arrayBuffer());
  let s = "";
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode(...b.subarray(i, i + 0x8000));
  return btoa(s);
};

function Modulo({ s, st, onSaved }: { s: Servizio; st?: StatoServizio; onSaved: (st: StatoServizio | null) => void }) {
  const [valori, setValori] = useState<Record<string, string | string[]>>(st?.valori ?? {});
  const [segreti, setSegreti] = useState<Record<string, string>>({});
  const [file, setFile] = useState<Record<string, { nome: string; dati: string }>>({});
  const [togli, setTogli] = useState<string[]>([]);
  const [msg, setMsg] = useState<{ tone: "ok" | "danger"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const salva = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const r = await fetch("/api/collegamenti", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: s.id, valori, segreti, file, togli }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error);
      onSaved(d as StatoServizio);
    } catch (e) {
      setMsg({ tone: "danger", text: e instanceof Error && e.message ? e.message : "Salvataggio non riuscito." });
      setBusy(false);
    }
  };

  const scollega = async () => {
    if (!confirm(`Cancellare tutti i dati salvati di ${s.nome}?`)) return;
    setBusy(true);
    const r = await fetch(`/api/collegamenti?id=${encodeURIComponent(s.id)}`, { method: "DELETE" });
    if (r.ok) onSaved(null);
    else {
      setMsg({ tone: "danger", text: "Non riesco a cancellare i dati." });
      setBusy(false);
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void salva();
      }}
      className="space-y-4"
    >
      {st?.aggiornato && <Notice tone="ok">Salvato il {new Date(st.aggiornato).toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" })}.</Notice>}
      <div className="grid gap-4 sm:grid-cols-2">
        {s.campi.map((c) => (
          <CampoInput
            key={c.key}
            c={c}
            valore={valori[c.key]}
            salvato={c.tipo === "segreto" ? !!st?.segreti[c.key] && !togli.includes(c.key) : undefined}
            fileSalvato={c.tipo === "file" && !togli.includes(c.key) ? st?.file[c.key] : undefined}
            nuovoFile={file[c.key]?.nome}
            segreto={segreti[c.key] ?? ""}
            onValore={(v) => setValori((x) => ({ ...x, [c.key]: v }))}
            onSegreto={(v) => setSegreti((x) => ({ ...x, [c.key]: v }))}
            onFile={async (f) => {
              setMsg(null);
              if (f.size > 64 * 1024) return setMsg({ tone: "danger", text: "Il file è troppo grande: un certificato pesa pochi KB." });
              const dati = await toBase64(f);
              setFile((x) => ({ ...x, [c.key]: { nome: f.name, dati } }));
              setTogli((t) => t.filter((k) => k !== c.key));
            }}
            onTogli={() => {
              setTogli((t) => [...t, c.key]);
              setSegreti((x) => ({ ...x, [c.key]: "" }));
              setFile((x) => {
                const rest = { ...x };
                delete rest[c.key];
                return rest;
              });
            }}
          />
        ))}
      </div>
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" disabled={busy}>
          {busy ? <Loader2 className="size-5 animate-spin" aria-hidden /> : null} Salva
        </Button>
        {st && (
          <Button type="button" variant="danger" disabled={busy} onClick={() => void scollega()}>
            Cancella i dati
          </Button>
        )}
      </div>
    </form>
  );
}

function CampoInput(p: {
  c: Campo;
  valore?: string | string[];
  salvato?: boolean;
  fileSalvato?: { nome: string; byte: number };
  nuovoFile?: string;
  segreto: string;
  onValore: (v: string | string[]) => void;
  onSegreto: (v: string) => void;
  onFile: (f: File) => void;
  onTogli: () => void;
}) {
  const { c } = p;
  const id = `campo-${c.key}`;
  const label = (
    <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-ink">
      {c.label}
      {c.facoltativo && <span className="font-normal text-ink-3"> · facoltativo</span>}
    </label>
  );
  const hint = c.hint && <span className="mt-1 block text-sm text-ink-3">{c.hint}</span>;

  if (c.tipo === "multipla") {
    const sel = Array.isArray(p.valore) ? p.valore : [];
    return (
      <fieldset className="sm:col-span-2">
        <legend className="mb-1.5 text-sm font-semibold text-ink">{c.label}</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          {c.opzioni!.map((o) => (
            <label key={o} className="flex min-h-11 items-center gap-3 rounded-md border border-hair bg-label px-3">
              <input
                type="checkbox"
                className="size-5 accent-[var(--band)]"
                checked={sel.includes(o)}
                onChange={(e) => p.onValore(e.target.checked ? [...sel, o] : sel.filter((x) => x !== o))}
              />
              <span className="text-[15px]">{o}</span>
            </label>
          ))}
        </div>
      </fieldset>
    );
  }

  if (c.tipo === "scelta") {
    return (
      <div>
        {label}
        <select id={id} className="field" value={typeof p.valore === "string" ? p.valore : ""} onChange={(e) => p.onValore(e.target.value)}>
          <option value="">Scegli…</option>
          {c.opzioni!.map((o) => (
            <option key={o}>{o}</option>
          ))}
        </select>
        {hint}
      </div>
    );
  }

  if (c.tipo === "segreto") {
    return (
      <div>
        {label}
        <input
          id={id}
          type="password"
          autoComplete="new-password"
          className="field"
          value={p.segreto}
          placeholder={p.salvato ? "•••••••• salvata" : ""}
          onChange={(e) => p.onSegreto(e.target.value)}
        />
        {p.salvato ? (
          <span className="mt-1 flex items-center gap-2 text-sm text-ink-3">
            Salvata. Scrivi solo per sostituirla.
            <button type="button" onClick={p.onTogli} className="font-semibold text-danger underline">Togli</button>
          </span>
        ) : (
          hint
        )}
      </div>
    );
  }

  if (c.tipo === "file") {
    const nome = p.nuovoFile ?? p.fileSalvato?.nome;
    return (
      <div>
        {label}
        <input
          id={id}
          type="file"
          accept={c.accept}
          className="field py-2 file:mr-3 file:rounded file:border-0 file:bg-band-tint file:px-3 file:py-1 file:font-semibold file:text-band-deep"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) p.onFile(f);
          }}
        />
        {nome ? (
          <span className="mt-1 flex items-center gap-2 text-sm text-ink-2">
            <FileKey className="size-4" aria-hidden /> {nome} {p.nuovoFile ? "(da salvare)" : `· ${Math.ceil((p.fileSalvato?.byte ?? 0) / 1024)} KB, salvato`}
            {!p.nuovoFile && <button type="button" onClick={p.onTogli} className="font-semibold text-danger underline">Togli</button>}
          </span>
        ) : (
          hint
        )}
      </div>
    );
  }

  return (
    <div>
      {label}
      <input id={id} className="field" value={typeof p.valore === "string" ? p.valore : ""} placeholder={c.placeholder} onChange={(e) => p.onValore(e.target.value)} autoComplete="off" />
      {hint}
    </div>
  );
}

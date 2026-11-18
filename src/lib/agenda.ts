import { locToString } from "./warehouse";
import { bonificaStato, isDraft, MISSING_TEXT, missingFields, periodKeyOf, periodsOf, workingDaysAfter, type BonificaStato } from "./periodo";
// Coda "Da fare": le attività nascono dai dati, non da una lista compilata a mano.
// Ogni voce ha un ruolo destinatario, una scadenza (se esiste) e porta all'azione.
import { typeById } from "./catalog";
import { eerByCode, fmtKg, stockByEer } from "./ambiente";
import { identOk } from "./pratica";
import type { Fir, Order, Part, Role, SalesDoc, StockRule, Vehicle, WasteMove } from "./types";

export type Urgency = "scaduto" | "oggi" | "settimana" | "quando-puoi";

export interface AgendaItem {
  id: string;
  title: string;
  detail: string;
  action: string; // verbo del pulsante
  href: string;
  due?: string; // ISO
  roles: Role[];
  kind: "veicolo" | "pratica" | "ricambi" | "ordine" | "scorte" | "ambiente";
}

// Termini dimostrativi, da configurare per impianto e da validare con il consulente.
export const TERMS = {
  verificaIdentita: 1, // giorni dall'ingresso
  registraPratica: 2,
  radiazione: 30,
  bozza: 2,
  posizione: 1,
  pagamento: 2, // dopo questo termine la riserva va rivista
  spedizione: 1,
  preventivo: 5, // giorni dopo i quali richiamare il cliente
};

const DAY = 864e5;
const addDays = (iso: string, d: number) => new Date(new Date(iso).getTime() + d * DAY).toISOString();
const oldest = (xs: { createdAt: string }[]) => xs.map((x) => x.createdAt).sort()[0];

export function urgencyOf(due: string | undefined, now = new Date()): Urgency {
  if (!due) return "quando-puoi";
  const d = new Date(due);
  const endOfToday = new Date(now);
  endOfToday.setHours(23, 59, 59, 999);
  const startOfToday = new Date(now);
  startOfToday.setHours(0, 0, 0, 0);
  if (d < startOfToday) return "scaduto";
  if (d <= endOfToday) return "oggi";
  if (d.getTime() - endOfToday.getTime() <= 7 * DAY) return "settimana";
  return "quando-puoi";
}

// Tempo di stazionamento prima della bonifica: obiettivo interno 7 giorni, legge 10 giorni lavorativi (vedi periodo.ts)
export type BonificaClock = BonificaStato;
export const bonificaClock = (v: Vehicle, now = new Date()): BonificaClock | null => (v.bonifica ? null : bonificaStato(v.intakeAt, now));

export function buildAgenda(
  {
    vehicles,
    parts,
    orders,
    rules,
    activeVehicleId,
    wasteMoves = [],
    firs = [],
    docs = [],
  }: { vehicles: Vehicle[]; parts: Part[]; orders: Order[]; rules: StockRule[]; activeVehicleId?: string; wasteMoves?: WasteMove[]; firs?: Fir[]; docs?: SalesDoc[] },
  role: Role,
): AgendaItem[] {
  const items: AgendaItem[] = [];
  const name = (v: Vehicle) => `${v.make} ${v.model} · ${v.plate}`;

  // Veicoli e pratiche
  for (const v of vehicles) {
    if (v.verification === "da verificare")
      items.push({
        id: `verifica-${v.id}`,
        kind: "veicolo",
        title: `Verifica identificazione ${v.id}`,
        detail: `${name(v)}${v.notes ? ` · ${v.notes}` : ""}`,
        action: "Verifica",
        href: `/veicoli/${v.id}`,
        due: addDays(v.intakeAt, TERMS.verificaIdentita),
        roles: ["accettazione", "responsabile"],
      });
    if (v.visura?.fermo && !v.presaInCarico && !v.documenti?.includes("inutilizzabilita"))
      items.push({
        id: `fermo-${v.id}`,
        kind: "pratica",
        title: `Fermo amministrativo su ${v.id}: serve l'attestazione di inutilizzabilità`,
        detail: `${name(v)} · senza attestazione la presa in carico resta ferma`,
        action: "Apri pratica",
        href: `/veicoli/${v.id}#pratica`,
        due: v.visura.at,
        roles: ["accettazione", "responsabile"],
      });
    else if (!v.presaInCarico)
      items.push({
        id: `pratica-${v.id}`,
        kind: "pratica",
        title: `Completa la presa in carico di ${v.id}`,
        detail: `${name(v)} · ${!v.conferente ? "chi consegna e documenti da registrare" : !v.visura ? "visura PRA da fare" : !identOk(v) ? "manca il telaio verificato" : "CRD da generare"}`,
        action: "Apri pratica",
        href: `/veicoli/${v.id}#pratica`,
        due: addDays(v.intakeAt, TERMS.registraPratica),
        roles: ["accettazione", "responsabile"],
      });
    else if (v.radiazione?.stato !== "completata")
      items.push({
        id: `radiazione-${v.id}`,
        kind: "pratica",
        title: v.radiazione?.stato === "richiesta" ? `Registra l'esito della radiazione di ${v.id}` : `Richiedi la radiazione di ${v.id}`,
        detail: `${name(v)} · pratica ${v.dossier.number}`,
        action: "Apri pratica",
        href: `/veicoli/${v.id}#pratica`,
        due: addDays(v.presaInCarico?.at ?? v.intakeAt, TERMS.radiazione),
        roles: ["accettazione", "responsabile"],
      });
    const clock = bonificaClock(v);
    if (clock)
      items.push({
        id: `bonifica-${v.id}`,
        kind: "ambiente",
        title: `${clock.label} · ${v.id}`,
        detail: `${name(v)} · ${clock.parked} · liquidi, batteria, airbag, catalizzatore, pneumatici`,
        action: "Bonifica",
        href: `/veicoli/${v.id}/bonifica`,
        due: clock.due,
        roles: ["smontatore", "accettazione", "responsabile"],
      });
    if (v.work === "accettato" && v.bonifica)
      items.push({
        id: `smonta-${v.id}`,
        kind: "veicolo",
        title: `Avvia lo smontaggio di ${v.id}`,
        detail: `${name(v)} · in piazzale dal ${new Date(v.intakeAt).toLocaleDateString("it-IT", { day: "numeric", month: "short" })}`,
        action: "Avvia",
        href: `/campo/${v.id}`,
        roles: ["smontatore", "responsabile"],
      });
    if (v.work === "in smontaggio")
      items.push({
        id: `riprendi-${v.id}`,
        kind: "veicolo",
        title: `Riprendi lo smontaggio di ${v.id}`,
        detail: `${name(v)} · ${parts.filter((p) => p.vehicleId === v.id).length} pezzi catalogati finora`,
        action: "Riprendi",
        href: `/campo/${v.id}`,
        due: v.id === activeVehicleId ? new Date().toISOString() : undefined,
        roles: ["smontatore"],
      });
  }

  // Ricambi: raggruppati, perché sono tanti e si lavorano in serie
  const drafts = parts.filter((p) => p.status === "bozza");
  if (drafts.length)
    items.push({
      id: "bozze",
      kind: "ricambi",
      title: `Approva ${drafts.length} ${drafts.length === 1 ? "scheda in bozza" : "schede in bozza"}`,
      detail: "Controlla foto, condizioni e prezzo prima che diventino vendibili",
      action: "Controlla",
      href: "/pubblicazione",
      due: addDays(oldest(drafts), TERMS.bozza),
      roles: ["responsabile"],
    });
  const noLoc = parts.filter((p) => (p.status === "disponibile" || p.status === "bozza") && !p.location);
  if (noLoc.length)
    items.push({
      id: "posizioni",
      kind: "ricambi",
      title: `Metti a scaffale ${noLoc.length} ${noLoc.length === 1 ? "ricambio" : "ricambi"}`,
      detail: noLoc.slice(0, 3).map((p) => p.id).join(", ") + (noLoc.length > 3 ? "…" : ""),
      action: "Assegna",
      href: "/ricambi?filtro=senza-posizione",
      due: addDays(oldest(noLoc), TERMS.posizione),
      roles: ["magazziniere", "responsabile"],
    });
  const noLabel = parts.filter((p) => p.labelPrints === 0 && p.status !== "scartato" && p.status !== "venduto");
  if (noLabel.length)
    items.push({
      id: "etichette",
      kind: "ricambi",
      title: `Stampa ${noLabel.length} ${noLabel.length === 1 ? "etichetta" : "etichette"}`,
      detail: noLabel.slice(0, 3).map((p) => p.id).join(", ") + (noLabel.length > 3 ? "…" : ""),
      action: "Stampa",
      href: "/ricambi?filtro=senza-etichetta",
      roles: ["magazziniere", "smontatore"],
    });
  const lost = parts.filter((p) => p.missingSince && p.status !== "venduto" && p.status !== "scartato");
  if (lost.length)
    items.push({
      id: "mancanti",
      kind: "ricambi",
      title: `Cerca ${lost.length} ${lost.length === 1 ? "ricambio non trovato" : "ricambi non trovati"} all'inventario`,
      detail: lost.slice(0, 3).map((p) => p.id).join(", ") + (lost.length > 3 ? "…" : "") + " · registrati ma non al loro posto",
      action: "Cerca",
      href: "/ricambi?filtro=mancanti",
      due: addDays(lost.map((p) => p.missingSince!).sort()[0], 3),
      roles: ["magazziniere", "responsabile"],
    });
  const offline = parts.filter((p) => p.status === "disponibile" && !p.annuncioId);
  if (offline.length)
    items.push({
      id: "online",
      kind: "ricambi",
      title: `Porta online ${offline.length} ${offline.length === 1 ? "ricambio disponibile" : "ricambi disponibili"}`,
      detail: "Sono in magazzino ma non si vedono sul negozio",
      action: "Pubblica",
      href: "/pubblicazione",
      roles: ["responsabile"],
    });

  // Scorte sotto la soglia minima
  const low = rules.filter((r) => r.min > 0 && parts.filter((p) => p.typeId === r.typeId && p.status === "disponibile").length < r.min);
  if (low.length)
    items.push({
      id: "scorte",
      kind: "scorte",
      title: `${low.length} ${low.length === 1 ? "tipologia sotto" : "tipologie sotto"} la scorta minima`,
      detail: low.slice(0, 3).map((r) => typeById(r.typeId).name).join(", ") + (low.length > 3 ? "…" : "") + " · da privilegiare nei prossimi smontaggi",
      action: "Vedi",
      href: "/regole",
      roles: ["responsabile"],
    });

  // Ordini
  for (const o of orders) {
    if (o.status === "in attesa di pagamento")
      items.push({
        id: `paga-${o.id}`,
        kind: "ordine",
        title:
          new Date(addDays(o.createdAt, TERMS.pagamento)) < new Date()
            ? `Riserva scaduta su ${o.id}: incassa o annulla`
            : `Incassa l'ordine ${o.id}`,
        detail: `${o.customer} · ${o.partIds.length} ${o.partIds.length === 1 ? "pezzo riservato" : "pezzi riservati"} · ${o.channel}`,
        action: "Apri",
        href: "/vendite",
        due: addDays(o.createdAt, TERMS.pagamento),
        roles: ["vendite", "responsabile"],
      });
    if (o.status === "pagato")
      items.push({
        id: `spedisci-${o.id}`,
        kind: "ordine",
        title: o.channel === "banco" ? `Consegna l'ordine ${o.id}` : o.delivery === "ritiro" ? `Prepara ${o.id} per il ritiro in sede` : `Prepara e spedisci ${o.id}`,
        detail: `${o.customer} · ${o.partIds.map((pid) => { const l = parts.find((p) => p.id === pid)?.location; return l ? `${pid} in ${locToString(l)}` : `${pid} prelevato`; }).join(", ")}`,
        action: o.channel === "banco" || o.delivery === "ritiro" ? "Consegna" : "Spedisci",
        href: "/vendite",
        due: addDays(o.createdAt, TERMS.spedizione),
        roles: ["vendite", "responsabile"],
      });
  }

  for (const d of docs.filter((x) => x.type === "preventivo" && x.status === "aperto")) {
    const gone = d.lines.filter((l) => l.partId && parts.find((p) => p.id === l.partId)?.status !== "disponibile").length;
    items.push({
      id: `preventivo-${d.id}`,
      kind: "ordine",
      title: gone ? `Preventivo ${d.id}: ${gone} ${gone === 1 ? "pezzo non più disponibile" : "pezzi non più disponibili"}` : `Richiama ${d.customer.name} per il preventivo`,
      detail: gone ? `${d.customer.name} · aggiorna o annulla il preventivo` : `${d.id} · ${d.lines.length} ${d.lines.length === 1 ? "pezzo" : "pezzi"} · ${d.total} € · i pezzi non sono riservati`,
      action: "Apri",
      href: "/vendite/documenti",
      due: addDays(d.at, TERMS.preventivo),
      roles: ["vendite", "responsabile"],
    });
  }

  // Ambiente: registro, formulari e limiti dell'autorizzazione
  // Bozze del registro: vanno completate entro 2 giorni lavorativi (art. 190 c. 3 lett. d D.Lgs. 152/2006)
  for (const m of wasteMoves.filter(isDraft)) {
    const miss = missingFields(m, wasteMoves);
    const v = vehicles.find((x) => x.id === m.origin);
    items.push({
      id: `bozza-${m.id}`,
      kind: "ambiente",
      title: `Completa la registrazione${v ? ` di ${v.plate}` : ""}`,
      detail: `${m.eer} · manca ${miss.map((x) => MISSING_TEXT[x]).join(", ") || "la conferma"} · entro 2 giorni lavorativi`,
      action: "Completa",
      href: `/ambiente/periodo?mese=${periodKeyOf(m)}`,
      due: workingDaysAfter(m.at, 2),
      roles: ["accettazione", "responsabile", "consulente"],
    });
  }
  // Periodi chiusi da trasmettere: entro la fine del mese successivo (DM 59/2023 art. 15)
  for (const p of periodsOf(wasteMoves, firs).filter((x) => x.status === "da trasmettere"))
    items.push({
      id: `rentri-${p.key}`,
      kind: "ambiente",
      title: `Periodo di ${p.label} da trasmettere al RENTRI`,
      detail: `${p.moves.length} registrazioni${p.drafts ? ` · ${p.drafts} da completare` : ""}${p.warnings ? ` · ${p.warnings} avvisi` : ""}`,
      action: "Apri",
      href: `/ambiente/periodo?mese=${p.key}`,
      due: p.deadline,
      roles: ["consulente", "responsabile", "accettazione"],
    });
  for (const f of firs) {
    if (f.status === "da firmare")
      items.push({
        id: `firma-${f.id}`,
        kind: "ambiente",
        title: `Firma il formulario ${f.numero ?? f.id}`,
        detail: `${eerByCode(f.eer)?.short} · ${fmtKg(f.kg)} → ${f.destinatario}`,
        action: "Firma",
        href: "/ambiente/formulari",
        due: f.at,
        roles: ["accettazione", "responsabile"],
      });
    if (f.status === "firmato")
      items.push({
        id: `fir-esito-${f.id}`,
        kind: "ambiente",
        title: `Esito del formulario ${f.numero ?? f.id}`,
        detail: `${eerByCode(f.eer)?.short} · ${fmtKg(f.kg)} · segna quanto ha accettato ${f.destinatario}`,
        action: "Esito",
        href: "/ambiente/formulari",
        roles: ["accettazione", "responsabile", "consulente"],
      });
  }
  const pendingFir = new Set(firs.filter((f) => f.status === "da firmare").map((f) => f.eer));
  for (const st of stockByEer(wasteMoves).filter((x) => x.pct >= 0.8 && x.code !== "16 01 04*" && !pendingFir.has(x.code)))
    items.push({
      id: `limite-${st.code}`,
      kind: "ambiente",
      title: `Programma il ritiro: ${st.short.toLowerCase()} al ${Math.round(st.pct * 100)}% del limite`,
      detail: `${fmtKg(st.kg)} su ${fmtKg(st.limitKg)} autorizzati · ${st.code}`,
      action: "Formulario",
      href: `/ambiente/formulari?eer=${encodeURIComponent(st.code)}`,
      due: addDays(new Date().toISOString(), st.pct >= 0.95 ? 0 : 3),
      roles: ["accettazione", "responsabile"],
    });

  const rank: Record<Urgency, number> = { scaduto: 0, oggi: 1, settimana: 2, "quando-puoi": 3 };
  return items
    .filter((i) => i.roles.includes(role))
    .sort((a, b) => rank[urgencyOf(a.due)] - rank[urgencyOf(b.due)] || (a.due ?? "~").localeCompare(b.due ?? "~"));
}

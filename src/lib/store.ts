"use client";

import { useSyncExternalStore } from "react";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { buildSeed, pad } from "./seed";
import { STORE_SCHEMA } from "./schema";
import { locToString, originLabel, WAREHOUSES, type Warehouse } from "./warehouse";
import { eerByCode, movesForBonifica, movesForIntake, stockByEer } from "./ambiente";
import { differenzaPesata } from "./stime";
import { DEFAULT_LISTINI, onlinePrice, type Listino } from "./pricing";
import { typeById } from "./catalog";
import { GPSR_ERRORE, categoriaEbayDa, gpsrAfterVehicleChange, gpsrBlocksEbay, alignedPrice, groupKey, listingFieldsChanged, listingOf, membershipAfter, missingNote, partsOf, pickForSale, placementFor, quantityOf, refreshAnnuncio, shopPicks } from "./annunci";
import { buildAnnuncio, fieldsFromPart, gpsrOf, textFor, type BozzaAnnuncio } from "./annuncio-build";
import { isShippable } from "./spedizione";
import type { EsitoAllinea, VenditaEbay } from "./ebay/contratto";
import { applyEsito, type Inviato } from "./ebay/sync-puro";
import type {
  Annuncio,
  AuditEvent,
  BonificaItem,
  Channel,
  DocType,
  SalesDoc,
  Fir,
  Gpsr,
  InventoryCount,
  ListingStatus,
  Location,
  Order,
  Part,
  PartStatus,
  Role,
  ScrapPickup,
  Soggetto,
  StockRule,
  Vehicle,
  WasteMove,
} from "./types";
import { euro, publishChecks } from "./logic";
import { canTransmit, firNumberTaken, isDraft, missingFields, monthLabel, nextRegisterNumber, periodsOf } from "./periodo";

export const ROLE_USER: Record<Role, { user: string; device: string; label: string }> = {
  accettazione: { user: "Giulia (accettazione)", device: "PC ufficio", label: "Accettazione" },
  smontatore: { user: "Marco (smontaggio)", device: "Smartphone campo 1", label: "Smontatore" },
  magazziniere: { user: "Paolo (magazzino)", device: "Smartphone magazzino", label: "Magazziniere" },
  responsabile: { user: "Sara (responsabile)", device: "PC ufficio", label: "Responsabile" },
  vendite: { user: "Anna (vendite)", device: "PC banco", label: "Vendite" },
  consulente: { user: "Laura (consulente ambientale)", device: "PC studio", label: "Consulente ambientale" },
};

interface Counters {
  vehicle: number;
  part: number;
  order: number;
  event: number;
  move: number;
  fir: number;
  docs: Record<"P" | "DC" | "FT" | "NC", number>;
  inventory: number;
  scrapPickup?: number;
  annuncio: number;
}

interface State {
  role: Role;
  vehicles: Vehicle[];
  parts: Part[];
  annunci: Annuncio[];
  orders: Order[];
  audit: AuditEvent[];
  rules: StockRule[];
  wasteMoves: WasteMove[];
  firs: Fir[];
  soggetti: Soggetto[];
  docs: SalesDoc[];
  listini: Listino[];
  warehouses: Warehouse[];
  inventory: InventoryCount[];
  counters: Counters;
  activeVehicleId?: string;
}

type Result<T = undefined> = { ok: true; value: T } | { ok: false; error: string; conflicts?: string[] };
type Actor = { user: string; role: AuditEvent["role"]; device: string };

interface Actions {
  setRole: (r: Role) => void;
  setActiveVehicle: (id?: string) => void;
  addVehicle: (v: Omit<Vehicle, "id" | "createdBy" | "intakeAt">) => string;
  updateVehicle: (id: string, patch: Partial<Vehicle>, action: string, detail?: string) => void;
  addPart: (p: Omit<Part, "id" | "createdAt" | "createdBy" | "labelPrints">) => string;
  updatePart: (id: string, patch: Partial<Part>, action: string, detail?: string) => void;
  printLabel: (id: string) => void;
  setLocation: (id: string, loc: Location) => void;
  pickPart: (id: string, detail?: string) => void;
  scrapPart: (id: string, reason: string) => Result;
  unscrapPart: (id: string, prev: Pick<Part, "status" | "location">) => void;
  scrapPickup: (partIds: string[], kg: number, eurPerKg: number, buyer: string) => Result<string>;
  setPartStatus: (id: string, status: PartStatus, reason?: string) => void;
  // Annunci: un annuncio raggruppa i pezzi uguali; la quantità è quella dei pezzi disponibili
  publishAnnuncio: (partId: string, bozza: BozzaAnnuncio) => Result<string>;
  placePart: (partId: string) => void;
  resolvePrice: (partId: string, scelta: "annuncio" | "pezzo") => void;
  setAnnuncioPrice: (annuncioId: string, price: number) => void;
  withdrawAnnuncio: (annuncioId: string, canale: "negozio" | "ebay" | "tutti") => Result<string>;
  republishAnnuncio: (annuncioId: string, canali: { negozio: boolean; ebay: boolean }) => Result<string>;
  setAnnuncioGpsr: (annuncioId: string, gpsr: Gpsr) => void;
  /** Numero della categoria eBay scritto dall'operatore; "" la toglie (la sceglie di nuovo eBay) */
  setAnnuncioCategoria: (annuncioId: string, categoriaId: string) => Result<string>;
  editAnnuncioText: (annuncioId: string, titolo: string, descrizione: string) => void;
  regenerateText: (annuncioId: string) => void;
  orderFromAnnunci: (channel: "negozio", annuncioIds: string[], customer: string, actor?: Actor, delivery?: "corriere" | "ritiro") => Result<string>;
  importEbaySale: (v: VenditaEbay) => Result<string>;
  setEbayResult: (annuncioId: string, esito: EsitoAllinea, inviato: Inviato) => void;
  markOrderHandled: (orderId: string) => void;
  createOrder: (
    channel: Channel,
    partIds: string[],
    customer: string,
    actor?: { user: string; role: AuditEvent["role"]; device: string },
    prices?: Record<string, number>,
    delivery?: "corriere" | "ritiro",
  ) => Result<string>;
  payOrder: (orderId: string, success: boolean, actor?: { user: string; role: AuditEvent["role"]; device: string }) => void;
  cancelOrder: (orderId: string, reason?: string) => void;
  shipOrder: (orderId: string) => void;
  returnOrder: (orderId: string) => void;
  setRule: (typeId: string, min: number, max: number) => void;
  saveBonifica: (vehicleId: string, items: BonificaItem[], weightKg: number) => number;
  // Registro rifiuti: le registrazioni numerate non si modificano; si completano le bozze, si rettifica o si annulla
  completeDraft: (id: string, patch: { produttoreNome?: string; produttoreCf?: string; certificato?: { numero: string; data: string }; kg?: number; pesoPesa?: boolean }) => Result<boolean>;
  rectifyMove: (id: string, kg: number, motivo: string) => Result<string>;
  cancelMove: (id: string, motivo: string) => Result<string>;
  transmitPeriod: (key: string) => Result<string>;
  // Formulari ricevuti dalla ditta che ritira
  receiveFir: (f: Pick<Fir, "numero" | "emessoAt" | "eer" | "kg" | "destinatarioId" | "trasportatoreId" | "intermediarioId" | "targa" | "conducente" | "inizioTrasportoAt" | "rinfusa" | "svuota" | "annotazioni" | "foto">) => Result<string>;
  setFirPhotos: (id: string, foto: string[]) => void;
  signFir: (id: string) => Result;
  confirmMove: (id: string) => void;
  setFirOutcome: (id: string, esito: NonNullable<Fir["esito"]>, kgAccettati: number, arrivoAt: string) => Result;
  saveSoggetto: (s: Soggetto) => void;
  createQuote: (partIds: string[], customer: SalesDoc["customer"], prices?: Record<string, number>, listino?: string) => string;
  issueDoc: (orderId: string, type: "documento commerciale" | "fattura", customer: SalesDoc["customer"], prices?: Record<string, number>, listino?: string) => string;
  convertQuote: (docId: string, type: "documento commerciale" | "fattura") => Result<string>;
  cancelQuote: (docId: string) => void;
  saveListini: (l: Listino[]) => void;
  addWarehouse: (w: Warehouse) => void;
  closeCount: (c: Omit<InventoryCount, "id" | "at" | "by">) => string;
  log: (e: Omit<AuditEvent, "id" | "at" | "user" | "role" | "device"> & Partial<Pick<AuditEvent, "user" | "role" | "device">>) => void;
  reset: () => void;
}

const now = () => new Date().toISOString();
const EBAY_ACTOR: Actor = { user: "Connettore eBay", role: "sistema", device: "Ponte eBay" };

// Chiave dei dati salvati: cambia quando cambia la struttura dei dati demo
export { STORE_SCHEMA }; // definito in schema.ts, usato anche dal server

function initial(): State {
  const s = buildSeed();
  return {
    role: "smontatore",
    vehicles: s.vehicles,
    parts: s.parts,
    annunci: s.annunci,
    orders: s.orders,
    audit: s.audit,
    rules: s.rules,
    wasteMoves: s.wasteMoves,
    firs: s.firs,
    soggetti: s.soggetti,
    docs: s.docs,
    listini: DEFAULT_LISTINI,
    warehouses: WAREHOUSES,
    inventory: s.inventory,
    counters: s.counters,
    activeVehicleId: "V-000118",
  };
}

// Copia locale nel browser del dispositivo. Il browser concede pochi MB: se si riempie
// (es. tante foto rimaste nel telefono perché il server non rispondeva) si toglie la foto dalla copia
// locale (resta in memoria e sul server) e, se non basta, si smette di salvare in locale senza bloccare
// il lavoro: l'archivio vero è quello sul server. useDeviceStorageFull() lo segnala all'utente.
let storageFull = false;
const storageListeners = new Set<() => void>();
const setStorageFull = (v: boolean) => {
  if (storageFull === v) return;
  storageFull = v;
  storageListeners.forEach((f) => f());
};
const deviceStorage = {
  getItem: (k: string) => {
    try {
      return localStorage.getItem(k);
    } catch {
      return null;
    }
  },
  setItem: (k: string, v: string) => {
    try {
      localStorage.setItem(k, v);
      setStorageFull(false);
      return;
    } catch {}
    try {
      localStorage.setItem(k, v.replace(/"data:image\/[^"]*"/g, '"/renders/scatola.png"'));
      setStorageFull(false);
    } catch {
      setStorageFull(true);
    }
  },
  removeItem: (k: string) => {
    try {
      localStorage.removeItem(k);
    } catch {}
  },
};
export const useDeviceStorageFull = () =>
  useSyncExternalStore(
    (f) => (storageListeners.add(f), () => void storageListeners.delete(f)),
    () => storageFull,
    () => false,
  );

export const useStore = create<State & Actions>()(
  persist(
    (set, get) => {
      const event = (
        e: Omit<AuditEvent, "id" | "at" | "user" | "role" | "device"> & Partial<Pick<AuditEvent, "user" | "role" | "device">>,
      ): AuditEvent => {
        const { role, counters } = get();
        const who = ROLE_USER[role];
        counters.event += 1;
        return {
          id: `E-${pad(counters.event)}`,
          at: now(),
          user: e.user ?? who.user,
          role: e.role ?? role,
          device: e.device ?? who.device,
          entity: e.entity,
          entityId: e.entityId,
          action: e.action,
          detail: e.detail,
        };
      };
      const push = (...evs: AuditEvent[]) => set((s) => ({ audit: [...s.audit, ...evs] }));
      // Il registro di carico e scarico si scrive da solo a partire dagli eventi operativi
      // Le registrazioni complete ricevono subito il numero progressivo; quelle a cui manca un dato restano bozze
      const addMoves = (ms: Omit<WasteMove, "id">[]) => {
        const ids: string[] = [];
        set((s) => {
          let n = s.counters.move;
          const all = [...s.wasteMoves];
          const by = ROLE_USER[s.role].user;
          for (const m of ms) {
            const id = `M-${pad(++n)}`;
            ids.push(id);
            const at = now();
            const ready = missingFields(m as WasteMove, all).length === 0;
            all.push({ ...m, id, ...(ready ? { numero: nextRegisterNumber(all, at), registeredAt: at, by } : {}) });
          }
          return { wasteMoves: all, counters: { ...s.counters, move: n } };
        });
        return ids;
      };

      const PREFIX: Record<DocType, "P" | "DC" | "FT" | "NC"> = { preventivo: "P", "documento commerciale": "DC", fattura: "FT", "nota di credito": "NC" };
      const newDoc = (d: Omit<SalesDoc, "id" | "at">) => {
        const k = PREFIX[d.type];
        const n = get().counters.docs[k] + 1;
        const id = `${k}-2026-${String(n).padStart(4, "0")}`;
        set((s) => ({ docs: [{ ...d, id, at: now() }, ...s.docs], counters: { ...s.counters, docs: { ...s.counters.docs, [k]: n } } }));
        push(event({ entity: "ordine", entityId: id, action: `${d.type[0].toUpperCase()}${d.type.slice(1)} emesso`, detail: `${d.customer.name} · ${d.total} €${d.orderId ? ` · ${d.orderId}` : ""}` }));
        return id;
      };
      const linesOf = (partIds: string[], prices?: Record<string, number>) =>
        partIds.map((pid) => {
          const p = get().parts.find((x) => x.id === pid);
          return { partId: pid, description: `${pid} · ${p?.description ?? "ricambio"}`, price: prices?.[pid] ?? p?.price ?? 0 };
        });

      // ——— Annunci ———
      const shipOf = (p: Part) => isShippable(p, typeById(p.typeId).shippable);
      const keyOf = (p: Part) => groupKey(p, shipOf(p));
      // Dati del pezzo che decidono l'annuncio: se cambiano, il pezzo può dover cambiare annuncio
      const sigOf = (p: Part) => JSON.stringify([p.typeId, p.oem ?? "", p.oemVerified, p.side ?? "", p.condition, shipOf(p)]);
      const checksPass = (p: Part) => publishChecks(p, get().vehicles.find((v) => v.id === p.vehicleId)).every((c) => c.ok || !c.blocking);
      const annuncioEvent = (aid: string, action: string, detail?: string, actor?: Actor) => event({ entity: "annuncio", entityId: aid, action, detail, ...actor });
      const setAnnuncioOf = (partId: string, aid: string | undefined) =>
        set((st) => ({ parts: st.parts.map((x) => (x.id === partId ? { ...x, annuncioId: aid } : x)) }));

      // Ricalcolo dopo ogni cambiamento che tocca quantità o dati: stato del negozio, data a zero,
      // eBay da riallineare, testo riscritto se l'operatore non l'ha modificato
      const touchAnnuncio = (aid: string) => {
        let esaurito = false;
        set((st) => {
          const a = st.annunci.find((x) => x.id === aid);
          if (!a) return {};
          const next = refreshAnnuncio(a, st.parts, now(), (q) => textFor(a, st.parts, st.vehicles, q));
          esaurito = !!next.esauritoDa && !a.esauritoDa;
          return { annunci: st.annunci.map((x) => (x.id === aid ? next : x)) };
        });
        if (esaurito) push(annuncioEvent(aid, "Annuncio esaurito", "Nessun pezzo disponibile: l'annuncio resta, a zero"));
      };

      // Un pezzo disponibile, senza annuncio e che passa i controlli entra da solo nell'annuncio uguale con lo stesso prezzo
      const placePart = (partId: string) => {
        const s = get();
        const p = s.parts.find((x) => x.id === partId);
        if (!p || p.status !== "disponibile" || p.annuncioId || !checksPass(p)) return;
        const place = placementFor(p, keyOf(p), s.annunci);
        if (place.kind !== "unisci") return;
        setAnnuncioOf(partId, place.annuncioId);
        push(annuncioEvent(place.annuncioId, "Pezzo aggiunto all'annuncio", partId));
        touchAnnuncio(place.annuncioId);
      };

      // I pezzi in coda uguali a un annuncio appena creato, ripubblicato o con un prezzo nuovo vi entrano da soli
      const joinQueued = (aid: string) => {
        const a = get().annunci.find((x) => x.id === aid);
        if (!a?.chiave) return;
        get()
          .parts.filter((p) => !p.annuncioId && p.status === "disponibile" && keyOf(p) === a.chiave)
          .forEach((p) => placePart(p.id));
      };

      // Dopo un cambio di stato: scartato o invendibile escono dall'annuncio; chi torna disponibile
      // resta solo se passa i controlli (altrimenti torna in coda); poi si ricalcolano gli annunci toccati
      // e i pezzi disponibili senza annuncio cercano un annuncio uguale
      const settle = (ids: string[]) => {
        const touched = new Set<string>();
        for (const id of ids) {
          const p = get().parts.find((x) => x.id === id);
          if (!p?.annuncioId) continue;
          touched.add(p.annuncioId);
          if (membershipAfter(p, checksPass(p)) === p.annuncioId) {
            // Resta o rientra disponibile: prende il prezzo dell'annuncio (un prezzo solo per i pezzi uguali)
            const a = get().annunci.find((x) => x.id === p.annuncioId);
            const price = alignedPrice(p, a);
            if (price !== undefined) {
              set((st) => ({ parts: st.parts.map((x) => (x.id === id ? { ...x, price } : x)) }));
              push(event({ entity: "ricambio", entityId: id, action: `Prezzo allineato all'annuncio ${p.annuncioId}: ${euro(p.price)} → ${euro(price)}` }));
            }
            continue;
          }
          setAnnuncioOf(id, undefined);
          push(
            annuncioEvent(
              p.annuncioId,
              "Pezzo uscito dall'annuncio",
              `${id} · ${p.status === "disponibile" ? "controlli di pubblicazione non superati: torna in coda" : p.status}`,
            ),
          );
        }
        touched.forEach(touchAnnuncio);
        ids.forEach(placePart);
      };

      return {
        ...initial(),
        setRole: (role) => set({ role }),
        setActiveVehicle: (id) => set({ activeVehicleId: id }),
        log: (e) => push(event(e)),

        addVehicle: (v) => {
          const n = get().counters.vehicle + 1;
          const id = `V-${pad(n)}`;
          const veh: Vehicle = { ...v, id, intakeAt: now(), createdBy: ROLE_USER[get().role].user };
          set((s) => ({ vehicles: [veh, ...s.vehicles], counters: { ...s.counters, vehicle: n } }));
          push(event({ entity: "veicolo", entityId: id, action: "Ingresso veicolo registrato", detail: `${v.plate} · ${v.make} ${v.model}${v.verification === "da verificare" ? " · da verificare" : ""}` }));
          addMoves(movesForIntake(veh, veh.intakeAt));
          return id;
        },

        updateVehicle: (id, patch, action, detail) => {
          const prev = get().vehicles.find((v) => v.id === id);
          set((s) => ({ vehicles: s.vehicles.map((v) => (v.id === id ? { ...v, ...patch } : v)) }));
          push(event({ entity: "veicolo", entityId: id, action, detail }));
          const next = get().vehicles.find((v) => v.id === id);
          if (!prev || !next) return;
          // Provenienza cambiata (es. tornata «da verificare»): i controlli bloccanti tolgono i suoi pezzi dagli annunci,
          // e con la provenienza di nuovo verificata vi rientrano
          if (prev.verification !== next.verification) settle(get().parts.filter((p) => p.vehicleId === id).map((p) => p.id));
          // Marca, modello, versione, anno o km cambiati: gli annunci dei suoi pezzi riscrivono il testo
          // (se non modificato) e si riallineano su eBay; con marca o anno cambiati si ricalcola anche il GPSR,
          // salvo quello confermato a mano dall'operatore
          const changed = listingFieldsChanged(prev, next);
          if (!changed.text) return;
          const aids = [...new Set(get().parts.filter((p) => p.vehicleId === id && p.annuncioId).map((p) => p.annuncioId!))];
          if (changed.gpsr)
            set((st) => ({
              annunci: st.annunci.map((a) => {
                if (!aids.includes(a.id)) return a;
                const gpsr = gpsrAfterVehicleChange(a, gpsrOf(a, st.parts, st.vehicles, id));
                return gpsr ? { ...a, gpsr } : a;
              }),
            }));
          aids.forEach(touchAnnuncio);
        },

        addPart: (p) => {
          const n = get().counters.part + 1;
          const id = `R-${pad(n)}`;
          const part: Part = { ...p, id, createdAt: now(), createdBy: ROLE_USER[get().role].user, labelPrints: 0 };
          const v = get().vehicles.find((x) => x.id === p.vehicleId);
          // Il primo pezzo catalogato da un veicolo accettato ne avvia lo smontaggio
          const starts = v?.work === "accettato" && p.origin !== "inventario";
          set((s) => ({
            parts: [part, ...s.parts],
            counters: { ...s.counters, part: n },
            vehicles: starts ? s.vehicles.map((x) => (x.id === v!.id ? { ...x, work: "in smontaggio" } : x)) : s.vehicles,
          }));
          if (starts) push(event({ entity: "veicolo", entityId: v!.id, action: "Smontaggio avviato", detail: `primo pezzo ${id}` }));
          push(event({ entity: "ricambio", entityId: id, action: "Ricambio catalogato", detail: `${p.description} da ${originLabel(p)}${p.aiSuggested ? ` · suggerimento IA ${p.aiSuggested.accepted ? "confermato" : "corretto"}` : ""}` }));
          placePart(id);
          return id;
        },

        updatePart: (id, patch, action, detail) => {
          const prev = get().parts.find((x) => x.id === id);
          if (!prev) return;
          const next: Part = { ...prev, ...patch };
          set((s) => ({ parts: s.parts.map((p) => (p.id === id ? next : p)) }));
          push(event({ entity: "ricambio", entityId: id, action, detail }));
          const a = prev.annuncioId ? get().annunci.find((x) => x.id === prev.annuncioId) : undefined;
          if (a) {
            // Cambio di chiave: con più pezzi il pezzo esce e torna in coda; con un pezzo solo cambia l'annuncio
            const keyChanged = sigOf(prev) !== sigOf(next) && !(a.chiave && keyOf(next) === a.chiave);
            if (keyChanged && partsOf(a, get().parts).length > 1) {
              setAnnuncioOf(id, undefined);
              push(annuncioEvent(a.id, "Pezzo uscito dall'annuncio", `${id} · dati cambiati: torna in coda`));
            } else if (keyChanged) {
              const f = fieldsFromPart(next, get().vehicles);
              const generated = ["Tipo", "Marca", "Numero ricambio produttore", "Posizionamento sul veicolo"];
              const kept = Object.fromEntries(Object.entries(a.caratteristiche).filter(([k]) => !generated.includes(k)));
              set((s) => ({ annunci: s.annunci.map((x) => (x.id === a.id ? { ...x, ...f, caratteristiche: { ...kept, ...f.caratteristiche } } : x)) }));
              push(annuncioEvent(a.id, "Dati dell'annuncio aggiornati", `da ${id}`));
            }
            // Prezzo: i pezzi uguali hanno un prezzo solo, quindi cambia quello dell'annuncio.
            // Un pezzo venduto cambia solo il suo prezzo
            const still = next.status !== "venduto" && get().parts.find((x) => x.id === id)?.annuncioId === a.id;
            if (still && typeof patch.price === "number" && patch.price > 0 && patch.price !== a.price) get().setAnnuncioPrice(a.id, patch.price);
          }
          settle([id]);
          if (a && get().parts.find((x) => x.id === id)?.annuncioId !== a.id) touchAnnuncio(a.id);
        },

        printLabel: (id) => {
          const p = get().parts.find((x) => x.id === id);
          if (!p) return;
          const reprint = p.labelPrints > 0;
          set((s) => ({ parts: s.parts.map((x) => (x.id === id ? { ...x, labelPrints: x.labelPrints + 1 } : x)) }));
          push(event({ entity: "ricambio", entityId: id, action: reprint ? "Ristampa etichetta" : "Etichetta stampata", detail: reprint ? `Stampa n. ${p.labelPrints + 1}, stesso ID` : undefined }));
        },

        setLocation: (id, loc) => {
          const p = get().parts.find((x) => x.id === id);
          set((s) => ({ parts: s.parts.map((x) => (x.id === id ? { ...x, location: loc, missingSince: undefined } : x)) }));
          push(event({ entity: "ricambio", entityId: id, action: p?.location ? "Ricambio spostato" : "Posizione assegnata", detail: p?.location ? `${locToString(p.location)} → ${locToString(loc)}` : locToString(loc) }));
          placePart(id);
        },

        // Il pezzo esce fisicamente dallo scaffale (prelievo per una vendita, o scansione annullata)
        pickPart: (id, detail) => {
          const p = get().parts.find((x) => x.id === id);
          if (!p?.location) return;
          set((s) => ({ parts: s.parts.map((x) => (x.id === id ? { ...x, location: undefined, missingSince: undefined } : x)) }));
          push(event({ entity: "ricambio", entityId: id, action: "Prelevato dallo scaffale", detail: `${locToString(p.location)}${detail ? ` · ${detail}` : ""}` }));
        },

        // Scarto: il pezzo esce dallo scaffale e va nell'area rottami (si vende a peso con il ritiro)
        scrapPart: (id, reason) => {
          const p = get().parts.find((x) => x.id === id);
          if (!p) return { ok: false, error: "Ricambio non trovato" };
          if (p.status === "venduto") return { ok: false, error: `${id} è già venduto` };
          if (p.status === "scartato") return { ok: false, error: `${id} è già nei rottami` };
          if (p.status === "riservato") return { ok: false, error: `${id} è in un ordine: annulla prima l'ordine` };
          const from = p.location ? locToString(p.location) : undefined;
          set((s) => ({
            parts: s.parts.map((x) =>
              x.id === id
                ? { ...x, status: "scartato" as const, location: undefined, missingSince: undefined, scrap: { at: now(), reason, from } }
                : x,
            ),
          }));
          push(event({ entity: "ricambio", entityId: id, action: "Messo nei rottami", detail: `${from ? `da ${from} · ` : ""}${reason}` }));
          settle([id]);
          return { ok: true, value: undefined };
        },

        unscrapPart: (id, prev) => {
          set((s) => ({ parts: s.parts.map((x) => (x.id === id ? { ...x, ...prev, scrap: undefined } : x)) }));
          push(event({ entity: "ricambio", entityId: id, action: "Tolto dai rottami", detail: prev.location ? `rimesso in ${locToString(prev.location)}` : undefined }));
          settle([id]);
        },

        scrapPickup: (partIds, kg, eurPerKg, buyer) => {
          const s = get();
          const ids = partIds.filter((id) => s.parts.some((p) => p.id === id && p.status === "scartato" && !p.scrap?.pickup));
          if (!ids.length) return { ok: false, error: "Nessun pezzo nei rottami da ritirare" };
          if (!(kg > 0)) return { ok: false, error: "Scrivi il peso del carico" };
          const n = (s.counters.scrapPickup ?? 0) + 1;
          const pickup: ScrapPickup = { id: `RT-${String(n).padStart(4, "0")}`, at: now(), buyer: buyer.trim() || "Acquirente non indicato", kg, eurPerKg };
          set((st) => ({
            parts: st.parts.map((p) => (ids.includes(p.id) && p.scrap ? { ...p, scrap: { ...p.scrap, pickup } } : p)),
            counters: { ...st.counters, scrapPickup: n },
          }));
          const total = Math.round(kg * eurPerKg * 100) / 100;
          push(event({ entity: "ricambio", entityId: pickup.id, action: "Ritiro rottami a peso", detail: `${ids.length} pezzi · ${kg} kg · ${eurPerKg} €/kg = ${total} € · ${pickup.buyer}` }));
          return { ok: true, value: pickup.id };
        },

        setPartStatus: (id, status, reason) => {
          const p = get().parts.find((x) => x.id === id);
          if (!p) return;
          set((s) => ({ parts: s.parts.map((x) => (x.id === id ? { ...x, status } : x)) }));
          push(event({ entity: "ricambio", entityId: id, action: `Stato: ${p.status} → ${status}`, detail: reason }));
          settle([id]);
        },

        // Il pezzo non ha un annuncio uguale: ne nasce uno nuovo, sui canali scelti
        publishAnnuncio: (partId, bozza) => {
          const s = get();
          const p = s.parts.find((x) => x.id === partId);
          if (!p) return { ok: false, error: "Ricambio non trovato" };
          const v = s.vehicles.find((x) => x.id === p.vehicleId);
          const missing = publishChecks(p, v).filter((c) => !c.ok && c.blocking);
          if (missing.length) return { ok: false, error: "Scheda incompleta", conflicts: missing.map((m) => m.label) };
          if (p.annuncioId) return { ok: false, error: `Il pezzo è già nell'annuncio ${p.annuncioId}`, conflicts: [p.annuncioId] };
          if (!bozza.canali.negozio && !bozza.canali.ebay) return { ok: false, error: "Scegli almeno un canale" };
          if (bozza.canali.ebay && gpsrBlocksEbay(bozza.gpsr)) return { ok: false, error: GPSR_ERRORE };
          const titolo = bozza.titolo.trim();
          if (!titolo) return { ok: false, error: "Scrivi il titolo dell'annuncio" };
          if (titolo.length > 80) return { ok: false, error: "Il titolo supera gli 80 caratteri ammessi da eBay" };
          const categoria = categoriaEbayDa(bozza.categoriaEbay ?? "");
          if (categoria === undefined) return { ok: false, error: "Il numero della categoria eBay ha solo cifre" };
          // Con un annuncio uguale non se ne crea un secondo
          const place = placementFor(p, keyOf(p), s.annunci);
          if (place.kind === "unisci") {
            placePart(partId);
            return { ok: true, value: place.annuncioId };
          }
          if (place.kind === "prezzo diverso")
            return { ok: false, error: `Prezzo diverso dall'annuncio ${place.annuncioId}: ${euro(p.price)} contro ${euro(place.prezzoAnnuncio)}`, conflicts: [place.annuncioId] };
          if (place.kind === "annuncio ritirato") return { ok: false, error: `Ripubblica l'annuncio ${place.annuncioId}: è uguale a questo pezzo`, conflicts: [place.annuncioId] };
          const n = s.counters.annuncio + 1;
          const aid = `A-${pad(n)}`;
          const base = buildAnnuncio([p], s.vehicles, aid, now());
          const a: Annuncio = {
            ...base,
            titolo,
            descrizione: bozza.descrizione.trim(),
            testoModificato: bozza.testoModificato,
            caratteristiche: bozza.caratteristiche,
            gpsr: bozza.gpsr,
            ...(bozza.gpsrManuale ? { gpsrManuale: true } : {}),
            negozio: bozza.canali.negozio ? base.negozio : undefined,
            ebay: bozza.canali.ebay
              ? { stato: "in pubblicazione", daRiallineare: true, ...(categoria ? { categoria: { id: categoria, manuale: true } } : {}) }
              : undefined,
          };
          set((st) => ({
            annunci: [a, ...st.annunci],
            parts: st.parts.map((x) => (x.id === partId ? { ...x, annuncioId: aid } : x)),
            counters: { ...st.counters, annuncio: n },
          }));
          const canali = [bozza.canali.negozio && "negozio", bozza.canali.ebay && "eBay"].filter(Boolean).join(" ed ");
          push(annuncioEvent(aid, "Annuncio creato", `${partId} · ${canali}`));
          joinQueued(aid);
          return { ok: true, value: aid };
        },

        placePart: (partId) => placePart(partId),

        // Prezzo diverso da quello dell'annuncio uguale: si allinea il pezzo, oppure l'annuncio prende il prezzo nuovo
        resolvePrice: (partId, scelta) => {
          const s = get();
          const p = s.parts.find((x) => x.id === partId);
          if (!p || p.annuncioId || p.price === undefined) return;
          const place = placementFor(p, keyOf(p), s.annunci);
          if (place.kind !== "prezzo diverso") return;
          if (scelta === "annuncio") {
            set((st) => ({ parts: st.parts.map((x) => (x.id === partId ? { ...x, price: place.prezzoAnnuncio } : x)) }));
            push(event({ entity: "ricambio", entityId: partId, action: "Prezzo allineato all'annuncio", detail: `${euro(p.price)} → ${euro(place.prezzoAnnuncio)} · ${place.annuncioId}` }));
          } else get().setAnnuncioPrice(place.annuncioId, p.price);
          placePart(partId);
        },

        // Un prezzo solo per i pezzi uguali: cambia sull'annuncio e su tutti i suoi pezzi non ancora venduti
        setAnnuncioPrice: (annuncioId, price) => {
          const a = get().annunci.find((x) => x.id === annuncioId);
          if (!a || !Number.isFinite(price) || !(price > 0) || a.price === price) return;
          const mine = partsOf(a, get().parts).filter((p) => p.status !== "venduto");
          set((st) => ({
            annunci: st.annunci.map((x) => (x.id === annuncioId ? { ...x, price } : x)),
            parts: st.parts.map((x) => (x.annuncioId === annuncioId && x.status !== "venduto" ? { ...x, price } : x)),
          }));
          push(annuncioEvent(annuncioId, "Prezzo dell'annuncio cambiato", `${euro(a.price)} → ${euro(price)} · ${mine.length} ${mine.length === 1 ? "pezzo" : "pezzi"}`));
          touchAnnuncio(annuncioId);
          joinQueued(annuncioId);
        },

        withdrawAnnuncio: (annuncioId, canale) => {
          const a = get().annunci.find((x) => x.id === annuncioId);
          if (!a) return { ok: false, error: "Annuncio non trovato" };
          const neg = canale !== "ebay" && !!a.negozio && a.negozio.stato !== "ritirato";
          const eb = canale !== "negozio" && !!a.ebay && a.ebay.stato !== "ritirato";
          if (!neg && !eb) return { ok: false, error: `L'annuncio ${annuncioId} è già ritirato` };
          set((st) => ({
            annunci: st.annunci.map((x) =>
              x.id === annuncioId
                ? {
                    ...x,
                    negozio: neg ? { stato: "ritirato" } : x.negozio,
                    // Su eBay il ritiro si manda al ponte, salvo un annuncio mai partito
                    ebay: eb && x.ebay ? { ...x.ebay, stato: "ritirato", daRiallineare: x.ebay.stato !== "non pubblicato" } : x.ebay,
                  }
                : x,
            ),
          }));
          push(annuncioEvent(annuncioId, `Annuncio ritirato da ${neg && eb ? "negozio ed eBay" : neg ? "negozio" : "eBay"}`));
          return { ok: true, value: annuncioId };
        },

        republishAnnuncio: (annuncioId, canali) => {
          const a = get().annunci.find((x) => x.id === annuncioId);
          if (!a) return { ok: false, error: "Annuncio non trovato" };
          const neg = canali.negozio && (!a.negozio || a.negozio.stato === "ritirato");
          const eb = canali.ebay && (!a.ebay || !["online", "esaurito", "in pubblicazione"].includes(a.ebay.stato));
          if (!neg && !eb) return { ok: false, error: `L'annuncio ${annuncioId} è già online su quel canale` };
          if (eb && gpsrBlocksEbay(a.gpsr)) return { ok: false, error: GPSR_ERRORE };
          const qty = quantityOf(a, get().parts);
          set((st) => ({
            annunci: st.annunci.map((x) =>
              x.id === annuncioId
                ? {
                    ...x,
                    negozio: neg ? { stato: qty > 0 ? "online" : "esaurito" } : x.negozio,
                    ebay: eb ? { ...x.ebay, stato: "in pubblicazione", daRiallineare: true, errore: undefined } : x.ebay,
                  }
                : x,
            ),
          }));
          push(annuncioEvent(annuncioId, `Annuncio ripubblicato su ${neg && eb ? "negozio ed eBay" : neg ? "negozio" : "eBay"}`));
          touchAnnuncio(annuncioId);
          joinQueued(annuncioId);
          return { ok: true, value: annuncioId };
        },

        // GPSR confermato dall'operatore: serve prima di attivare eBay
        // Confermato a mano: resta anche se poi cambiano marca o anno del veicolo; "da confermare" lo riapre
        setAnnuncioGpsr: (annuncioId, gpsr) => {
          if (!get().annunci.some((x) => x.id === annuncioId)) return;
          const gpsrManuale = gpsr.tipo !== "da confermare";
          set((st) => ({ annunci: st.annunci.map((x) => (x.id === annuncioId ? { ...x, gpsr, gpsrManuale } : x)) }));
          push(annuncioEvent(annuncioId, "GPSR dell'annuncio confermato", gpsr.tipo === "esente" ? "Messo in commercio prima del 13/12/2024" : gpsr.tipo === "produttore" ? gpsr.produttore.ragioneSociale : "da confermare"));
          touchAnnuncio(annuncioId);
        },

        setAnnuncioCategoria: (annuncioId, categoriaId) => {
          const a = get().annunci.find((x) => x.id === annuncioId);
          if (!a?.ebay) return { ok: false, error: "L'annuncio non è su eBay" };
          const id = categoriaEbayDa(categoriaId);
          if (id === undefined) return { ok: false, error: "Il numero della categoria eBay ha solo cifre" };
          const prima = a.ebay.categoria;
          if ((id || undefined) === (prima?.manuale ? prima.id : undefined)) return { ok: true, value: annuncioId };
          set((st) => ({
            annunci: st.annunci.map((x) =>
              x.id === annuncioId && x.ebay
                ? {
                    ...x,
                    // Senza numero la categoria la sceglie di nuovo eBay; un annuncio ritirato non si rimanda
                    ebay: { ...x.ebay, categoria: id ? { id, manuale: true } : undefined, daRiallineare: x.ebay.stato === "ritirato" ? x.ebay.daRiallineare : true },
                  }
                : x,
            ),
          }));
          push(annuncioEvent(annuncioId, "Categoria eBay cambiata", id ? `${prima?.id ?? "scelta da eBay"} → ${id}` : "la sceglie eBay"));
          return { ok: true, value: annuncioId };
        },

        editAnnuncioText: (annuncioId, titolo, descrizione) => {
          const t = titolo.trim().slice(0, 80);
          if (!t || !get().annunci.some((x) => x.id === annuncioId)) return;
          set((st) => ({ annunci: st.annunci.map((x) => (x.id === annuncioId ? { ...x, titolo: t, descrizione: descrizione.trim(), testoModificato: true } : x)) }));
          push(annuncioEvent(annuncioId, "Testo dell'annuncio modificato", t));
          touchAnnuncio(annuncioId);
        },

        regenerateText: (annuncioId) => {
          if (!get().annunci.some((x) => x.id === annuncioId)) return;
          set((st) => ({ annunci: st.annunci.map((x) => (x.id === annuncioId ? { ...x, testoModificato: false } : x)) }));
          push(annuncioEvent(annuncioId, "Testo dell'annuncio riscritto in automatico"));
          touchAnnuncio(annuncioId);
        },

        // Ordine del negozio per annunci: il prossimo a partire si sceglie nello stesso aggiornamento
        // che controlla la disponibilità, così lo stesso pezzo non si vende due volte
        orderFromAnnunci: (channel, annuncioIds, customer, actor, delivery) => {
          if (!annuncioIds.length) return { ok: false, error: "Il carrello è vuoto" };
          let made = undefined as { id: string; partIds: string[]; annunci: string[] } | undefined;
          let conflicts: string[] = [];
          set((st) => {
            const r = shopPicks(annuncioIds, st.annunci, st.parts);
            if (r.conflicts.length || !r.picks.length) {
              conflicts = r.conflicts;
              return {};
            }
            const partIds = r.picks.map((x) => x.partId);
            const prices = Object.fromEntries(r.picks.map((x) => [x.partId, onlinePrice(x.price) ?? 0]));
            const amount = Math.round(Object.values(prices).reduce((t, x) => t + x, 0) * 100) / 100;
            const pickupOnly = st.parts.some((p) => partIds.includes(p.id) && !shipOf(p));
            const n = st.counters.order + 1;
            const id = `O-${pad(n)}`;
            const at = now();
            made = { id, partIds, annunci: [...new Set(r.picks.map((x) => x.annuncioId))] };
            return {
              parts: st.parts.map((x) => (partIds.includes(x.id) ? { ...x, status: "riservato" as const } : x)),
              orders: [
                { id, channel, delivery: pickupOnly ? "ritiro" : delivery, partIds, amount, prices, status: "in attesa di pagamento", customer, createdAt: at, history: [{ at, status: "in attesa di pagamento" }] },
                ...st.orders,
              ],
              counters: { ...st.counters, order: n },
            };
          });
          if (!made) {
            push(event({ entity: "ordine", entityId: "—", action: "Riserva rifiutata", detail: `${conflicts.join(", ")} non disponibile (${channel})`, ...actor }));
            return { ok: false, error: "Ricambio non più disponibile", conflicts };
          }
          const { id, partIds } = made;
          push(
            event({ entity: "ordine", entityId: id, action: "Ordine creato", detail: `${channel} · ${made.annunci.join(", ")} · ${partIds.join(", ")}`, ...actor }),
            ...partIds.map((pid) => event({ entity: "ricambio", entityId: pid, action: "Stato: disponibile → riservato", detail: id, ...actor })),
          );
          made.annunci.forEach(touchAnnuncio);
          return { ok: true, value: id };
        },

        // Vendita arrivata da eBay: già pagata, prende tanti pezzi quanti ne sono stati comprati, i più vecchi.
        // Se ne restano meno (venduti nel frattempo altrove) l'ordine si crea lo stesso, segnato da gestire.
        importEbaySale: (v) => {
          const valid =
            !!v &&
            typeof v.orderId === "string" &&
            v.orderId.trim() !== "" &&
            typeof v.sku === "string" &&
            Number.isInteger(v.quantita) &&
            v.quantita >= 1 &&
            v.quantita <= 999 &&
            Number.isFinite(v.prezzoUnitario) &&
            v.prezzoUnitario >= 0;
          if (!valid) return { ok: false, error: "Vendita eBay non valida" };
          const actor: Actor = { user: "Connettore eBay", role: "sistema", device: "Ponte eBay" };
          let dup = undefined as string | undefined;
          let made = undefined as { id: string; partIds: string[]; daGestire?: string } | undefined;
          set((st) => {
            const prev = st.orders.find((o) => o.ebayOrderId === v.orderId);
            if (prev) {
              dup = prev.id;
              return {};
            }
            const a = st.annunci.find((x) => x.id === v.sku);
            const pick = a ? pickForSale(a, st.parts, v.quantita) : { partIds: [], mancano: v.quantita };
            const note = missingNote(pick.mancano);
            const daGestire = a ? note : `annuncio ${v.sku} non trovato${note ? `: ${note}` : ""}`;
            const n = st.counters.order + 1;
            const id = `O-${pad(n)}`;
            const at = now();
            made = { id, partIds: pick.partIds, daGestire };
            const order: Order = {
              id,
              channel: "marketplace",
              delivery: a && !a.spedibile ? "ritiro" : "corriere",
              partIds: pick.partIds,
              amount: Math.round(v.prezzoUnitario * v.quantita * 100) / 100,
              prices: Object.fromEntries(pick.partIds.map((pid) => [pid, v.prezzoUnitario])),
              status: "pagato",
              // Un acquirente non testo (dati strani da eBay) non deve bloccare questa e le vendite dopo
              customer: String(v.acquirente ?? "").trim().slice(0, 120) || "Acquirente eBay",
              paymentRef: `EBAY-${v.orderId}`,
              ebayOrderId: v.orderId,
              daGestire,
              createdAt: at,
              history: [{ at, status: "pagato", note: `Vendita eBay del ${v.at} · ${v.quantita} pz` }],
            };
            return {
              parts: st.parts.map((x) => (pick.partIds.includes(x.id) ? { ...x, status: "venduto" as const } : x)),
              orders: [order, ...st.orders],
              counters: { ...st.counters, order: n },
            };
          });
          if (dup) return { ok: true, value: dup };
          if (!made) return { ok: false, error: "Vendita eBay non importata" };
          const { id, partIds, daGestire } = made;
          push(
            annuncioEvent(v.sku, "Vendita eBay importata", `${id} · ordine eBay ${v.orderId} · ${v.quantita} pz${daGestire ? ` · da gestire: ${daGestire}` : ""}`, actor),
            event({ entity: "ordine", entityId: id, action: "Ordine creato", detail: `marketplace (eBay ${v.orderId}) · ${partIds.join(", ") || "nessun pezzo disponibile"}`, ...actor }),
            ...partIds.map((pid) => event({ entity: "ricambio", entityId: pid, action: "Stato: disponibile → venduto", detail: `${id} · eBay`, ...actor })),
          );
          touchAnnuncio(v.sku);
          return { ok: true, value: id };
        },

        // Esito del ponte eBay per un annuncio. Se nel frattempo l'annuncio è cambiato (quantità, prezzo, titolo,
        // ritiro) rispetto a ciò che è stato inviato, resta da riallineare e riparte al giro dopo.
        setEbayResult: (annuncioId, esito, inviato) => {
          const st0 = get();
          const a = st0.annunci.find((x) => x.id === annuncioId);
          if (!a?.ebay) return;
          const prevListingId = a.ebay.listingId;
          const prevErrore = a.ebay.errore;
          const cambiato =
            quantityOf(a, st0.parts) !== inviato.quantita ||
            onlinePrice(a.price) !== inviato.prezzo ||
            (inviato.attivo !== undefined && inviato.attivo !== (a.ebay.stato !== "ritirato")) ||
            (inviato.titolo !== undefined && inviato.titolo !== a.titolo);
          const ebay = applyEsito(a, esito, inviato, now(), cambiato);
          set((st) => ({ annunci: st.annunci.map((x) => (x.id === annuncioId ? { ...x, ebay } : x)) }));
          if (esito.stato === "errore") {
            if (prevErrore !== ebay.errore) push(annuncioEvent(annuncioId, "Errore eBay", ebay.errore, EBAY_ACTOR));
          } else if (inviato.attivo === false && esito.stato === "ritirato" && !ebay.daRiallineare) {
            push(annuncioEvent(annuncioId, "Ritirato da eBay", undefined, EBAY_ACTOR));
          } else if (!prevListingId && ebay.listingId && esito.stato !== "ritirato") {
            push(annuncioEvent(annuncioId, "Pubblicato su eBay", ebay.listingId, EBAY_ACTOR));
          }
        },

        // Un ordine eBay con "da gestire" è stato sistemato a mano
        markOrderHandled: (orderId) => {
          const o = get().orders.find((x) => x.id === orderId);
          if (!o?.daGestire) return;
          set((st) => ({ orders: st.orders.map((x) => (x.id === orderId ? { ...x, daGestire: undefined } : x)) }));
          push(event({ entity: "ordine", entityId: orderId, action: "Ordine eBay segnato come gestito", detail: o.daGestire }));
        },

        // Riserva atomica: controllo e cambio di stato nello stesso aggiornamento.
        // In produzione: transazione sul database con vincolo sullo stato del pezzo.
        createOrder: (channel, partIds, customer, actor, prices, delivery) => {
          const s = get();
          // Prezzo applicato: quello passato (listino al banco), altrimenti il prezzo del pezzo; online con la commissione dell'8%
          const priceOf = (pid: string) => {
            const base = s.parts.find((x) => x.id === pid)?.price;
            return prices?.[pid] ?? (channel === "banco" ? base : onlinePrice(base));
          };
          const conflicts = partIds.filter((pid) => {
            const p = s.parts.find((x) => x.id === pid);
            // Il negozio vende solo pezzi di un annuncio online sul negozio (non basta che sia online su eBay)
            const shopOff = channel === "negozio" && s.annunci.find((a) => a.id === p?.annuncioId)?.negozio?.stato !== "online";
            return !p || p.status !== "disponibile" || !priceOf(pid) || (channel !== "banco" && listingOf(p, s.annunci) !== "pubblicato") || shopOff;
          });
          if (conflicts.length) {
            push(event({ entity: "ordine", entityId: "—", action: "Riserva rifiutata", detail: `${conflicts.join(", ")} non disponibile (${channel})`, ...actor }));
            return { ok: false, error: "Ricambio non più disponibile", conflicts };
          }
          const n = s.counters.order + 1;
          const id = `O-${pad(n)}`;
          const amount = Math.round(partIds.reduce((a, pid) => a + (priceOf(pid) ?? 0), 0) * 100) / 100;
          const at = now();
          set((st) => ({
            parts: st.parts.map((x) => (partIds.includes(x.id) ? { ...x, status: "riservato" } : x)),
            orders: [
              {
                id,
                channel,
                delivery,
                partIds,
                amount,
                prices: Object.fromEntries(partIds.map((pid) => [pid, priceOf(pid) ?? 0])),
                status: "in attesa di pagamento",
                customer,
                createdAt: at,
                history: [{ at, status: "in attesa di pagamento" }],
              },
              ...st.orders,
            ],
            counters: { ...st.counters, order: n },
          }));
          push(
            event({ entity: "ordine", entityId: id, action: "Ordine creato", detail: `${channel} · ${partIds.join(", ")}`, ...actor }),
            ...partIds.map((pid) => event({ entity: "ricambio", entityId: pid, action: "Stato: disponibile → riservato", detail: id, ...actor })),
          );
          settle(partIds);
          return { ok: true, value: id };
        },

        payOrder: (orderId, success, actor) => {
          const o = get().orders.find((x) => x.id === orderId);
          if (!o || o.status !== "in attesa di pagamento") return;
          const at = now();
          const status = success ? "pagato" : "pagamento fallito";
          set((s) => ({
            orders: s.orders.map((x) => (x.id === orderId ? { ...x, status, paymentRef: success ? `PAY-DEMO-${orderId.slice(2)}` : undefined, history: [...x.history, { at, status, note: success ? "Conferma dal provider (simulata)" : "Rifiuto dal provider (simulato)" }] } : x)),
            // Venduto: esce dal negozio; pagamento fallito: torna disponibile
            parts: s.parts.map((x) =>
              o.partIds.includes(x.id) ? { ...x, status: success ? "venduto" : "disponibile" } : x,
            ),
          }));
          push(
            event({ entity: "ordine", entityId: orderId, action: success ? "Pagamento confermato" : "Pagamento fallito", detail: success ? "Webhook provider (simulato)" : "Disponibilità ripristinata", ...actor }),
            ...o.partIds.map((pid) => event({ entity: "ricambio", entityId: pid, action: success ? "Stato: riservato → venduto" : "Stato: riservato → disponibile", detail: orderId, ...actor })),
          );
          settle(o.partIds);
        },

        cancelOrder: (orderId, reason) => {
          const o = get().orders.find((x) => x.id === orderId);
          // Si annulla solo un ordine non ancora spedito o consegnato (dopo si gestisce come reso)
          if (!o || !["in attesa di pagamento", "pagamento fallito", "pagato"].includes(o.status)) return;
          const wasPaid = o.status === "pagato";
          const touchesParts = o.status !== "pagamento fallito"; // con pagamento fallito i pezzi sono già tornati disponibili
          const at = now();
          set((s) => ({
            orders: s.orders.map((x) => (x.id === orderId ? { ...x, status: "annullato", history: [...x.history, { at, status: "annullato", note: reason }] } : x)),
            parts: s.parts.map((x) => (touchesParts && o.partIds.includes(x.id) && (x.status === "riservato" || x.status === "venduto") ? { ...x, status: "disponibile" } : x)),
          }));
          push(event({ entity: "ordine", entityId: orderId, action: "Ordine annullato", detail: `${reason ?? ""}${wasPaid ? " · rimborso da gestire" : ""}` }));
          if (touchesParts) settle(o.partIds);
        },

        shipOrder: (orderId) => {
          const at = now();
          const o = get().orders.find((x) => x.id === orderId);
          if (!o || o.status !== "pagato") return;
          const status = o.channel === "banco" || o.delivery === "ritiro" ? "consegnato" : "spedito";
          // Consegnato o spedito: i pezzi non sono più sullo scaffale, anche se nessuno ha scansionato il prelievo
          const stillShelved = get().parts.filter((x) => o.partIds.includes(x.id) && x.location);
          set((s) => ({
            orders: s.orders.map((x) => (x.id === orderId ? { ...x, status, history: [...x.history, { at, status }] } : x)),
            parts: s.parts.map((x) => (o.partIds.includes(x.id) && x.location ? { ...x, location: undefined } : x)),
          }));
          push(
            event({ entity: "ordine", entityId: orderId, action: status === "spedito" ? "Ordine spedito" : o.channel === "banco" ? "Consegnato al banco" : "Ritirato in sede" }),
            ...stillShelved.map((x) => event({ entity: "ricambio", entityId: x.id, action: "Uscito dal magazzino", detail: `${locToString(x.location)} · ${orderId}` })),
          );
        },

        returnOrder: (orderId) => {
          const o = get().orders.find((x) => x.id === orderId);
          if (!o || (o.status !== "spedito" && o.status !== "consegnato")) return;
          const at = now();
          set((s) => ({
            orders: s.orders.map((x) => (x.id === orderId ? { ...x, status: "reso", history: [...x.history, { at, status: "reso", note: "Ricambio rientrato: da ricontrollare" }] } : x)),
            parts: s.parts.map((x) => (o.partIds.includes(x.id) ? { ...x, status: "bozza" } : x)),
          }));
          const inv = get().docs.find((d) => d.orderId === orderId && (d.type === "fattura" || d.type === "documento commerciale"));
          if (inv) newDoc({ type: "nota di credito", customer: inv.customer, lines: inv.lines.map((l) => ({ ...l, price: -l.price })), total: -inv.total, orderId, refDocId: inv.id, status: inv.type === "fattura" ? "inviata allo SdI" : "emesso" });
          push(
            event({ entity: "ordine", entityId: orderId, action: "Reso registrato" }),
            ...o.partIds.map((pid) => event({ entity: "ricambio", entityId: pid, action: "Stato: venduto → bozza", detail: `Rientro da reso ${orderId}, da ricontrollare` })),
          );
          // Il reso tiene il suo annuncio ma non conta finché non torna disponibile e passa i controlli
          settle(o.partIds);
        },

        setRule: (typeId, min, max) => {
          set((s) => ({ rules: s.rules.map((r) => (r.typeId === typeId ? { ...r, min, max } : r)) }));
          push(event({ entity: "regola", entityId: typeId, action: "Soglia scorta modificata", detail: `min ${min} · max ${max}` }));
        },

        saveBonifica: (vehicleId, items, weightKg) => {
          const v0 = get().vehicles.find((x) => x.id === vehicleId);
          if (!v0 || v0.bonifica) return 0;
          const at = now();
          let carico = get().wasteMoves.find((m) => m.origin === vehicleId && m.causale === "*T");
          const intake = carico ? [] : movesForIntake({ ...v0, weightKg: v0.weightKg ?? (weightKg || undefined) }, v0.intakeAt);
          // Pesata fatta solo ora (alla bonifica): completa il carico d'ingresso ancora in bozza
          if (carico && isDraft(carico) && !v0.weightKg && weightKg > 0) {
            get().completeDraft(carico.id, { kg: weightKg, pesoPesa: true });
            carico = get().wasteMoves.find((m) => m.id === carico!.id);
          }
          const v = get().vehicles.find((x) => x.id === vehicleId)!;
          const withWeight = { ...v, weightKg: v.weightKg ?? (weightKg || undefined) };
          // Lo scarico interno usa il peso registrato all'ingresso, così carico e scarico del veicolo coincidono
          const { moves, residualKg } = movesForBonifica(carico ? { ...withWeight, weightKg: carico.kg } : withWeight, items, at, carico?.id);
          set((s) => ({ vehicles: s.vehicles.map((x) => (x.id === vehicleId ? { ...withWeight, bonifica: { at, by: ROLE_USER[s.role].user, items, residualKg } } : x)) }));
          addMoves([...intake, ...moves]);
          push(event({ entity: "veicolo", entityId: vehicleId, action: "Bonifica registrata", detail: `${intake.length + moves.length} movimenti nel registro rifiuti · pesi dei componenti stimati per modello` }));
          return intake.length + moves.length;
        },

        completeDraft: (id, patch) => {
          const m = get().wasteMoves.find((x) => x.id === id);
          if (!m) return { ok: false, error: "Registrazione non trovata" };
          if (!isDraft(m)) return { ok: false, error: `La registrazione n. ${m.numero} è già numerata: si corregge con una rettifica` };
          const nome = patch.produttoreNome?.trim() || m.produttore?.nome;
          const cf = patch.produttoreCf !== undefined ? patch.produttoreCf.trim().toUpperCase() : m.produttore?.cf;
          const next: WasteMove = {
            ...m,
            ...(nome || cf ? { produttore: { nome: nome ?? "", cf } } : {}),
            ...(patch.certificato ? { certificato: patch.certificato } : {}),
            ...(patch.kg !== undefined ? { kg: patch.kg } : {}),
            ...(patch.pesoPesa !== undefined ? { pesoPesa: patch.pesoPesa } : {}),
          };
          const at = now();
          const by = ROLE_USER[get().role].user;
          const ready = missingFields(next, get().wasteMoves).length === 0;
          set((s) => {
            let all = s.wasteMoves.map((x) => (x.id === id ? { ...next, ...(ready ? { numero: nextRegisterNumber(s.wasteMoves, at), registeredAt: at, by } : {}) } : x));
            // Registrato il carico d'ingresso, si registrano anche gli scarichi interni che lo aspettavano, con lo stesso peso
            if (ready && next.causale === "*T")
              for (const d of all.filter((x) => isDraft(x) && x.causale === "I" && x.caricoRif === id)) {
                const fixed = { ...d, kg: next.kg };
                if (missingFields(fixed, all).length === 0) all = all.map((x) => (x.id === d.id ? { ...fixed, numero: nextRegisterNumber(all, at), registeredAt: at, by } : x));
              }
            // Il peso della pesa diventa il peso del veicolo: la bonifica scaricherà lo stesso peso
            const vehicles = patch.kg !== undefined && next.causale === "*T" ? s.vehicles.map((v) => (v.id === m.origin ? { ...v, weightKg: patch.kg } : v)) : s.vehicles;
            return { wasteMoves: all, vehicles };
          });
          push(event({ entity: "sistema", entityId: id, action: ready ? "Registrazione completata" : "Bozza aggiornata", detail: `${m.eer} · ${next.kg} kg · ${m.note ?? ""}` }));
          return { ok: true, value: ready };
        },

        rectifyMove: (id, kg, motivo) => {
          const m = get().wasteMoves.find((x) => x.id === id);
          if (!m || isDraft(m)) return { ok: false, error: "Si rettificano solo le registrazioni numerate" };
          if (!(kg > 0)) return { ok: false, error: "Scrivi i kg corretti" };
          if (!motivo.trim()) return { ok: false, error: "Scrivi il motivo della rettifica" };
          const [newId] = addMoves([{ at: now(), kind: m.kind, eer: m.eer, kg, origin: m.origin, note: `Rettifica della n. ${m.numero}`, rentri: "da trasmettere", causale: "RETT", rettificaDi: id, motivo: motivo.trim(), statoFisico: m.statoFisico, hp: m.hp, operazione: m.operazione }]);
          push(event({ entity: "sistema", entityId: newId, action: "Rettifica registrata", detail: `n. ${m.numero}: ${m.kg} → ${kg} kg · ${motivo.trim()}` }));
          return { ok: true, value: newId };
        },

        cancelMove: (id, motivo) => {
          const m = get().wasteMoves.find((x) => x.id === id);
          if (!m || isDraft(m)) return { ok: false, error: "Si annullano solo le registrazioni numerate" };
          if (!motivo.trim()) return { ok: false, error: "Scrivi il motivo dell'annullamento" };
          if (get().wasteMoves.some((x) => x.annullaDi === id)) return { ok: false, error: `La registrazione n. ${m.numero} è già annullata` };
          const [newId] = addMoves([{ at: now(), kind: m.kind, eer: m.eer, kg: 0, origin: m.origin, note: `Annullamento della n. ${m.numero}`, rentri: "da trasmettere", causale: "ANN", annullaDi: id, motivo: motivo.trim() }]);
          push(event({ entity: "sistema", entityId: newId, action: "Annullamento registrato", detail: `n. ${m.numero} · ${motivo.trim()}` }));
          return { ok: true, value: newId };
        },

        transmitPeriod: (key) => {
          const p = periodsOf(get().wasteMoves, get().firs).find((x) => x.key === key);
          if (!p || !canTransmit(p)) return { ok: false, error: p?.drafts ? `Ci sono ${p.drafts} bozze da completare` : "Questo periodo non si può trasmettere" };
          const at = now();
          const ricevuta = `RENTRI-SIM-${key}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;
          const ids = new Set(p.moves.map((m) => m.id));
          set((s) => ({ wasteMoves: s.wasteMoves.map((m) => (ids.has(m.id) ? { ...m, rentri: "trasmesso", rentriAt: at, rentriRicevuta: ricevuta } : m)) }));
          push(event({ entity: "sistema", entityId: "RENTRI", action: `Periodo di ${monthLabel(key)} trasmesso al RENTRI`, detail: `${p.moves.length} registrazioni · ricevuta ${ricevuta} (trasmissione simulata)` }));
          return { ok: true, value: ricevuta };
        },

        receiveFir: (f) => {
          if (f.numero && firNumberTaken(get().firs, f.numero)) return { ok: false, error: `Il formulario ${f.numero} è già registrato` };
          const n = get().counters.fir + 1;
          const id = `F-${pad(n)}`;
          const at = now();
          const by = ROLE_USER[get().role].user;
          const nome = (sid?: string) => get().soggetti.find((x) => x.id === sid)?.nome;
          const fir: Fir = { ...f, id, at, destinatario: nome(f.destinatarioId), trasportatore: nome(f.trasportatoreId), status: "da firmare", history: [{ at, status: "da firmare", by }] };
          set((s) => ({ firs: [fir, ...s.firs], counters: { ...s.counters, fir: n } }));
          push(event({ entity: "sistema", entityId: id, action: "Formulario ricevuto", detail: `${f.numero} · ${f.eer} · ${f.kg} kg → ${fir.destinatario ?? ""}` }));
          return { ok: true, value: id };
        },

        signFir: (id) => {
          const f = get().firs.find((x) => x.id === id);
          if (!f) return { ok: false, error: "Formulario non trovato" };
          if (f.status !== "da firmare") return { ok: false, error: "Formulario già firmato" };
          const stock = stockByEer(get().wasteMoves).find((x) => x.code === f.eer)?.kg ?? 0;
          // Se parte tutto il contenitore, la pesata è il peso vero: la differenza con la giacenza stimata si registra da sola
          if (!f.svuota && f.kg > stock + 0.05) {
            push(event({ entity: "sistema", entityId: id, action: "Firma bloccata", detail: `${f.kg} kg richiesti, ${stock} kg in giacenza` }));
            return { ok: false, error: `In giacenza ci sono solo ${stock} kg di ${f.eer}: controlla la quantità del formulario, oppure indica che parte tutta la giacenza` };
          }
          const at = now();
          const dest = get().soggetti.find((x) => x.id === f.destinatarioId);
          const e = eerByCode(f.eer);
          const nome = f.numero ?? id;
          const diff = f.svuota ? differenzaPesata(stock, f.kg) : 0;
          set((s) => ({ firs: s.firs.map((x) => (x.id === id ? { ...x, status: "firmato", history: [...x.history, { at, status: "firmato", by: ROLE_USER[s.role].user }] } : x)) }));
          addMoves([
            ...(diff
              ? [{ at, kind: diff > 0 ? ("carico" as const) : ("scarico" as const), eer: f.eer, kg: Math.abs(diff), origin: id, note: `Differenza tra giacenza stimata (${stock} kg) e pesata del formulario ${nome} (${f.kg} kg)`, rentri: "da trasmettere" as const, causale: "DIFF" as const, fir: id, statoFisico: e?.stato, hp: e?.hp }]
              : []),
            // Con la firma il rifiuto lascia l'impianto: scarico "a terzi" nel registro, legato al formulario
            { at, kind: "scarico", eer: f.eer, kg: f.kg, origin: id, note: `Uscita verso ${f.destinatario ?? "destinatario"} · formulario ${nome}`, rentri: "da trasmettere", causale: "aT", fir: id, operazione: dest?.operazione ?? "R13", statoFisico: e?.stato, hp: e?.hp },
          ]);
          push(event({ entity: "sistema", entityId: id, action: "Formulario firmato", detail: `${f.numero ?? ""} · ${f.eer} · ${f.kg} kg${diff ? ` · differenza di pesata ${diff > 0 ? "+" : ""}${diff} kg` : ""}` }));
          return { ok: true, value: undefined };
        },

        setFirPhotos: (id, foto) => {
          const f = get().firs.find((x) => x.id === id);
          if (!f) return;
          const before = f.foto?.length ?? 0;
          set((s) => ({ firs: s.firs.map((x) => (x.id === id ? { ...x, foto } : x)) }));
          push(event({ entity: "sistema", entityId: id, action: foto.length > before ? "Foto del formulario aggiunta" : "Foto del formulario rimossa", detail: `${f.numero ?? id} · ${foto.length} foto` }));
        },

        confirmMove: (id) => {
          const m = get().wasteMoves.find((x) => x.id === id);
          if (!m) return;
          const by = ROLE_USER[get().role].user;
          set((s) => ({ wasteMoves: s.wasteMoves.map((x) => (x.id === id ? { ...x, verificato: { at: now(), by } } : x)) }));
          push(event({ entity: "sistema", entityId: id, action: "Registrazione controllata", detail: `n. ${m.numero ?? "bozza"} · ${m.note ?? ""}` }));
        },

        setFirOutcome: (id, esito, kgAccettati, arrivoAt) => {
          const f = get().firs.find((x) => x.id === id);
          if (!f) return { ok: false, error: "Formulario non trovato" };
          if (f.status !== "firmato" && f.status !== "accettato") return { ok: false, error: "Prima va firmato" };
          if (esito !== "respinto" && !(kgAccettati > 0)) return { ok: false, error: "Scrivi i kg accettati" };
          const kg = esito === "accettato" ? f.kg : esito === "respinto" ? 0 : kgAccettati;
          set((s) => ({ firs: s.firs.map((x) => (x.id === id ? { ...x, status: "accettato", esito, kgAccettati: kg, arrivoAt, history: [...x.history, { at: now(), status: "accettato", by: f.destinatario ?? "Destinatario" }] } : x)) }));
          push(event({ entity: "sistema", entityId: id, action: `Esito del destinatario: ${esito}`, detail: `${f.numero ?? ""} · ${kg} kg su ${f.kg}` }));
          return { ok: true, value: undefined };
        },

        saveSoggetto: (sg) => {
          set((s) => ({ soggetti: s.soggetti.some((x) => x.id === sg.id) ? s.soggetti.map((x) => (x.id === sg.id ? sg : x)) : [...s.soggetti, sg] }));
          push(event({ entity: "sistema", entityId: sg.id, action: "Anagrafica soggetto salvata", detail: `${sg.nome} · ${sg.ruolo}` }));
        },

        createQuote: (partIds, customer, prices, listino) => {
          const lines = linesOf(partIds, prices);
          return newDoc({ type: "preventivo", customer, lines, total: lines.reduce((a, l) => a + l.price, 0), listino, status: "aperto" });
        },

        issueDoc: (orderId, type, customer, prices, listino) => {
          const o = get().orders.find((x) => x.id === orderId);
          if (!o) return "";
          // Il documento riprende i prezzi dell'ordine (listino compreso); un solo documento per ordine
          if (get().docs.some((d) => d.orderId === orderId && (d.type === "fattura" || d.type === "documento commerciale"))) return "";
          const lines = linesOf(o.partIds, prices ?? o.prices ?? (o.partIds.length === 1 ? { [o.partIds[0]]: o.amount } : undefined));
          return newDoc({ type, customer, lines, total: Math.round(lines.reduce((a, l) => a + l.price, 0) * 100) / 100, orderId, listino, status: type === "fattura" ? "inviata allo SdI" : "emesso" });
        },

        convertQuote: (docId, type) => {
          const q = get().docs.find((d) => d.id === docId && d.type === "preventivo" && d.status === "aperto");
          if (!q) return { ok: false, error: "Preventivo non trovato o già convertito" };
          const ids = q.lines.map((l) => l.partId!).filter(Boolean);
          const prices = Object.fromEntries(q.lines.filter((l) => l.partId).map((l) => [l.partId!, l.price]));
          const r = get().createOrder("banco", ids, q.customer.name, undefined, prices);
          if (!r.ok) return r;
          get().payOrder(r.value, true);
          const id = get().issueDoc(r.value, type, q.customer, prices, q.listino);
          set((s) => ({ docs: s.docs.map((d) => (d.id === docId ? { ...d, status: "convertito", orderId: r.value } : d)) }));
          return { ok: true, value: id };
        },

        cancelQuote: (docId) => {
          set((s) => ({ docs: s.docs.map((d) => (d.id === docId && d.type === "preventivo" && d.status === "aperto" ? { ...d, status: "annullato" } : d)) }));
          push(event({ entity: "ordine", entityId: docId, action: "Preventivo annullato" }));
        },

        saveListini: (listini) => {
          set({ listini });
          push(event({ entity: "regola", entityId: "listini", action: "Listini aggiornati", detail: listini.map((l) => `${l.name} ${l.pct > 0 ? "+" : ""}${l.pct}%`).join(" · ") }));
        },

        addWarehouse: (w) => {
          set((s) => ({ warehouses: [...s.warehouses, w] }));
          push(event({ entity: "regola", entityId: `MAG-${w.id}`, action: "Magazzino creato", detail: w.corsie ? `${w.name} · ${w.corsie} corsie × ${w.scaffali} scaffali × ${w.ripiani.length} ripiani` : `${w.name} · ubicazioni libere` }));
        },

        closeCount: (c) => {
          const n = get().counters.inventory + 1;
          const id = `I-${pad(n)}`;
          const at = now();
          const by = ROLE_USER[get().role].user;
          set((s) => ({
            inventory: [...s.inventory, { ...c, id, at, by }],
            counters: { ...s.counters, inventory: n },
            // Chi manca all'appello resta segnalato finché non viene ritrovato
            parts: s.parts.map((p) =>
              c.missing.includes(p.id) ? { ...p, missingSince: p.missingSince ?? at } : c.found.includes(p.id) && p.missingSince ? { ...p, missingSince: undefined } : p,
            ),
          }));
          push(event({ entity: "ricambio", entityId: id, action: "Ripiano contato", detail: `${c.mag}/${c.corsia}-${c.scaffale}-${c.ripiano} · ${c.found.length} trovati · ${c.missing.length} mancanti · ${c.added.length} nuovi` }));
          return id;
        },

        reset: () => set(initial()),
      };
    },
    {
      name: STORE_SCHEMA,
      storage: createJSONStorage(() => deviceStorage),
      skipHydration: true,
    },
  ),
);

export { buildAnnuncio };

// Stato del pezzo sul negozio, ricavato dal suo annuncio
export const useListing = (p: Part): ListingStatus => useStore((s) => listingOf(p, s.annunci));

export const useHydrated = () => {
  // gestito da <Hydrator/>
  return useStore.persist?.hasHydrated?.() ?? false;
};

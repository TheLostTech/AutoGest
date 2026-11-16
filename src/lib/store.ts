"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { buildSeed, pad } from "./seed";
import { locToString } from "./warehouse";
import type {
  AuditEvent,
  Channel,
  Location,
  Order,
  Part,
  PartStatus,
  Role,
  StockRule,
  Vehicle,
} from "./types";
import { publishChecks } from "./logic";

export const ROLE_USER: Record<Role, { user: string; device: string; label: string }> = {
  accettazione: { user: "Giulia (accettazione)", device: "PC ufficio", label: "Accettazione" },
  smontatore: { user: "Marco (smontaggio)", device: "Smartphone campo 1", label: "Smontatore" },
  magazziniere: { user: "Paolo (magazzino)", device: "Smartphone magazzino", label: "Magazziniere" },
  responsabile: { user: "Sara (responsabile)", device: "PC ufficio", label: "Responsabile" },
  vendite: { user: "Anna (vendite)", device: "PC banco", label: "Vendite" },
};

interface Counters {
  vehicle: number;
  part: number;
  order: number;
  event: number;
}

interface State {
  role: Role;
  vehicles: Vehicle[];
  parts: Part[];
  orders: Order[];
  audit: AuditEvent[];
  rules: StockRule[];
  counters: Counters;
  activeVehicleId?: string;
}

type Result<T = undefined> = { ok: true; value: T } | { ok: false; error: string; conflicts?: string[] };

interface Actions {
  setRole: (r: Role) => void;
  setActiveVehicle: (id?: string) => void;
  addVehicle: (v: Omit<Vehicle, "id" | "createdBy" | "intakeAt">) => string;
  updateVehicle: (id: string, patch: Partial<Vehicle>, action: string, detail?: string) => void;
  addPart: (p: Omit<Part, "id" | "createdAt" | "createdBy" | "labelPrints" | "listing">) => string;
  updatePart: (id: string, patch: Partial<Part>, action: string, detail?: string) => void;
  printLabel: (id: string) => void;
  setLocation: (id: string, loc: Location) => void;
  setPartStatus: (id: string, status: PartStatus, reason?: string) => void;
  publish: (id: string) => Result;
  unpublish: (id: string) => void;
  createOrder: (channel: Channel, partIds: string[], customer: string, actor?: { user: string; role: AuditEvent["role"]; device: string }) => Result<string>;
  payOrder: (orderId: string, success: boolean) => void;
  cancelOrder: (orderId: string, reason?: string) => void;
  shipOrder: (orderId: string) => void;
  returnOrder: (orderId: string) => void;
  setRule: (typeId: string, min: number, max: number) => void;
  log: (e: Omit<AuditEvent, "id" | "at" | "user" | "role" | "device"> & Partial<Pick<AuditEvent, "user" | "role" | "device">>) => void;
  reset: () => void;
}

const now = () => new Date().toISOString();

function initial(): State {
  const s = buildSeed();
  return {
    role: "smontatore",
    vehicles: s.vehicles,
    parts: s.parts,
    orders: s.orders,
    audit: s.audit,
    rules: s.rules,
    counters: s.counters,
    activeVehicleId: "V-000118",
  };
}

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
          return id;
        },

        updateVehicle: (id, patch, action, detail) => {
          set((s) => ({ vehicles: s.vehicles.map((v) => (v.id === id ? { ...v, ...patch } : v)) }));
          push(event({ entity: "veicolo", entityId: id, action, detail }));
        },

        addPart: (p) => {
          const n = get().counters.part + 1;
          const id = `R-${pad(n)}`;
          const part: Part = { ...p, id, createdAt: now(), createdBy: ROLE_USER[get().role].user, labelPrints: 0, listing: "non pubblicato" };
          set((s) => ({ parts: [part, ...s.parts], counters: { ...s.counters, part: n } }));
          push(event({ entity: "ricambio", entityId: id, action: "Ricambio catalogato", detail: `${p.description} da ${p.vehicleId}${p.aiSuggested ? ` · suggerimento IA ${p.aiSuggested.accepted ? "confermato" : "corretto"}` : ""}` }));
          return id;
        },

        updatePart: (id, patch, action, detail) => {
          set((s) => ({ parts: s.parts.map((p) => (p.id === id ? { ...p, ...patch } : p)) }));
          push(event({ entity: "ricambio", entityId: id, action, detail }));
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
          set((s) => ({ parts: s.parts.map((x) => (x.id === id ? { ...x, location: loc } : x)) }));
          push(event({ entity: "ricambio", entityId: id, action: p?.location ? "Ricambio spostato" : "Posizione assegnata", detail: p?.location ? `${locToString(p.location)} → ${locToString(loc)}` : locToString(loc) }));
        },

        setPartStatus: (id, status, reason) => {
          const p = get().parts.find((x) => x.id === id);
          if (!p) return;
          const listing = status === "disponibile" ? p.listing : p.listing === "pubblicato" && status !== "riservato" && status !== "venduto" ? "ritirato" : p.listing;
          set((s) => ({ parts: s.parts.map((x) => (x.id === id ? { ...x, status, listing } : x)) }));
          push(event({ entity: "ricambio", entityId: id, action: `Stato: ${p.status} → ${status}`, detail: reason }));
        },

        publish: (id) => {
          const s = get();
          const p = s.parts.find((x) => x.id === id);
          if (!p) return { ok: false, error: "Ricambio non trovato" };
          const v = s.vehicles.find((x) => x.id === p.vehicleId);
          const missing = publishChecks(p, v).filter((c) => !c.ok && c.blocking);
          if (missing.length) return { ok: false, error: "Scheda incompleta", conflicts: missing.map((m) => m.label) };
          set((st) => ({ parts: st.parts.map((x) => (x.id === id ? { ...x, listing: "pubblicato" } : x)) }));
          push(event({ entity: "ricambio", entityId: id, action: "Pubblicato sul negozio" }));
          return { ok: true, value: undefined };
        },

        unpublish: (id) => {
          set((s) => ({ parts: s.parts.map((x) => (x.id === id ? { ...x, listing: "ritirato" } : x)) }));
          push(event({ entity: "ricambio", entityId: id, action: "Ritirato dal negozio" }));
        },

        // Riserva atomica: controllo e cambio di stato nello stesso aggiornamento.
        // In produzione: transazione sul database con vincolo sullo stato del pezzo.
        createOrder: (channel, partIds, customer, actor) => {
          const s = get();
          const conflicts = partIds.filter((pid) => {
            const p = s.parts.find((x) => x.id === pid);
            return !p || p.status !== "disponibile" || (channel !== "banco" && p.listing !== "pubblicato");
          });
          if (conflicts.length) {
            push(event({ entity: "ordine", entityId: "—", action: "Riserva rifiutata", detail: `${conflicts.join(", ")} non disponibile (${channel})`, ...actor }));
            return { ok: false, error: "Ricambio non più disponibile", conflicts };
          }
          const n = s.counters.order + 1;
          const id = `O-${pad(n)}`;
          const amount = partIds.reduce((a, pid) => a + (s.parts.find((x) => x.id === pid)?.price ?? 0), 0);
          const at = now();
          set((st) => ({
            parts: st.parts.map((x) => (partIds.includes(x.id) ? { ...x, status: "riservato" } : x)),
            orders: [{ id, channel, partIds, amount, status: "in attesa di pagamento", customer, createdAt: at, history: [{ at, status: "in attesa di pagamento" }] }, ...st.orders],
            counters: { ...st.counters, order: n },
          }));
          push(
            event({ entity: "ordine", entityId: id, action: "Ordine creato", detail: `${channel} · ${partIds.join(", ")}`, ...actor }),
            ...partIds.map((pid) => event({ entity: "ricambio", entityId: pid, action: "Stato: disponibile → riservato", detail: id, ...actor })),
          );
          return { ok: true, value: id };
        },

        payOrder: (orderId, success) => {
          const o = get().orders.find((x) => x.id === orderId);
          if (!o || o.status !== "in attesa di pagamento") return;
          const at = now();
          const status = success ? "pagato" : "pagamento fallito";
          set((s) => ({
            orders: s.orders.map((x) => (x.id === orderId ? { ...x, status, paymentRef: success ? `PAY-DEMO-${orderId.slice(2)}` : undefined, history: [...x.history, { at, status, note: success ? "Conferma dal provider (simulata)" : "Rifiuto dal provider (simulato)" }] } : x)),
            parts: s.parts.map((x) => (o.partIds.includes(x.id) ? { ...x, status: success ? "venduto" : "disponibile" } : x)),
          }));
          push(
            event({ entity: "ordine", entityId: orderId, action: success ? "Pagamento confermato" : "Pagamento fallito", detail: success ? "Webhook provider (simulato)" : "Disponibilità ripristinata" }),
            ...o.partIds.map((pid) => event({ entity: "ricambio", entityId: pid, action: success ? "Stato: riservato → venduto" : "Stato: riservato → disponibile", detail: orderId })),
          );
        },

        cancelOrder: (orderId, reason) => {
          const o = get().orders.find((x) => x.id === orderId);
          if (!o || o.status === "annullato" || o.status === "reso") return;
          const wasPaid = o.status !== "in attesa di pagamento" && o.status !== "pagamento fallito";
          const at = now();
          set((s) => ({
            orders: s.orders.map((x) => (x.id === orderId ? { ...x, status: "annullato", history: [...x.history, { at, status: "annullato", note: reason }] } : x)),
            parts: s.parts.map((x) => (o.partIds.includes(x.id) && (x.status === "riservato" || x.status === "venduto") ? { ...x, status: "disponibile" } : x)),
          }));
          push(event({ entity: "ordine", entityId: orderId, action: "Ordine annullato", detail: `${reason ?? ""}${wasPaid ? " · rimborso da gestire" : ""}` }));
        },

        shipOrder: (orderId) => {
          const at = now();
          const o = get().orders.find((x) => x.id === orderId);
          const status = o?.channel === "banco" ? "consegnato" : "spedito";
          set((s) => ({ orders: s.orders.map((x) => (x.id === orderId ? { ...x, status, history: [...x.history, { at, status }] } : x)) }));
          push(event({ entity: "ordine", entityId: orderId, action: status === "spedito" ? "Ordine spedito" : "Consegnato al banco" }));
        },

        returnOrder: (orderId) => {
          const o = get().orders.find((x) => x.id === orderId);
          if (!o) return;
          const at = now();
          set((s) => ({
            orders: s.orders.map((x) => (x.id === orderId ? { ...x, status: "reso", history: [...x.history, { at, status: "reso", note: "Ricambio rientrato: da ricontrollare" }] } : x)),
            parts: s.parts.map((x) => (o.partIds.includes(x.id) ? { ...x, status: "bozza", listing: "ritirato" } : x)),
          }));
          push(
            event({ entity: "ordine", entityId: orderId, action: "Reso registrato" }),
            ...o.partIds.map((pid) => event({ entity: "ricambio", entityId: pid, action: "Stato: venduto → bozza", detail: `Rientro da reso ${orderId}, da ricontrollare` })),
          );
        },

        setRule: (typeId, min, max) => {
          set((s) => ({ rules: s.rules.map((r) => (r.typeId === typeId ? { ...r, min, max } : r)) }));
          push(event({ entity: "regola", entityId: typeId, action: "Soglia scorta modificata", detail: `min ${min} · max ${max}` }));
        },

        reset: () => set(initial()),
      };
    },
    {
      name: "gestionale-demolizione-demo-v4",
      storage: createJSONStorage(() => localStorage),
      skipHydration: true,
    },
  ),
);

export const useHydrated = () => {
  // gestito da <Hydrator/>
  return useStore.persist?.hasHydrated?.() ?? false;
};

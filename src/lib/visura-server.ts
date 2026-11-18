// Visura PRA tramite Openapi DocuEngine ("PRA License Plate Report"). Solo server: il token non va al browser.
// La visura è asincrona: si crea la richiesta, Openapi la evade entro 24 ore lavorative e restituisce un PDF
// (intestatario, ipoteche, fermi, dati tecnici). Non ci sono dati strutturati: l'esito lo registra l'ufficio leggendo il PDF.
// Documentazione: https://console.openapi.com/apis/docuengine/documentation · costi e note in docs/INTEGRAZIONI.md.
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { leggiValori } from "@/lib/collegamenti-server";
import { cartellaAzienda } from "@/lib/server-data";

export type ModoVisura = "Simulato" | "Sandbox" | "Produzione";
export type TipoVeicolo = "AUTOVEICOLO" | "MOTOVEICOLO" | "RIMORCHIO";
export const TIPI_VEICOLO: TipoVeicolo[] = ["AUTOVEICOLO", "MOTOVEICOLO", "RIMORCHIO"];

const BASE = { Sandbox: "https://test.docuengine.openapi.com", Produzione: "https://docuengine.openapi.com" };
// Id del documento nell'elenco /documents di Openapi; si cerca per nome e, se non si trova, si usa questo
const DOCUMENTO_PRA = "67d066772cbb7e30d3d93e33";
// Ogni azienda ha le sue visure: aziende/<id>/visure/ (mai una cartella comune a tutte)
const cartellaVisure = (aziendaId: string) => path.join(cartellaAzienda(aziendaId), "visure");
const MAX_PDF = 10 * 1024 * 1024;

export class ErroreVisura extends Error {
  constructor(message: string, readonly status = 502) {
    super(message);
  }
}

interface Cred {
  modo: Exclude<ModoVisura, "Simulato">;
  base: string;
  token: string;
}

/** Credenziali da Impostazioni → Collegamenti → Openapi. Senza token o senza "Visura PRA" tra i servizi: simulata. */
export async function credenziali(aziendaId: string): Promise<Cred | undefined> {
  const v = await leggiValori(aziendaId, "openapi");
  const token = typeof v.token === "string" ? v.token.trim() : "";
  const servizi = Array.isArray(v.servizi) ? v.servizi : [];
  if (!token || !servizi.includes("Visura PRA")) return undefined;
  const modo = v.ambiente === "Produzione" ? "Produzione" : "Sandbox";
  // OPENAPI_DOCUENGINE_URL serve solo per le prove con un server finto
  return { modo, token, base: process.env.OPENAPI_DOCUENGINE_URL || BASE[modo] };
}

interface Busta<T> {
  success?: boolean;
  message?: string;
  data?: T;
}

async function chiama<T>(c: Cred, metodo: "GET" | "POST", percorso: string, corpo?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(c.base + percorso, {
      method: metodo,
      headers: { Authorization: `Bearer ${c.token}`, Accept: "application/json", ...(corpo ? { "Content-Type": "application/json" } : {}) },
      body: corpo ? JSON.stringify(corpo) : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });
  } catch {
    throw new ErroreVisura("Openapi non risponde: riprova tra poco.");
  }
  const b = (await res.json().catch(() => ({}))) as Busta<T>;
  if (res.status === 401 || res.status === 403) throw new ErroreVisura("Openapi rifiuta il token: controllalo in Impostazioni → Collegamenti.");
  if (res.status === 402) throw new ErroreVisura("Credito Openapi esaurito: ricarica dalla console.");
  if (!res.ok || b.success === false || b.data === undefined) throw new ErroreVisura(`Openapi: ${b.message || `errore ${res.status}`}`);
  return b.data;
}

let documentoCache: { base: string; id: string } | undefined;

async function idDocumento(c: Cred) {
  if (documentoCache?.base === c.base) return documentoCache.id;
  let id = DOCUMENTO_PRA;
  try {
    const docs = await chiama<{ id?: string; _id?: string; name?: string }[]>(c, "GET", "/documents");
    const pra = docs.find((d) => /\bPRA\b/i.test(d.name ?? "") && /targa|plate/i.test(d.name ?? ""));
    id = pra?.id ?? pra?._id ?? id;
  } catch {
    // elenco non disponibile: si prova con l'id noto
  }
  documentoCache = { base: c.base, id };
  return id;
}

interface Richiesta {
  id?: string;
  _id?: string;
  state?: string;
}

/** Crea la richiesta di visura per targa. Restituisce l'id della richiesta e lo stato iniziale. */
export async function richiediVisura(c: Cred, targa: string, tipo: TipoVeicolo) {
  const documentId = await idDocumento(c);
  const r = await chiama<Richiesta>(c, "POST", "/requests", {
    documentId,
    // Campi del documento: field0 = tipo di veicolo, field1 = targa (da /documents → requestStructure)
    search: { field0: tipo, field1: targa },
  });
  const id = r.id ?? r._id;
  if (!id) throw new ErroreVisura("Openapi non ha restituito il numero della richiesta.");
  return { id, stato: r.state ?? "NEW" };
}

export const idValido = (id: string) => /^[A-Za-z0-9_-]{6,64}$/.test(id);
const filePdf = (aziendaId: string, id: string) => path.join(cartellaVisure(aziendaId), `${id}.pdf`);
export const urlPdf = (id: string) => `/api/visura/${id}/pdf`;

export async function leggiPdf(aziendaId: string, id: string) {
  if (!idValido(id)) return undefined;
  return readFile(filePdf(aziendaId, id)).catch(() => undefined);
}

/** Stato della richiesta; quando è evasa scarica il PDF nella cartella dati e ne dà l'indirizzo. */
export async function statoVisura(c: Cred, aziendaId: string, id: string): Promise<{ stato: string; pdf?: string; messaggio?: string }> {
  if (await leggiPdf(aziendaId, id)) return { stato: "DONE", pdf: urlPdf(id) };
  const r = await chiama<Richiesta & { cancellationReason?: string }>(c, "GET", `/requests/${id}`);
  const stato = r.state ?? "NEW";
  if (stato === "CANCELLED") return { stato, messaggio: r.cancellationReason || "Richiesta annullata da Openapi." };
  if (stato === "WAIT") return { stato, messaggio: "Openapi ha trovato più risultati: scegli quello giusto dalla console Openapi." };
  if (stato !== "DONE") return { stato };

  const files = await chiama<{ mimeType?: string; downloadUrl?: string; fileSize?: number }[]>(c, "GET", `/requests/${id}/documents`);
  const f = files.find((x) => x.mimeType === "application/pdf" && x.downloadUrl) ?? files.find((x) => x.downloadUrl);
  const prova = process.env.OPENAPI_DOCUENGINE_URL;
  if (!f?.downloadUrl || !(/^https:\/\//.test(f.downloadUrl) || (prova && f.downloadUrl.startsWith(prova)))) throw new ErroreVisura("Visura pronta ma senza PDF da scaricare.");
  // Indirizzo firmato e a tempo: niente token
  const res = await fetch(f.downloadUrl, { cache: "no-store", signal: AbortSignal.timeout(30_000) }).catch(() => undefined);
  if (!res?.ok) throw new ErroreVisura("Download del PDF non riuscito: riprova.");
  let bytes = Buffer.from(await res.arrayBuffer());
  if (bytes.length > MAX_PDF) throw new ErroreVisura("PDF della visura troppo grande.");
  // Openapi può consegnare il PDF codificato in base64
  if (bytes.subarray(0, 4).toString() !== "%PDF") {
    const dec = Buffer.from(bytes.toString("utf8").trim(), "base64");
    if (dec.subarray(0, 4).toString() !== "%PDF") throw new ErroreVisura("Il file ricevuto non è un PDF.");
    bytes = dec;
  }
  await mkdir(cartellaVisure(aziendaId), { recursive: true });
  await writeFile(filePdf(aziendaId, id), bytes, { mode: 0o600 });
  return { stato, pdf: urlPdf(id) };
}

// Sceglie il ponte eBay in base ai collegamenti salvati. Solo server.
import { leggiValori } from "@/lib/collegamenti-server";
import type { Ponte } from "./contratto";
import { ErroreEbay } from "./payload";
import { creaPonteSandbox, type CredSandbox } from "./sandbox";
import { creaPonteSimulato } from "./simulato";

const piena = (v: unknown): v is string => typeof v === "string" && v.trim() !== "";

/** Chiavi del Developers Program, solo con ambiente Sandbox e App ID, Cert ID e RuName tutti presenti. */
export async function credenzialiSandbox(aziendaId: string): Promise<CredSandbox | undefined> {
  const v = await leggiValori(aziendaId, "ebay");
  if (v.ambiente !== "Sandbox" || !piena(v.appId) || !piena(v.certId) || !piena(v.ruName)) return undefined;
  return { aziendaId, appId: v.appId.trim(), certId: v.certId.trim(), ruName: v.ruName.trim() };
}

/** Sandbox con le chiavi; altrimenti Simulato. */
export async function scegliPonte(aziendaId: string): Promise<Ponte> {
  const cred = await credenzialiSandbox(aziendaId);
  return cred ? creaPonteSandbox(cred) : creaPonteSimulato();
}

/** Messaggio da mostrare all'operatore: solo i nostri testi in italiano, mai il testo grezzo di un errore. */
export function messaggioPerUtente(e: unknown, predefinito = "eBay non risponde. Cosa fare: niente, il gestionale riprova da solo tra poco."): string {
  if (e instanceof ErroreEbay) return e.message;
  console.error("[ebay]", e);
  return predefinito;
}

// Sceglie il ponte eBay in base ai collegamenti salvati. Solo server.
import { leggiValori } from "@/lib/collegamenti-server";
import type { Ponte } from "./contratto";
import { creaPonteSimulato } from "./simulato";

const piena = (v: unknown) => typeof v === "string" && v.trim() !== "";

/** Sandbox solo con ambiente Sandbox e App ID, Cert ID e RuName; altrimenti Simulato. */
export async function scegliPonte(): Promise<Ponte> {
  const v = await leggiValori("ebay");
  const sandbox = v.ambiente === "Sandbox" && piena(v.appId) && piena(v.certId) && piena(v.ruName);
  if (sandbox) {
    // Il ponte Sandbox arriva con il Task 10: fin lì anche con le chiavi si lavora in modo simulato
  }
  return creaPonteSimulato();
}

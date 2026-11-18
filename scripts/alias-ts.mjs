// Per le prove lato server con `node --test` (npm test): risolve "@/..." in src/ e i percorsi relativi senza
// estensione (come fa Next), così i moduli del server (Better Auth compreso) si caricano in Node senza compilazione.
// Si usa con: node --import ./scripts/alias-ts.mjs --test ...
import { existsSync, statSync } from "node:fs";
import { registerHooks } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SRC = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "src");
const ESTENSIONI = [".ts", ".tsx", "/index.ts"];

function trova(base) {
  if (existsSync(base) && statSync(base).isFile()) return base;
  for (const e of ESTENSIONI) if (existsSync(base + e)) return base + e;
  return null;
}

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier.startsWith("@/")) {
      const f = trova(path.join(SRC, specifier.slice(2)));
      if (f) return nextResolve(pathToFileURL(f).href, context);
    }
    const relativo = specifier.startsWith("./") || specifier.startsWith("../");
    if (relativo && context.parentURL?.startsWith("file:") && !/\.(m?[jt]sx?|json)$/.test(specifier)) {
      const f = trova(path.resolve(path.dirname(fileURLToPath(context.parentURL)), specifier));
      if (f) return nextResolve(pathToFileURL(f).href, context);
    }
    return nextResolve(specifier, context);
  },
});

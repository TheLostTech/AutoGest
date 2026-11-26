import { PRODUTTORE } from "@/lib/config";
import type { Email } from "./invia";
import { indirizzoPubblico } from "./indirizzo";

function esc(v: string): string {
  return v.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

const PIEDE = `${PRODUTTORE.ragioneSociale} · ${PRODUTTORE.sede} · P. IVA e C.F. ${PRODUTTORE.piva} · REA ${PRODUTTORE.rea}`;
const MOTIVO = "Ricevi questa email perché ti sei registrato a Piazzale.";

// Mai relativo: senza indirizzo pubblico (in locale) si prende l'origine dal link dell'email stessa
function linkPrivacy(link: string): string {
  return `${indirizzoPubblico() ?? new URL(link).origin}/privacy`;
}

type Corpo = { oggetto: string; paragrafi: string[]; pulsante: string; link: string; nota?: string };

function componi(a: string, c: Corpo): Email {
  const privacy = linkPrivacy(c.link);
  const testo = [
    ...c.paragrafi,
    "",
    `${c.pulsante}: ${c.link}`,
    ...(c.nota ? ["", c.nota] : []),
    "",
    "—",
    PIEDE,
    MOTIVO,
    `Informativa privacy: ${privacy}`,
  ].join("\n");
  const p = c.paragrafi.map((t) => `<p style="margin:0 0 14px;font-size:15px;line-height:1.5;color:#1f2937">${esc(t)}</p>`).join("");
  const html = `<!doctype html><html lang="it"><body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:8px"><tr><td style="padding:28px">
${p}
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:20px 0"><tr><td style="background:#111827;border-radius:6px"><a href="${esc(c.link)}" style="display:inline-block;padding:12px 22px;color:#ffffff;font-size:15px;font-weight:bold;text-decoration:none">${esc(c.pulsante)}</a></td></tr></table>
<p style="margin:0 0 14px;font-size:13px;line-height:1.5;color:#4b5563">Se il pulsante non funziona, copia questo indirizzo nel browser: <a href="${esc(c.link)}" style="color:#4b5563;word-break:break-all">${esc(c.link)}</a></p>
${c.nota ? `<p style="margin:0 0 14px;font-size:13px;line-height:1.5;color:#4b5563">${esc(c.nota)}</p>` : ""}
<hr style="border:0;border-top:1px solid #e5e7eb;margin:20px 0">
<p style="margin:0 0 6px;font-size:12px;line-height:1.5;color:#6b7280">${esc(PIEDE)}</p>
<p style="margin:0;font-size:12px;line-height:1.5;color:#6b7280">${esc(MOTIVO)} <a href="${esc(privacy)}" style="color:#6b7280">Informativa privacy</a></p>
</td></tr></table></td></tr></table></body></html>`;
  return { a, oggetto: c.oggetto, testo, html };
}

// Senza il nome: chi la riceve non ha ancora dimostrato che quell'email è sua, e il nome lo scrive chi registra (anche
// con l'email di altri). Nessun testo scelto da chi registra entra in questa email.
export function emailConferma(link: string): Email {
  return componi("", {
    oggetto: "Conferma la tua email su Piazzale",
    paragrafi: [
      "Ciao,",
      "grazie per esserti registrato a Piazzale, il gestionale per autodemolizioni di Lostar Technology. Per attivare la prova gratuita conferma il tuo indirizzo email.",
      "Ti chiederemo la password che hai scelto quando ti sei registrato.",
    ],
    pulsante: "Conferma l'email",
    link,
    nota: "Se non sei stato tu a registrarti, ignora questo messaggio: senza conferma non succede nulla.",
  });
}

export function emailProvaInScadenza(nome: string, giorni: number, link: string): Email {
  const quando = giorni === 1 ? "domani" : `tra ${giorni} giorni`;
  return componi("", {
    oggetto: giorni === 1 ? "La tua prova di Piazzale finisce domani" : `La tua prova di Piazzale finisce tra ${giorni} giorni`,
    paragrafi: [`Ciao ${nome},`, `la tua prova gratuita di Piazzale finisce ${quando}. Per continuare a usare i moduli che ti servono, scegli ora quelli da tenere: i tuoi dati restano al sicuro.`],
    pulsante: "Scegli i moduli",
    link,
  });
}

export function emailProvaFinita(nome: string, link: string): Email {
  return componi("", {
    oggetto: "La tua prova di Piazzale è finita",
    paragrafi: [`Ciao ${nome},`, "la prova gratuita di Piazzale è terminata. I tuoi dati sono al sicuro: scegli i moduli che vuoi tenere per riprendere da dove avevi lasciato."],
    pulsante: "Scegli i moduli",
    link,
  });
}

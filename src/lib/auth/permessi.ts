import { createAccessControl } from "better-auth/plugins/access";
import { defaultStatements as statementsAzienda, memberAc } from "better-auth/plugins/organization/access";
import { defaultStatements as statementsPiattaforma, userAc } from "better-auth/plugins/admin/access";

// Permessi del plugin "organization" (le aziende): i sei ruoli hanno i permessi base di "member".
// Cosa può fare ogni ruolo nella gestione lo decide l'app (vedi accesso/), non questo elenco.
export const acAzienda = createAccessControl(statementsAzienda);
export const ruoliAzienda = {
  accettazione: acAzienda.newRole(memberAc.statements),
  smontatore: acAzienda.newRole(memberAc.statements),
  magazziniere: acAzienda.newRole(memberAc.statements),
  responsabile: acAzienda.newRole(memberAc.statements),
  vendite: acAzienda.newRole(memberAc.statements),
  consulente: acAzienda.newRole(memberAc.statements),
};

// Permessi del plugin "admin" (la piattaforma): il super admin ha i permessi di serie TRANNE
// "impersonate" e "impersonate-admins": "vedi come questo utente" non esiste, perché creerebbe una
// sessione vera dentro un'azienda senza ingresso di assistenza (motivo, 2 ore, codice dal telefono).
export const acPiattaforma = createAccessControl(statementsPiattaforma);
export const ruoliPiattaforma = {
  superadmin: acPiattaforma.newRole({
    ...statementsPiattaforma,
    user: statementsPiattaforma.user.filter((p) => p !== "impersonate" && p !== "impersonate-admins"),
  }),
  user: acPiattaforma.newRole(userAc.statements),
};

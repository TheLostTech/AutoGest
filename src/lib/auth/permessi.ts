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

// Permessi del plugin "admin" (la piattaforma): il super admin ha tutti i permessi di serie.
export const acPiattaforma = createAccessControl(statementsPiattaforma);
export const ruoliPiattaforma = {
  superadmin: acPiattaforma.newRole(statementsPiattaforma),
  user: acPiattaforma.newRole(userAc.statements),
};

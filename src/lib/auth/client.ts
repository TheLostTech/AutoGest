import { createAuthClient } from "better-auth/react";
import { adminClient, organizationClient, twoFactorClient } from "better-auth/client/plugins";
import { acAzienda, acPiattaforma, ruoliAzienda, ruoliPiattaforma } from "./permessi";

export const authClient = createAuthClient({
  plugins: [
    organizationClient({ ac: acAzienda, roles: ruoliAzienda }),
    adminClient({ ac: acPiattaforma, roles: ruoliPiattaforma }),
    twoFactorClient(),
  ],
});

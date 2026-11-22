import { TYPE_GROUPS } from "@/lib/catalog";

// Le tipologie sono centinaia: nei menu a tendina vanno raggruppate per categoria, in ordine alfabetico.
export function TypeOptions() {
  return (
    <>
      {TYPE_GROUPS.map(([cat, types]) => (
        <optgroup key={cat} label={cat}>
          {types.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </optgroup>
      ))}
    </>
  );
}

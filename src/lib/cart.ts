"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

interface Cart {
  ids: string[];
  add: (id: string) => void;
  remove: (id: string) => void;
  clear: () => void;
}

export const useCart = create<Cart>()(
  persist(
    (set) => ({
      ids: [],
      add: (id) => set((s) => (s.ids.includes(id) ? s : { ids: [...s.ids, id] })),
      remove: (id) => set((s) => ({ ids: s.ids.filter((x) => x !== id) })),
      clear: () => set({ ids: [] }),
    }),
    { name: "gestionale-demolizione-carrello", storage: createJSONStorage(() => localStorage) },
  ),
);

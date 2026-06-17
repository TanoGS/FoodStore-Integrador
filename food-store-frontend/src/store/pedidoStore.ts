// src/store/pedidoStore.ts
// Store del último pedido creado.
// Persiste el ID y el estado para que PedidoExitoso pueda recuperarlo
// incluso si el usuario navega o recarga la página.

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface PedidoState {
  ultimoPedidoId:     number | null;
  ultimoPedidoEstado: string | null;

  setUltimoPedido: (id: number, estado: string) => void;
  clearUltimoPedido: () => void;
}

export const usePedidoStore = create<PedidoState>()(
  persist(
    (set) => ({
      ultimoPedidoId:     null,
      ultimoPedidoEstado: null,

      setUltimoPedido: (id, estado) =>
        set({ ultimoPedidoId: id, ultimoPedidoEstado: estado }),

      clearUltimoPedido: () =>
        set({ ultimoPedidoId: null, ultimoPedidoEstado: null }),
    }),
    {
      name: 'food-store-pedido',
      storage: createJSONStorage(() => sessionStorage),
    }
  )
);

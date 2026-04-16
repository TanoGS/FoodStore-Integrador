import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Tipos temporales, luego los ajustaremos con las entities
interface CartItem {
  productoId: number;
  cantidad: number;
  precioSnapshot: number; 
}

interface CartState {
  items: CartItem[];
  total: number;
  addItem: (item: CartItem) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      total: 0,
      addItem: (item) => set((state) => ({ items: [...state.items, item] })), // Lógica temporal
      clearCart: () => set({ items: [], total: 0 }),
    }),
    {
      name: 'food-store-cart', // Clave en localStorage
    }
  )
);
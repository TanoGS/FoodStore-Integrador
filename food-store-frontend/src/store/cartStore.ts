import { create } from 'zustand';
import { persist } from 'zustand/middleware';


export interface ProductoCart {
  id: number;
  nombre: string;
  precio_base: number;
  imagen_url?: string | null;
  categoria_nombre?: string;
  opciones_seleccionadas?: any[]; 
  subtotal: number;
}

export interface CartItem {
  producto: ProductoCart;
  cantidad: number;
}

interface CartState {
  items: CartItem[];
  
  // Acciones
  addItem: (producto: ProductoCart, cantidad?: number) => void;
  removeItem: (productoId: number) => void;
  updateQuantity: (productoId: number, cantidad: number) => void;
  clearCart: () => void;
  
  // Getters computados
  getTotalItems: () => number;
  getTotalPrice: () => number;
  setItems: (items: CartItem[]) => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
        items: [],

        // 1. Agregar un producto (si ya existe, suma la cantidad)
        addItem: (producto, cantidad = 1) => {
          const currentItems = get().items;
          const existingItem = currentItems.find(item => item.producto.id === producto.id);

          if (existingItem) {
            set({
              items: currentItems.map(item => 
                item.producto.id === producto.id 
                  ? { ...item, cantidad: item.cantidad + cantidad }
                  : item
              )
            });
          } else {
            set({ items: [...currentItems, { producto, cantidad }] });
          }
        },

        // 2. Eliminar producto por completo
        removeItem: (productoId) => {
          set({ items: get().items.filter(item => item.producto.id !== productoId) });
        },

        // 3. Cambiar la cantidad con los botones + y -
        updateQuantity: (productoId, cantidad) => {
          if (cantidad <= 0) {
            get().removeItem(productoId); // Si llega a 0, lo borramos
            return;
          }
          set({
            items: get().items.map(item => 
              item.producto.id === productoId ? { ...item, cantidad } : item
            )
          });
        },

        // 4. Vaciar carrito
        clearCart: () => set({ items: [] }),

        // 5. Cálculos automáticos para el Navbar y el Total a Pagar
        getTotalItems: () => get().items.reduce((total, item) => total + item.cantidad, 0),
        getTotalPrice: () => get().items.reduce((total, item) => total + (item.producto.precio_base * item.cantidad), 0),

        // 6. Cargar items (usado al iniciar sesión para restaurar el carrito del usuario)
        setItems: (items) => set({ items }),
      }),
    {
      name: 'foodstore-cart', // nombre de la key en localStorage
    }
  )
);

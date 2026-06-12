import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ThemeState {
  isDarkMode: boolean;
  toggle: () => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      isDarkMode: true, // el panel admin arranca en dark por defecto
      toggle: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
    }),
    {
      name: 'food-store-theme',
    }
  )
);
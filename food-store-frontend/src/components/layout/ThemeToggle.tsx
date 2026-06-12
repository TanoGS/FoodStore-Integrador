import { Sun, Moon } from 'lucide-react';
import { useThemeStore } from '../../store/themeStore';

export default function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { isDarkMode, toggle } = useThemeStore();

  return (
    <button
      onClick={toggle}
      title={isDarkMode ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      className={`
        flex items-center justify-center rounded-xl transition-all duration-200
        ${compact
          ? 'w-9 h-9'
          : 'gap-2 px-3 py-2 text-sm font-bold'
        }
        ${isDarkMode
          ? 'bg-slate-700 text-yellow-400 hover:bg-slate-600 hover:text-yellow-300'
          : 'bg-slate-200 text-slate-700 hover:bg-slate-300 hover:text-slate-900'
        }
      `}
    >
      {isDarkMode ? (
        <>
          {!compact && <span>Modo Claro</span>}
          <Sun className="w-4 h-4" />
        </>
      ) : (
        <>
          {!compact && <span>Modo Oscuro</span>}
          <Moon className="w-4 h-4" />
        </>
      )}
    </button>
  );
}
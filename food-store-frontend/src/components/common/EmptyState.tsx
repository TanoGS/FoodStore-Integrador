// src/components/common/EmptyState.tsx
// Componente genérico de estado vacío para listas sin datos.

import type { ReactNode } from 'react';
import { PackageOpen } from 'lucide-react';

interface EmptyStateProps {
  title?:       string;
  description?: string;
  icon?:        ReactNode;
  action?:      ReactNode;
}

export function EmptyState({
  title       = 'Sin resultados',
  description = 'No hay datos para mostrar.',
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-5">
        {icon ?? <PackageOpen className="w-8 h-8 text-slate-400" />}
      </div>
      <h3 className="text-lg font-bold text-slate-700 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 max-w-xs">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

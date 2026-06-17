// src/components/common/SkeletonCard.tsx
// Skeletons reutilizables con animate-pulse de Tailwind.

/** Skeleton para una fila/card de pedido (MisPedidos, GestorPedidos) */
export function SkeletonPedidoRow() {
  return (
    <div className="animate-pulse bg-white rounded-2xl border border-slate-100 p-5 space-y-3">
      <div className="flex justify-between">
        <div className="h-4 bg-slate-200 rounded w-24" />
        <div className="h-5 bg-slate-200 rounded-full w-24" />
      </div>
      <div className="h-3 bg-slate-100 rounded w-40" />
      <div className="flex justify-between">
        <div className="h-3 bg-slate-100 rounded w-32" />
        <div className="h-4 bg-slate-200 rounded w-16" />
      </div>
    </div>
  );
}

/** Skeleton para una tarjeta de producto (Home / catálogo) */
export function SkeletonProductCard() {
  return (
    <div className="animate-pulse bg-white rounded-2xl border border-slate-100 overflow-hidden">
      <div className="h-44 bg-slate-200" />
      <div className="p-4 space-y-2">
        <div className="h-4 bg-slate-200 rounded w-3/4" />
        <div className="h-3 bg-slate-100 rounded w-full" />
        <div className="h-3 bg-slate-100 rounded w-2/3" />
        <div className="flex justify-between items-center pt-2">
          <div className="h-5 bg-slate-200 rounded w-16" />
          <div className="h-8 bg-slate-200 rounded-xl w-24" />
        </div>
      </div>
    </div>
  );
}

/** Skeleton para una fila de pedido en el admin (GestorPedidos) */
export function SkeletonAdminRow() {
  return (
    <div className="animate-pulse bg-slate-800/60 rounded-xl p-4 space-y-2 border border-slate-700/40">
      <div className="flex justify-between">
        <div className="h-4 bg-slate-700 rounded w-20" />
        <div className="h-5 bg-slate-700 rounded-full w-28" />
      </div>
      <div className="h-3 bg-slate-700/60 rounded w-48" />
      <div className="flex gap-2">
        <div className="h-7 bg-slate-700 rounded-lg w-24" />
        <div className="h-7 bg-slate-700 rounded-lg w-24" />
      </div>
    </div>
  );
}

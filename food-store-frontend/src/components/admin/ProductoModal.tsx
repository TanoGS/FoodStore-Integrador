import React, { useState, useEffect, useMemo } from 'react';
import { X, Calculator, ArrowRight, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { CatalogoService } from '../../services/catalogo.service';

// ── Interfaces TypeScript del componente ───────────────────────────────────────────
interface RecetaItemPayload {
  ingrediente_id:     number;
  cantidad_requerida: number;
  es_removible:       boolean;
}

export interface ProductoPayload {
  nombre:          string;
  descripcion?:    string | null;
  imagen_url?:     string | null;
  stock:           number;
  activo:          boolean;
  categoria_ids:   number[];
  margen_ganancia: number;
  precio_manual?:  number | null;
  receta:          RecetaItemPayload[];
}

export interface ProductoEditar {
  id:                    number;
  nombre:                string;
  descripcion?:          string;
  imagen_url?:           string | null;
  stock:                 number;
  activo:                boolean;
  margen_ganancia:       number;
  precio:                number;
  categorias?:           { id: number; nombre: string }[];
  ingredientes_enlaces?: {
    ingrediente_id:     number;
    cantidad_requerida: number;
    es_removible:       boolean;
  }[];
}

interface ProductoModalProps {
  productoEditar?: ProductoEditar | null;
  onClose: () => void;
  onSave: (payload: ProductoPayload) => void;
}

interface IngCfg {
  cantidad:     number | '';
  es_removible: boolean;
  agregado:     boolean;
}

const INGS_POR_PAG = 10;

export default function ProductoModal({ productoEditar, onClose, onSave }: ProductoModalProps) {
  // --- Catálogos Maestros ---
  const [categoriasDB,    setCategoriasDB]    = useState<any[]>([]);
  const [ingredientesDB,  setIngredientesDB]  = useState<any[]>([]);
  const [loadingDatos,    setLoadingDatos]    = useState(true);

  // --- Estado del Producto ---
  const [nombre,      setNombre]      = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [imagenUrl,   setImagenUrl]   = useState('');
  const [stock,       setStock]       = useState<number | ''>('');
  const [activo,      setActivo]      = useState(true);
  const [categoriaId, setCategoriaId] = useState<number | null>(null);

  // Finanzas
  const [margenGanancia, setMargenGanancia] = useState<number>(90);
  const [precioManual,   setPrecioManual]   = useState<number | ''>('');

  // Ingredientes: mapa id → configuración de fila
  const [ingConfig, setIngConfig] = useState<Record<number, IngCfg>>({});
  const [filtroIng, setFiltroIng] = useState('');
  const [pagIng,    setPagIng]    = useState(1);

  // Preview de imagen: reset del error cuando cambia la URL
  const [imgPreviewError, setImgPreviewError] = useState(false);

  useEffect(() => { cargarDatosMaestros(); }, []);
  useEffect(() => { setPagIng(1); }, [filtroIng]);
  useEffect(() => { setImgPreviewError(false); }, [imagenUrl]);

  const cargarDatosMaestros = async () => {
    try {
      const [cats, ings] = await Promise.all([
        CatalogoService.getCategorias(),
        CatalogoService.getIngredientes(),
      ]);
      setCategoriasDB(cats);
      setIngredientesDB(ings);

      if (productoEditar) {
        setNombre(productoEditar.nombre || '');
        setDescripcion(productoEditar.descripcion || '');
        setImagenUrl(productoEditar.imagen_url || '');
        setStock(productoEditar.stock ?? '');
        setActivo(productoEditar.activo !== false);
        setMargenGanancia(productoEditar.margen_ganancia ?? 90);
        setPrecioManual(productoEditar.precio ?? '');

        if (productoEditar.categorias?.length) {
          setCategoriaId(productoEditar.categorias[0].id);
        }

        if (productoEditar.ingredientes_enlaces?.length) {
          const cfg: Record<number, IngCfg> = {};
          for (const e of productoEditar.ingredientes_enlaces) {
            cfg[e.ingrediente_id] = {
              cantidad:     e.cantidad_requerida,
              es_removible: e.es_removible,
              agregado:     true,
            };
          }
          setIngConfig(cfg);
        }
      }
    } catch (err) {
      console.error('Error cargando catálogos:', err);
    } finally {
      setLoadingDatos(false);
    }
  };

  // ── Ingredientes filtrados y paginados ─────────────────────────────────────
  const ingsFiltrados = useMemo(
    () => ingredientesDB.filter(i =>
      i.nombre.toLowerCase().includes(filtroIng.toLowerCase())
    ),
    [ingredientesDB, filtroIng]
  );
  const totalPagsIng  = Math.max(1, Math.ceil(ingsFiltrados.length / INGS_POR_PAG));
  const ingsPaginados = ingsFiltrados.slice(
    (pagIng - 1) * INGS_POR_PAG,
    pagIng * INGS_POR_PAG
  );

  // ── Receta computada (sólo ingredientes marcados con cantidad > 0) ─────────
  const receta = useMemo(
    () =>
      Object.entries(ingConfig)
        .filter(([, c]) => c.agregado && Number(c.cantidad) > 0)
        .map(([id, c]) => {
          const ing = ingredientesDB.find(i => i.id === Number(id));
          return {
            ingrediente_id:     Number(id),
            cantidad_requerida: Number(c.cantidad),
            es_removible:       c.es_removible,
            _nombre:            ing?.nombre          || 'Desconocido',
            _costo_unitario:    ing?.costo_unitario  || 0,
            _unidad:            ing?.unidad_medida   || '',
          };
        }),
    [ingConfig, ingredientesDB]
  );

  // ── Finanzas ───────────────────────────────────────────────────────────────
  const costoTotalProduccion = useMemo(
    () => receta.reduce((acc, r) => acc + r.cantidad_requerida * r._costo_unitario, 0),
    [receta]
  );
  const precioSugerido = useMemo(
    () => costoTotalProduccion * (1 + margenGanancia / 100),
    [costoTotalProduccion, margenGanancia]
  );
  const precioFinal = precioManual !== '' ? Number(precioManual) : precioSugerido;

  // ── Helpers tabla de ingredientes ─────────────────────────────────────────
  const getCfg = (id: number): IngCfg =>
    ingConfig[id] ?? { cantidad: '', es_removible: false, agregado: false };

  const setCfg = (id: number, patch: Partial<IngCfg>) =>
    setIngConfig(prev => ({ ...prev, [id]: { ...getCfg(id), ...patch } }));

  const handleCantidad = (ing: any, val: string) => {
    if (val === '') { setCfg(ing.id, { cantidad: '' }); return; }
    const esUnidad = ing.unidad_medida?.toUpperCase() === 'UNIDAD';
    const num      = esUnidad ? Math.floor(Math.abs(Number(val))) : Math.abs(Number(val));
    if (!isNaN(num)) setCfg(ing.id, { cantidad: num });
  };

  // ── Submit ─────────────────────────────────────────────────────────────────
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoriaId) {
      alert('Debes seleccionar una categoría.');
      return;
    }
    const ingSinCantidad = Object.entries(ingConfig).filter(
      ([, c]) => c.agregado && (c.cantidad === '' || Number(c.cantidad) <= 0)
    );
    if (ingSinCantidad.length > 0) {
      const nombres = ingSinCantidad.map(([id]) => {
        const ing = ingredientesDB.find(i => i.id === Number(id));
        return ing?.nombre || `ID ${id}`;
      });
      alert(`Los siguientes ingredientes seleccionados necesitan una cantidad mayor a 0:\n${nombres.join(', ')}`);
      return;
    }

    const payload: ProductoPayload = {
      nombre,
      descripcion:     descripcion || null,
      imagen_url:      imagenUrl   || null,
      stock:           stock === '' ? 0 : Number(stock),
      activo,
      categoria_ids:   [categoriaId],
      margen_ganancia: Number(margenGanancia),
      precio_manual:   precioManual === '' ? null : Number(precioManual),
      receta: receta.map(r => ({
        ingrediente_id:     r.ingrediente_id,
        cantidad_requerida: r.cantidad_requerida,
        es_removible:       r.es_removible,
      })),
    };

    onSave(payload);
  };

  const categoriaSel = categoriasDB.find(c => c.id === categoriaId);

  if (loadingDatos) {
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-2xl shadow-xl flex items-center gap-3">
          <div className="animate-spin h-5 w-5 border-2 border-orange-600 border-t-transparent rounded-full"></div>
          <span className="font-bold text-slate-700">Cargando base de datos...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-[min(95vw,1344px)] max-h-[95vh] flex flex-col overflow-hidden">

        {/* Cabecera */}
        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-slate-900 text-white shrink-0">
          <h3 className="font-black text-xl">
            {productoEditar ? 'Modificar Plato y Receta' : 'Creación de Nuevo Plato'}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-red-400 transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Cuerpo Scrollable */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50">
          <form id="product-form" onSubmit={handleSubmit} className="space-y-8">

            {/* SECCIÓN 1: Info Básica */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h4 className="text-sm font-black text-slate-400 uppercase tracking-wider mb-4">1. Identidad del Plato</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1">Nombre Comercial *</label>
                  <input
                    type="text" required value={nombre}
                    onChange={e => setNombre(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1">Stock Fijo (Opcional)</label>
                  <input
                    type="number" value={stock}
                    onChange={e => setStock(e.target.value === '' ? '' : Number(e.target.value))}
                    className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none"
                    placeholder="Dejar vacío si es ilimitado"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1">URL de Imagen (Opcional)</label>
                  <input
                    type="url" value={imagenUrl}
                    onChange={e => setImagenUrl(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none"
                    placeholder="https://..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1">Descripción</label>
                  <input
                    type="text" value={descripcion}
                    onChange={e => setDescripcion(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-bold text-slate-700 mb-2">Categoría del Menú *</label>
                  <div className="flex flex-wrap gap-2">
                    {categoriasDB.map(cat => (
                      <button
                        type="button" key={cat.id}
                        onClick={() => setCategoriaId(cat.id)}
                        className={`px-3 py-1.5 rounded-lg text-sm font-bold transition-all border ${
                          categoriaId === cat.id
                            ? 'bg-orange-100 border-orange-500 text-orange-700 shadow-sm'
                            : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
                        }`}
                      >
                        {cat.nombre}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* SECCIÓN 2: ESCANDALLO */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h4 className="text-sm font-black text-slate-400 uppercase tracking-wider mb-4">2. Hoja de Receta (Escandallo)</h4>

              {/* Filtro */}
              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filtrar ingredientes por nombre..."
                  value={filtroIng}
                  onChange={e => setFiltroIng(e.target.value)}
                  className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none text-sm"
                />
              </div>

              {/* Tabla */}
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-sm text-left">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs font-black uppercase">
                      <th className="px-4 py-3">Nombre</th>
                      <th className="px-4 py-3 w-44">Cantidad usada</th>
                      <th className="px-4 py-3 w-48 text-center">Cliente puede quitarlo</th>
                      <th className="px-4 py-3 w-24 text-center">Agregar</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {ingsPaginados.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-4 py-8 text-center text-slate-400">
                          No se encontraron ingredientes.
                        </td>
                      </tr>
                    ) : ingsPaginados.map(ing => {
                      const cfg      = getCfg(ing.id);
                      const esUnidad = ing.unidad_medida?.toUpperCase() === 'UNIDAD';
                      const invalid  = cfg.agregado && (cfg.cantidad === '' || Number(cfg.cantidad) <= 0);
                      return (
                        <tr key={ing.id} className={cfg.agregado ? 'bg-orange-50' : 'hover:bg-slate-50'}>
                          <td className="px-4 py-3">
                            <span className="font-bold text-slate-800">{ing.nombre}</span>
                            <span className="ml-2 text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded font-medium">
                              {ing.unidad_medida}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <input
                              type="number"
                              min={esUnidad ? 1 : 0.001}
                              step={esUnidad ? 1 : 0.001}
                              value={cfg.cantidad}
                              onChange={e => handleCantidad(ing, e.target.value)}
                              placeholder={esUnidad ? '1' : '0.000'}
                              className={`w-full px-2 py-1.5 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-orange-400 ${
                                invalid
                                  ? 'border-red-300 bg-red-50'
                                  : 'border-slate-200 bg-white'
                              }`}
                            />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <input
                              type="checkbox"
                              checked={cfg.es_removible}
                              onChange={e => setCfg(ing.id, { es_removible: e.target.checked })}
                              className="w-4 h-4 accent-orange-600 cursor-pointer"
                            />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <input
                              type="checkbox"
                              checked={cfg.agregado}
                              onChange={e => setCfg(ing.id, { agregado: e.target.checked })}
                              className="w-4 h-4 accent-orange-600 cursor-pointer"
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Paginación */}
              <div className="flex items-center justify-between mt-3">
                <span className="text-xs text-slate-500">
                  {ingsFiltrados.length} ingredientes · Página {pagIng} de {totalPagsIng}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setPagIng(p => Math.max(1, p - 1))}
                    disabled={pagIng === 1}
                    className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setPagIng(p => Math.min(totalPagsIng, p + 1))}
                    disabled={pagIng === totalPagsIng}
                    className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* SECCIÓN 3: FINANZAS */}
            <div className="bg-slate-900 p-6 rounded-2xl shadow-sm text-white">
              <h4 className="text-sm font-black text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Calculator className="w-4 h-4" /> 3. Proyección Financiera
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
                <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
                  <div className="text-slate-400 text-xs font-bold mb-1">COSTO DE PRODUCCIÓN</div>
                  <div className="text-2xl font-black text-white">${costoTotalProduccion.toFixed(2)}</div>
                </div>
                <div className="space-y-4">
                  <div>
                    <label className="flex justify-between text-xs font-bold text-slate-300 mb-1">
                      <span>Margen de Ganancia (%)</span>
                      <span className="text-orange-400">{margenGanancia}%</span>
                    </label>
                    <input
                      type="range" min="0" max="300" step="5" value={margenGanancia}
                      onChange={e => setMargenGanancia(Number(e.target.value))}
                      className="w-full accent-orange-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-300 mb-1">O Forzar Precio Manual ($)</label>
                    <input
                      type="number" value={precioManual}
                      onChange={e => setPrecioManual(e.target.value === '' ? '' : Number(e.target.value))}
                      className="w-full px-3 py-1.5 bg-slate-800 border border-slate-600 rounded-lg text-white outline-none focus:border-orange-500"
                      placeholder="Ej: 5000"
                    />
                  </div>
                </div>
                <div className="bg-orange-500 p-4 rounded-xl shadow-lg shadow-orange-500/20 text-right flex flex-col justify-center h-full">
                  <div className="text-orange-100 text-xs font-bold mb-1">PRECIO DE VENTA PÚBLICO</div>
                  <div className="text-3xl font-black text-white flex items-center justify-end gap-2">
                    {precioManual !== '' && (
                      <span className="line-through text-orange-300 text-lg">${precioSugerido.toFixed(2)}</span>
                    )}
                    ${precioFinal.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>

            {/* SECCIÓN 4: VISTA PREVIA */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h4 className="text-sm font-black text-slate-400 uppercase tracking-wider mb-4">4. Vista Previa del Plato</h4>
              <div className="flex gap-6 items-start">
                <div className="w-24 h-24 rounded-xl overflow-hidden bg-slate-100 flex items-center justify-center text-4xl shrink-0">
                  {imagenUrl && !imgPreviewError
                    ? (
                      <img
                        src={imagenUrl}
                        alt="preview"
                        referrerPolicy="no-referrer"
                        className="w-full h-full object-cover"
                        onError={() => setImgPreviewError(true)}
                      />
                    )
                    : '🍽️'
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-2xl font-black text-slate-900 truncate">
                    {nombre || <span className="text-slate-300 font-normal text-lg">Sin nombre</span>}
                  </h3>
                  {categoriaSel && (
                    <span className="inline-block mt-1 px-2.5 py-0.5 bg-orange-100 text-orange-700 text-xs font-black rounded-full">
                      {categoriaSel.nombre}
                    </span>
                  )}
                  {descripcion && <p className="text-sm text-slate-500 mt-2 line-clamp-2">{descripcion}</p>}
                  <p className="text-3xl font-black text-orange-600 mt-2">${precioFinal.toFixed(2)}</p>
                </div>
              </div>

              {receta.length > 0 ? (
                <div className="mt-5">
                  <h5 className="text-xs font-black text-slate-400 uppercase tracking-wider mb-3">Composición de la Receta</h5>
                  <div className="flex flex-wrap gap-2">
                    {receta.map(r => (
                      <span
                        key={r.ingrediente_id}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold border ${
                          r.es_removible
                            ? 'bg-green-50 border-green-200 text-green-700'
                            : 'bg-slate-100 border-slate-200 text-slate-700'
                        }`}
                      >
                        {r._nombre}
                        <span className="text-xs font-normal opacity-70">
                          {r.cantidad_requerida} {r._unidad}
                        </span>
                        {r.es_removible && (
                          <span className="text-[10px] bg-green-200 text-green-800 px-1 rounded font-black">
                            REMOVIBLE
                          </span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="mt-4 p-4 bg-slate-50 rounded-xl text-center text-slate-400 text-sm border-2 border-dashed border-slate-200">
                  Seleccioná ingredientes en la tabla para ver la composición del plato.
                </div>
              )}
            </div>

          </form>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-white flex justify-end items-center gap-3 shrink-0">
          <button type="button" onClick={onClose} className="px-5 py-2.5 text-slate-500 font-bold hover:bg-slate-50 rounded-xl transition">
            Cancelar
          </button>
          <button form="product-form" type="submit" className="px-6 py-2.5 bg-orange-600 text-white font-black rounded-xl hover:bg-orange-700 transition shadow-lg shadow-orange-600/20 flex items-center gap-2">
            Guardar Plato <ArrowRight className="w-5 h-5" />
          </button>
        </div>

      </div>
    </div>
  );
}

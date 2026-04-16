interface ProductoCardProps {
  id: number;
  nombre: string;
  descripcion: string;
  precio: number;
  imagen?: string;
}

export const ProductoCard = ({ id, nombre, descripcion, precio, imagen }: ProductoCardProps) => {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow duration-300 border border-gray-100 flex flex-col">
      {/* Imagen placeholder */}
      <div className="h-48 bg-gray-200 w-full object-cover flex items-center justify-center text-5xl">
        {imagen ? <img src={imagen} alt={nombre} className="w-full h-full object-cover" /> : "🍔"}
      </div>
      
      <div className="p-5 flex flex-col flex-grow">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-xl font-bold text-gray-800">{nombre}</h3>
          <span className="bg-orange-100 text-orange-800 text-sm font-semibold px-2.5 py-0.5 rounded">
            ${precio.toFixed(2)}
          </span>
        </div>
        
        <p className="text-gray-600 text-sm mb-4 flex-grow line-clamp-2">
          {descripcion}
        </p>
        
        <button className="w-full mt-auto bg-orange-600 hover:bg-orange-700 text-white font-bold py-2 px-4 rounded transition-colors focus:ring-4 focus:ring-orange-300">
          Agregar al Carrito
        </button>
      </div>
    </div>
  );
};
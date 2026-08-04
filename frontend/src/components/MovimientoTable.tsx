import type { Movimiento } from "../services/api";

type MovimientoTableProps = {
  movimientos: Movimiento[];
  onEdit?: (movimiento: Movimiento) => void;
  onDelete?: (movimiento: Movimiento) => void;
};

function formatFecha(fecha: string): string {
  const date = new Date(fecha);
  if (Number.isNaN(date.getTime())) {
    return fecha;
  }
  return date.toLocaleString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MovimientoTable({
  movimientos,
  onEdit,
  onDelete,
}: MovimientoTableProps) {
  const showActions = Boolean(onEdit || onDelete);

  return (
    <table className="movimiento-table">
      <thead>
        <tr>
          <th>Descripción</th>
          <th>Monto</th>
          <th>Subtotal</th>
          <th>Fecha</th>
          {showActions ? (
            <th className="movimiento-table-actions-header">Acciones</th>
          ) : null}
        </tr>
      </thead>
      <tbody>
        {movimientos.length === 0 ? (
          <tr>
            <td colSpan={showActions ? 5 : 4} className="movimiento-table-empty">
              No hay movimientos registrados.
            </td>
          </tr>
        ) : null}
        {movimientos.map((movimiento) => (
          <tr key={movimiento.id}>
            <td>{movimiento.descripcion}</td>
            <td
              className={
                movimiento.tipo === "entrada"
                  ? "movimiento-entrada"
                  : "movimiento-salida"
              }
            >
              {movimiento.tipo === "salida" ? "-" : ""}
              {movimiento.monto}
            </td>
            <td>{movimiento.subtotal}</td>
            <td>{formatFecha(movimiento.fecha)}</td>
            {showActions ? (
              <td className="movimiento-table-actions">
                <div className="movimiento-table-actions-inner">
                  {movimiento.editable && onEdit ? (
                    <button
                      type="button"
                      className="btn-table-action btn-table-action-edit"
                      onClick={() => onEdit(movimiento)}
                    >
                      Editar
                    </button>
                  ) : null}
                  {movimiento.editable && onDelete ? (
                    <button
                      type="button"
                      className="btn-table-action btn-table-action-delete"
                      onClick={() => onDelete(movimiento)}
                    >
                      Eliminar
                    </button>
                  ) : null}
                </div>
              </td>
            ) : null}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

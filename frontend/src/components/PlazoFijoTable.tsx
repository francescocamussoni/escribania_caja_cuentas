import type { PlazoFijo } from "../services/api";

type PlazoFijoTableProps = {
  plazosFijos: PlazoFijo[];
  onEdit?: (plazoFijo: PlazoFijo) => void;
  onDelete?: (plazoFijo: PlazoFijo) => void;
};

function formatFechaVencimiento(fecha: string): string {
  const date = new Date(`${fecha}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return fecha;
  }
  return date.toLocaleDateString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function handleDeleteClick(
  plazoFijo: PlazoFijo,
  onDelete: (plazoFijo: PlazoFijo) => void,
) {
  const confirmed = window.confirm("¿Eliminar este plazo fijo?");
  if (!confirmed) {
    return;
  }
  onDelete(plazoFijo);
}

export default function PlazoFijoTable({
  plazosFijos,
  onEdit,
  onDelete,
}: PlazoFijoTableProps) {
  const showActions = Boolean(onEdit || onDelete);

  return (
    <table className="movimiento-table plazo-fijo-table">
      <thead>
        <tr>
          <th>Monto ingresado</th>
          <th>Fecha de vencimiento</th>
          <th>Monto a vencimiento</th>
          {showActions ? (
            <th className="movimiento-table-actions-header">Acciones</th>
          ) : null}
        </tr>
      </thead>
      <tbody>
        {plazosFijos.length === 0 ? (
          <tr>
            <td
              colSpan={showActions ? 4 : 3}
              className="movimiento-table-empty"
            >
              No hay plazos fijos registrados.
            </td>
          </tr>
        ) : null}
        {plazosFijos.map((plazoFijo) => (
          <tr
            key={plazoFijo.id}
            className={plazoFijo.vencido ? "plazo-fijo-row--vencido" : undefined}
          >
            <td>{plazoFijo.monto_ingresado}</td>
            <td>{formatFechaVencimiento(plazoFijo.fecha_vencimiento)}</td>
            <td>{plazoFijo.monto_a_vencimiento}</td>
            {showActions ? (
              <td className="movimiento-table-actions">
                <div className="movimiento-table-actions-inner">
                  {onEdit ? (
                    <button
                      type="button"
                      className="btn-table-action btn-table-action-edit"
                      onClick={() => onEdit(plazoFijo)}
                    >
                      Editar
                    </button>
                  ) : null}
                  {onDelete ? (
                    <button
                      type="button"
                      className="btn-table-action btn-table-action-delete"
                      onClick={() => handleDeleteClick(plazoFijo, onDelete)}
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

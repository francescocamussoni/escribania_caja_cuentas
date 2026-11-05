import type { Movimiento } from "../services/api";
import { formatFechaIso, llegoFechaLiquidacion } from "../utils/fechas";

type MovimientoTableProps = {
  movimientos: Movimiento[];
  onEdit?: (movimiento: Movimiento) => void;
  onDelete?: (movimiento: Movimiento) => void;
  /** Liquidate a pending cheque listed among the movimientos (Registro only). */
  onLiquidar?: (movimiento: Movimiento) => void;
  /** Endorse a pending cheque listed among the movimientos (Registro only). */
  onEndosar?: (movimiento: Movimiento) => void;
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
  onLiquidar,
  onEndosar,
}: MovimientoTableProps) {
  const showActions = Boolean(onEdit || onDelete || onLiquidar || onEndosar);
  const showValorTotal = movimientos.some((m) => m.valor_total != null);

  return (
    <table className="movimiento-table">
      <thead>
        <tr>
          <th>Descripción</th>
          <th>Monto</th>
          <th>Subtotal</th>
          {showValorTotal ? <th>Valor de caja total</th> : null}
          <th>Fecha</th>
          {showActions ? (
            <th className="movimiento-table-actions-header">Acciones</th>
          ) : null}
        </tr>
      </thead>
      <tbody>
        {movimientos.length === 0 ? (
          <tr>
            <td colSpan={(showActions ? 5 : 4) + (showValorTotal ? 1 : 0)} className="movimiento-table-empty">
              No hay movimientos registrados.
            </td>
          </tr>
        ) : null}
        {movimientos.map((movimiento) => (
          <tr key={movimiento.id}>
            <td data-label="Descripción">
              {movimiento.descripcion}
              {movimiento.endosado_a ? (
                <span className="movimiento-endose-marca">
                  Endosado → {movimiento.endosado_a.nombre}
                </span>
              ) : null}
              {movimiento.endose_origen ? (
                <span className="movimiento-endose-marca">
                  Endose desde {movimiento.endose_origen.caja.nombre}
                </span>
              ) : null}
            </td>
            <td
              data-label="Monto"
              className={
                movimiento.tipo === "entrada"
                  ? "movimiento-entrada"
                  : "movimiento-salida"
              }
            >
              {movimiento.instrumento === "cheque" ||
              movimiento.instrumento === "echeque" ? (
                <>
                  <span className="instrumento-badge">
                    {movimiento.instrumento === "cheque" ? "Cheque" : "Echeque"}
                  </span>{" "}
                  {movimiento.estado === "pendiente" ? (
                    <span className="estado-badge estado-badge--pendiente">Pendiente</span>
                  ) : (
                    <span className="estado-badge estado-badge--liquidado">Liquidado</span>
                  )}{" "}
                </>
              ) : null}
              {movimiento.tipo === "salida" ? "-" : ""}
              {movimiento.monto}{" "}
              <span className="movimiento-moneda-badge">{movimiento.moneda}</span>
            </td>
            <td data-label="Subtotal">{movimiento.subtotal ?? "—"}</td>
            {showValorTotal ? (
              <td data-label="Valor de caja total">{movimiento.valor_total ?? "—"}</td>
            ) : null}
            <td data-label="Fecha">
              {formatFecha(movimiento.fecha)}
              {movimiento.estado === "pendiente" && movimiento.fecha_liquidacion ? (
                <span className="movimiento-fecha-liquidacion">
                  Liquida el {formatFechaIso(movimiento.fecha_liquidacion)}
                </span>
              ) : null}
            </td>
            {showActions ? (
              <td className="movimiento-table-actions" data-label="Acciones">
                <div className="movimiento-table-actions-inner">
                  {movimiento.liquidable && onLiquidar ? (
                    <button
                      type="button"
                      className="btn-table-action btn-table-action-edit"
                      onClick={() => onLiquidar(movimiento)}
                      disabled={!llegoFechaLiquidacion(movimiento.fecha_liquidacion)}
                      title={
                        llegoFechaLiquidacion(movimiento.fecha_liquidacion)
                          ? undefined
                          : `Disponible desde el ${formatFechaIso(movimiento.fecha_liquidacion)}`
                      }
                    >
                      Liquidar
                    </button>
                  ) : null}
                  {movimiento.endosable && onEndosar ? (
                    <button
                      type="button"
                      className="btn-table-action btn-table-action-edit"
                      onClick={() => onEndosar(movimiento)}
                    >
                      Endose
                    </button>
                  ) : null}
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

import { useEffect, useState } from "react";

import {
  fetchChequesPendientes,
  type Movimiento,
  type MovimientoFiltros,
} from "../services/api";
import { formatFechaCarga, formatFechaIso, llegoFechaLiquidacion } from "../utils/fechas";
import EndoseDialog from "./EndoseDialog";
import Pagination from "./Pagination";

type ChequesPendientesBlockProps = {
  cajaId: number | null;
  /** Bump to force a reload (after create / edit / delete / liquidar). */
  refreshKey?: number;
  /** Consulta mode: no actions. */
  readOnly?: boolean;
  /**
   * Liquidate a pending cheque (Registro only). Must reject on failure. When absent the
   * block offers no Liquidar action.
   */
  onLiquidar?: (cheque: Movimiento) => Promise<void>;
  /**
   * Endorse a pending cheque to another caja (Registro only, secretaria). Must reject on
   * failure. When absent the block offers no Endose action.
   */
  onEndosar?: (cheque: Movimiento, cajaDestinoId: number) => Promise<void>;
  /** Open the edit panel for a pending cheque (Registro only). */
  onEdit?: (cheque: Movimiento) => void;
  /** Delete a pending cheque (Registro only). Must reject on failure. */
  onDelete?: (cheque: Movimiento) => Promise<void>;
  /** Same moneda / fecha filters as the movimientos listing (Registro). */
  filtros?: MovimientoFiltros;
  /** Hide the heading when the surrounding UI already labels the list (Registro toggle). */
  showTitle?: boolean;
};

const INSTRUMENTO_LABEL: Record<string, string> = {
  cheque: "Cheque",
  echeque: "Echeque",
};

export default function ChequesPendientesBlock({
  cajaId,
  refreshKey = 0,
  readOnly = false,
  onLiquidar,
  onEndosar,
  onEdit,
  onDelete,
  filtros,
  showTitle = true,
}: ChequesPendientesBlockProps) {
  const [items, setItems] = useState<Movimiento[]>([]);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [liquidandoId, setLiquidandoId] = useState<number | null>(null);
  // 011: cheque whose Endose dialog is open.
  const [endosando, setEndosando] = useState<Movimiento | null>(null);
  // Reload trigger owned by the block itself (after a successful liquidation).
  const [localRefresh, setLocalRefresh] = useState(0);
  const moneda = filtros?.moneda || undefined;
  const fechaDesde = filtros?.fecha_desde || undefined;
  const fechaHasta = filtros?.fecha_hasta || undefined;
  // The page belongs to a caja + filter set: changing either always restarts at page 1.
  const scopeKey = `${cajaId ?? ""}|${moneda ?? ""}|${fechaDesde ?? ""}|${fechaHasta ?? ""}`;
  const [cursor, setCursor] = useState<{ scopeKey: string; page: number }>({
    scopeKey,
    page: 1,
  });
  const page = cursor.scopeKey === scopeKey ? cursor.page : 1;

  useEffect(() => {
    if (cajaId === null) {
      setItems([]);
      setTotalPages(0);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchChequesPendientes(cajaId, page, {
      moneda,
      fecha_desde: fechaDesde,
      fecha_hasta: fechaHasta,
    })
      .then((response) => {
        if (cancelled) {
          return;
        }
        // The last cheque of the last page was settled/deleted: step back one page.
        if (response.items.length === 0 && page > 1 && response.total_pages > 0) {
          setCursor({ scopeKey, page: response.total_pages });
          return;
        }
        setItems(response.items);
        setTotalPages(response.total_pages);
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
          setTotalPages(0);
          setError("No se pudieron cargar los cheques pendientes.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [cajaId, refreshKey, localRefresh, page, scopeKey, moneda, fechaDesde, fechaHasta]);

  const canAct =
    !readOnly &&
    (onLiquidar !== undefined ||
      onEndosar !== undefined ||
      onEdit !== undefined ||
      onDelete !== undefined);

  async function runAction(
    cheque: Movimiento,
    confirmMessage: string,
    failureMessage: string,
    action: (cheque: Movimiento) => Promise<void>,
  ) {
    if (liquidandoId !== null) {
      return;
    }
    if (!window.confirm(confirmMessage)) {
      return;
    }

    setLiquidandoId(cheque.id);
    setActionError(null);
    try {
      await action(cheque);
      setLocalRefresh((key) => key + 1);
    } catch {
      setActionError(failureMessage);
    } finally {
      setLiquidandoId(null);
    }
  }

  function handleLiquidar(cheque: Movimiento) {
    if (!onLiquidar) {
      return;
    }
    void runAction(
      cheque,
      "¿Liquidar este cheque? Pasará a impactar el Valor de caja.",
      "No se pudo liquidar el cheque.",
      onLiquidar,
    );
  }

  async function handleConfirmEndose(cajaDestinoId: number) {
    if (!endosando || !onEndosar) {
      return;
    }
    // A rejection propagates to the dialog, which shows a generic error and stays open.
    await onEndosar(endosando, cajaDestinoId);
    setEndosando(null);
    setActionError(null);
    setLocalRefresh((key) => key + 1);
  }

  function handleDelete(cheque: Movimiento) {
    if (!onDelete) {
      return;
    }
    void runAction(
      cheque,
      "¿Eliminar este cheque pendiente? No afecta el Valor de caja.",
      "No se pudo eliminar el cheque.",
      onDelete,
    );
  }

  const content = (
    <>
      {error ? <p className="form-error">{error}</p> : null}
      {actionError ? (
        <p className="form-error" role="alert">
          {actionError}
        </p>
      ) : null}

      <table className="movimiento-table cheques-table">
        <thead>
          <tr>
            <th>Descripción</th>
            <th>Monto</th>
            <th>Instrumento</th>
            <th>Fecha de carga</th>
            <th>Fecha de liquidación</th>
            {canAct ? <th>Acciones</th> : null}
          </tr>
        </thead>
        <tbody>
          {items.length === 0 && !error ? (
            <tr>
              <td colSpan={canAct ? 6 : 5} className="movimiento-table-empty">
                {loading ? "Cargando…" : "No hay cheques pendientes."}
              </td>
            </tr>
          ) : null}
          {items.map((cheque) => (
            <tr key={cheque.id}>
              <td data-label="Descripción">{cheque.descripcion}</td>
              <td
                data-label="Monto"
                className={
                  cheque.tipo === "entrada" ? "movimiento-entrada" : "movimiento-salida"
                }
              >
                {cheque.tipo === "salida" ? "-" : ""}
                {cheque.monto}{" "}
                <span className="movimiento-moneda-badge">{cheque.moneda}</span>
              </td>
              <td data-label="Instrumento">
                <span className="instrumento-badge">
                  {INSTRUMENTO_LABEL[cheque.instrumento] ?? cheque.instrumento}
                </span>
              </td>
              <td data-label="Fecha de carga">{formatFechaCarga(cheque.fecha_carga)}</td>
              <td data-label="Fecha de liquidación">
                {formatFechaIso(cheque.fecha_liquidacion)}
              </td>
              {canAct ? (
                <td className="movimiento-table-actions" data-label="Acciones">
                  <div className="movimiento-table-actions-inner">
                    {onLiquidar && cheque.liquidable ? (
                      <button
                        type="button"
                        className="btn-table-action btn-table-action-edit"
                        onClick={() => handleLiquidar(cheque)}
                        disabled={
                          liquidandoId !== null ||
                          !llegoFechaLiquidacion(cheque.fecha_liquidacion)
                        }
                        title={
                          llegoFechaLiquidacion(cheque.fecha_liquidacion)
                            ? undefined
                            : `Disponible desde el ${formatFechaIso(cheque.fecha_liquidacion)}`
                        }
                      >
                        Liquidar
                      </button>
                    ) : null}
                    {onEndosar && cheque.endosable ? (
                      <button
                        type="button"
                        className="btn-table-action btn-table-action-edit"
                        onClick={() => setEndosando(cheque)}
                        disabled={liquidandoId !== null}
                      >
                        Endose
                      </button>
                    ) : null}
                    {onEdit && cheque.editable ? (
                      <button
                        type="button"
                        className="btn-table-action btn-table-action-edit"
                        onClick={() => onEdit(cheque)}
                        disabled={liquidandoId !== null}
                      >
                        Editar
                      </button>
                    ) : null}
                    {onDelete && cheque.editable ? (
                      <button
                        type="button"
                        className="btn-table-action btn-table-action-delete"
                        onClick={() => handleDelete(cheque)}
                        disabled={liquidandoId !== null}
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

      <Pagination
        page={page}
        totalPages={totalPages}
        onPageChange={(next) => setCursor({ scopeKey, page: next })}
        disabled={loading}
      />
    </>
  );

  return (
    <section
      className={`cheques-pendientes${readOnly ? " cheques-pendientes--readonly" : ""}`}
      aria-live="polite"
    >
      {showTitle ? <h2>Cheques pendientes</h2> : null}
      {content}
      {endosando && onEndosar && !readOnly ? (
        <EndoseDialog
          cajaOrigenId={endosando.caja.id}
          onConfirm={handleConfirmEndose}
          onCancel={() => setEndosando(null)}
        />
      ) : null}
    </section>
  );
}

import { useEffect, useId, useState } from "react";

import EndoseDialog from "../components/EndoseDialog";
import Pagination from "../components/Pagination";
import { useAuth } from "../hooks/useAuth";
import {
  endosarCheque,
  fetchCheques,
  liquidarCheque,
  type ChequeCategoria,
  type Movimiento,
} from "../services/api";
import { formatFechaCarga, formatFechaIso, llegoFechaLiquidacion } from "../utils/fechas";

const INSTRUMENTO_LABEL: Record<string, string> = {
  cheque: "Cheque",
  echeque: "Echeque",
};

type ChequesListadoProps = {
  categoria: ChequeCategoria;
  titulo: string;
  emptyText: string;
  block: string;
  refreshKey: number;
  canAct: boolean;
  liquidandoId: number | null;
  onLiquidar: (cheque: Movimiento) => void;
  onEndosar: (cheque: Movimiento) => void;
};

function ChequesListado({
  categoria,
  titulo,
  emptyText,
  block,
  refreshKey,
  canAct,
  liquidandoId,
  onLiquidar,
  onEndosar,
}: ChequesListadoProps) {
  const headingId = useId();
  const [items, setItems] = useState<Movimiento[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchCheques(categoria, page)
      .then((response) => {
        if (cancelled) {
          return;
        }
        // The last row of the last page was settled: step back one page.
        if (response.items.length === 0 && page > 1 && response.total_pages > 0) {
          setPage(response.total_pages);
          return;
        }
        setItems(response.items);
        setTotalPages(response.total_pages);
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
          setTotalPages(0);
          setError("No se pudieron cargar los cheques.");
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
  }, [categoria, page, refreshKey]);

  const columns = canAct ? 9 : 8;

  return (
    <section className="page-block" data-block={block} aria-labelledby={headingId}>
      <h2 id={headingId}>{titulo}</h2>

      {error ? <p className="form-error">{error}</p> : null}

      <table className="movimiento-table cheques-seccion-table">
        <thead>
          <tr>
            <th>Caja</th>
            <th>Instrumento</th>
            <th>Descripción</th>
            <th>Tipo</th>
            <th>Moneda</th>
            <th>Monto</th>
            <th>Fecha de carga</th>
            <th>Fecha de liquidación</th>
            {canAct ? <th>Acciones</th> : null}
          </tr>
        </thead>
        <tbody>
          {items.length === 0 && !error ? (
            <tr>
              <td colSpan={columns} className="movimiento-table-empty">
                {loading ? "Cargando…" : emptyText}
              </td>
            </tr>
          ) : null}
          {items.map((cheque) => (
            <tr key={cheque.id}>
              <td data-label="Caja">{cheque.caja.nombre}</td>
              <td data-label="Instrumento">
                <span className="instrumento-badge">
                  {INSTRUMENTO_LABEL[cheque.instrumento] ?? cheque.instrumento}
                </span>
              </td>
              <td data-label="Descripción">{cheque.descripcion}</td>
              <td data-label="Tipo">{cheque.tipo === "entrada" ? "Entrada" : "Salida"}</td>
              <td data-label="Moneda">
                <span className="movimiento-moneda-badge">{cheque.moneda}</span>
              </td>
              <td
                data-label="Monto"
                className={
                  cheque.tipo === "entrada" ? "movimiento-entrada" : "movimiento-salida"
                }
              >
                {cheque.monto}
              </td>
              <td data-label="Fecha de carga">{formatFechaCarga(cheque.fecha_carga)}</td>
              <td data-label="Fecha de liquidación">
                {formatFechaIso(cheque.fecha_liquidacion)}
              </td>
              {canAct ? (
                <td className="movimiento-table-actions" data-label="Acciones">
                  <div className="movimiento-table-actions-inner">
                    {cheque.liquidable ? (
                      <button
                        type="button"
                        className="btn-table-action btn-table-action-edit"
                        onClick={() => onLiquidar(cheque)}
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
                    {cheque.endosable ? (
                      <button
                        type="button"
                        className="btn-table-action btn-table-action-edit"
                        onClick={() => onEndosar(cheque)}
                        disabled={liquidandoId !== null}
                      >
                        Endose
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
        onPageChange={setPage}
        disabled={loading}
      />
    </section>
  );
}

export default function ChequesPage() {
  const { rol } = useAuth();
  const canAct = rol === "secretaria";
  const [refreshKey, setRefreshKey] = useState(0);
  const [liquidandoId, setLiquidandoId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  // 011: cheque whose Endose dialog is open (origin caja = cheque.caja).
  const [endosando, setEndosando] = useState<Movimiento | null>(null);

  async function handleEndosar(cajaDestinoId: number) {
    if (!endosando) {
      return;
    }
    // A rejection propagates to the dialog, which shows a generic error and stays open.
    await endosarCheque(endosando.caja.id, endosando.id, cajaDestinoId);
    setEndosando(null);
    setError(null);
    setRefreshKey((key) => key + 1);
  }

  async function handleLiquidar(cheque: Movimiento) {
    if (liquidandoId !== null) {
      return;
    }
    const confirmed = window.confirm(
      "¿Liquidar este cheque? Pasará a impactar el Valor de caja.",
    );
    if (!confirmed) {
      return;
    }

    setLiquidandoId(cheque.id);
    setError(null);
    try {
      await liquidarCheque(cheque.caja.id, cheque.id);
      setRefreshKey((key) => key + 1);
    } catch {
      setError("No se pudo liquidar el cheque.");
    } finally {
      setLiquidandoId(null);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header page-block" data-block="titulo">
        <h1>Cheques</h1>
      </header>

      {error ? (
        <p className="form-error page-block" data-block="error" role="alert">
          {error}
        </p>
      ) : null}

      <ChequesListado
        categoria="aptos"
        titulo="Aptos para liquidar"
        emptyText="No hay cheques aptos para liquidar."
        block="cheques-aptos"
        refreshKey={refreshKey}
        canAct={canAct}
        liquidandoId={liquidandoId}
        onLiquidar={(cheque) => void handleLiquidar(cheque)}
        onEndosar={setEndosando}
      />
      <ChequesListado
        categoria="proximos"
        titulo="Próximos a liquidar este mes"
        emptyText="No hay cheques próximos a liquidar este mes."
        block="cheques-proximos"
        refreshKey={refreshKey}
        canAct={canAct}
        liquidandoId={liquidandoId}
        onLiquidar={(cheque) => void handleLiquidar(cheque)}
        onEndosar={setEndosando}
      />
      {canAct && endosando ? (
        <EndoseDialog
          cajaOrigenId={endosando.caja.id}
          onConfirm={handleEndosar}
          onCancel={() => setEndosando(null)}
        />
      ) : null}
    </div>
  );
}

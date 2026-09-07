import { FormEvent, useCallback, useEffect, useState } from "react";

import CajaSelector from "../components/CajaSelector";
import MovimientoForm from "../components/MovimientoForm";
import MovimientoTable from "../components/MovimientoTable";
import Pagination from "../components/Pagination";
import {
  apiGet,
  apiPost,
  deleteMovimiento,
  updateMovimiento,
  type Caja,
  type CajaSaldo,
  type CreateMovimientoPayload,
  type Movimiento,
  type MovimientoCreateResponse,
  type MovimientoFiltros,
  type PaginatedMovimientos,
} from "../services/api";

export default function RegistroCajaPage() {
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [selectedCajaId, setSelectedCajaId] = useState<number | null>(null);
  const [saldo, setSaldo] = useState<CajaSaldo | null>(null);
  const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingMovimiento, setEditingMovimiento] = useState<Movimiento | null>(
    null,
  );
  const [editDescripcion, setEditDescripcion] = useState("");
  const [editMonto, setEditMonto] = useState("");
  const [editTipo, setEditTipo] = useState<"entrada" | "salida">("entrada");

  // ── Filtros US3 ──────────────────────────────────────────────────────────
  const [filtroMoneda, setFiltroMoneda] = useState<"ARS" | "USD" | "">("");
  const [filtroFechaDesde, setFiltroFechaDesde] = useState("");
  const [filtroFechaHasta, setFiltroFechaHasta] = useState("");

  const buildFiltros = useCallback((): MovimientoFiltros => {
    const filtros: MovimientoFiltros = {};
    if (filtroMoneda) filtros.moneda = filtroMoneda;
    if (filtroFechaDesde) filtros.fecha_desde = filtroFechaDesde;
    if (filtroFechaHasta) filtros.fecha_hasta = filtroFechaHasta;
    return filtros;
  }, [filtroMoneda, filtroFechaDesde, filtroFechaHasta]);

  const loadCajaData = useCallback(
    async (cajaId: number, currentPage: number, filtros?: MovimientoFiltros) => {
      const params = new URLSearchParams({ page: String(currentPage) });
      if (filtros?.moneda) params.set("moneda", filtros.moneda);
      if (filtros?.fecha_desde) params.set("fecha_desde", filtros.fecha_desde);
      if (filtros?.fecha_hasta) params.set("fecha_hasta", filtros.fecha_hasta);

      const [saldoResponse, movimientosResponse] = await Promise.all([
        apiGet<CajaSaldo>(`/api/v1/cajas/${cajaId}/saldo`),
        apiGet<PaginatedMovimientos>(
          `/api/v1/cajas/${cajaId}/movimientos?${params.toString()}`,
        ),
      ]);

      setSaldo(saldoResponse);
      setMovimientos(movimientosResponse.items);
      setPage(movimientosResponse.page);
      setTotalPages(movimientosResponse.total_pages);
    },
    [],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadInitialData() {
      setLoading(true);
      setError(null);

      try {
        const cajasResponse = await apiGet<Caja[]>("/api/v1/cajas");
        if (cancelled) {
          return;
        }

        setCajas(cajasResponse);
        const firstCajaId = cajasResponse[0]?.id ?? null;
        setSelectedCajaId(firstCajaId);

        if (firstCajaId) {
          await loadCajaData(firstCajaId, 1);
        }
      } catch {
        if (!cancelled) {
          setError("No se pudieron cargar las cajas.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadInitialData();

    return () => {
      cancelled = true;
    };
  }, [loadCajaData]);

  async function handleCajaChange(cajaId: number) {
    setSelectedCajaId(cajaId);
    setFiltroMoneda("");
    setFiltroFechaDesde("");
    setFiltroFechaHasta("");
    setLoading(true);
    setError(null);

    try {
      await loadCajaData(cajaId, 1);
    } catch {
      setError("No se pudieron cargar los datos de la caja.");
    } finally {
      setLoading(false);
    }
  }

  async function handlePageChange(nextPage: number) {
    if (!selectedCajaId) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await loadCajaData(selectedCajaId, nextPage, buildFiltros());
    } catch {
      setError("No se pudieron cargar los movimientos.");
    } finally {
      setLoading(false);
    }
  }

  async function handleFiltroChange(newFiltros: MovimientoFiltros) {
    if (!selectedCajaId) return;
    setLoading(true);
    setError(null);
    try {
      await loadCajaData(selectedCajaId, 1, newFiltros);
    } catch {
      setError("No se pudieron cargar los movimientos.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateMovimiento(
    payload: CreateMovimientoPayload,
    additionalCajaIds: number[],
  ) {
    if (!selectedCajaId) {
      return;
    }

    const targetCajaIds = [selectedCajaId, ...additionalCajaIds];

    await Promise.all(
      targetCajaIds.map((cajaId) =>
        apiPost<MovimientoCreateResponse>(`/api/v1/cajas/${cajaId}/movimientos`, payload),
      ),
    );
    await loadCajaData(selectedCajaId, 1);
  }

  function handleStartEdit(movimiento: Movimiento) {
    setEditingMovimiento(movimiento);
    setEditDescripcion(movimiento.descripcion);
    setEditMonto(movimiento.monto);
    setEditTipo(movimiento.tipo);
    setError(null);
  }

  function handleCancelEdit() {
    setEditingMovimiento(null);
    setEditDescripcion("");
    setEditMonto("");
    setEditTipo("entrada");
  }

  async function handleSaveEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCajaId || !editingMovimiento) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await updateMovimiento(selectedCajaId, editingMovimiento.id, {
        descripcion: editDescripcion,
        monto: editMonto,
        tipo: editTipo,
      });
      handleCancelEdit();
      await loadCajaData(selectedCajaId, page);
    } catch {
      setError("No se pudo actualizar el movimiento.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(movimiento: Movimiento) {
    if (!selectedCajaId) {
      return;
    }

    const confirmed = window.confirm(
      "¿Eliminar este movimiento? Se recalcularán los subtotales posteriores.",
    );
    if (!confirmed) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await deleteMovimiento(selectedCajaId, movimiento.id);
      if (editingMovimiento?.id === movimiento.id) {
        handleCancelEdit();
      }
      await loadCajaData(selectedCajaId, page);
    } catch {
      setError("No se pudo eliminar el movimiento.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header page-block" data-block="titulo">
        <h1>Registro de caja</h1>
      </header>

      {error ? (
        <p className="form-error page-block" data-block="error">
          {error}
        </p>
      ) : null}

      <div className="page-block" data-block="selector">
        <CajaSelector
          cajas={cajas}
          selectedCajaId={selectedCajaId}
          onChange={handleCajaChange}
          disabled={loading}
        />
      </div>

      <section className="saldo-panel page-block" data-block="saldo" aria-live="polite">
        <h2>Valor de caja</h2>
        {saldo ? (
          <div className="saldo-dual">
            <p className="saldo-valor">
              <span className="saldo-moneda-label">ARS</span>
              {` $ ${saldo.saldo_ars}`}
            </p>
            <p className="saldo-valor">
              <span className="saldo-moneda-label">USD</span>
              {` $ ${saldo.saldo_usd}`}
            </p>
          </div>
        ) : (
          <p className="saldo-valor">{loading ? "Cargando…" : "—"}</p>
        )}
      </section>

      <div className="page-block" data-block="formulario">
        <MovimientoForm
          cajas={cajas}
          activeCajaId={selectedCajaId}
          onSubmit={handleCreateMovimiento}
          disabled={loading}
        />
      </div>

      {editingMovimiento ? (
        <section className="movimiento-edit-panel page-block" data-block="edicion">
          <h2>Editar movimiento</h2>
          <form onSubmit={handleSaveEdit}>
            <label className="field">
              <span>Descripción</span>
              <input
                name="edit-descripcion"
                type="text"
                value={editDescripcion}
                disabled={loading}
                onChange={(event) => setEditDescripcion(event.target.value)}
                required
              />
            </label>

            <label className="field">
              <span>Monto</span>
              <input
                name="edit-monto"
                type="text"
                inputMode="decimal"
                value={editMonto}
                disabled={loading}
                onChange={(event) => setEditMonto(event.target.value)}
                required
              />
            </label>

            <label className="field">
              <span>Tipo</span>
              <select
                name="edit-tipo"
                value={editTipo}
                disabled={loading}
                onChange={(event) =>
                  setEditTipo(event.target.value as "entrada" | "salida")
                }
              >
                <option value="entrada">Entrada</option>
                <option value="salida">Salida</option>
              </select>
            </label>

            <div className="movimiento-edit-actions">
              <button
                type="submit"
                className="button button--primary"
                disabled={loading}
              >
                Guardar
              </button>
              <button
                type="button"
                className="button button--secondary"
                disabled={loading}
                onClick={handleCancelEdit}
              >
                Cancelar
              </button>
            </div>
          </form>
        </section>
      ) : null}

      <div className="page-block movimiento-filtros" data-block="filtros">
        <div className="field field--inline">
          <span className="filtro-label" aria-hidden="true">Moneda</span>
          <select
            id="filtro-moneda"
            aria-label="Filtrar por divisa"
            value={filtroMoneda}
            disabled={loading}
            onChange={(e) => {
              const val = e.target.value as "ARS" | "USD" | "";
              setFiltroMoneda(val);
              void handleFiltroChange({
                moneda: val,
                fecha_desde: filtroFechaDesde || undefined,
                fecha_hasta: filtroFechaHasta || undefined,
              });
            }}
          >
            <option value="">Todas</option>
            <option value="ARS">ARS</option>
            <option value="USD">USD</option>
          </select>
        </div>

        <label className="field field--inline" htmlFor="filtro-fecha-desde">
          <span>Desde</span>
          <input
            id="filtro-fecha-desde"
            type="date"
            value={filtroFechaDesde}
            disabled={loading}
            onChange={(e) => {
              const val = e.target.value;
              setFiltroFechaDesde(val);
              void handleFiltroChange({
                moneda: filtroMoneda || undefined,
                fecha_desde: val || undefined,
                fecha_hasta: filtroFechaHasta || undefined,
              });
            }}
          />
        </label>

        <label className="field field--inline" htmlFor="filtro-fecha-hasta">
          <span>Hasta</span>
          <input
            id="filtro-fecha-hasta"
            type="date"
            value={filtroFechaHasta}
            disabled={loading}
            onChange={(e) => {
              const val = e.target.value;
              setFiltroFechaHasta(val);
              void handleFiltroChange({
                moneda: filtroMoneda || undefined,
                fecha_desde: filtroFechaDesde || undefined,
                fecha_hasta: val || undefined,
              });
            }}
          />
        </label>
      </div>

      <div className="page-block" data-block="historial">
        <MovimientoTable
          movimientos={movimientos}
          onEdit={handleStartEdit}
          onDelete={handleDelete}
        />
      </div>

      <div className="page-block" data-block="paginacion">
        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={handlePageChange}
          disabled={loading}
        />
      </div>
    </div>
  );
}

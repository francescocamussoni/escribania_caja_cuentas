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

  const loadCajaData = useCallback(async (cajaId: number, currentPage: number) => {
    const [saldoResponse, movimientosResponse] = await Promise.all([
      apiGet<CajaSaldo>(`/api/v1/cajas/${cajaId}/saldo`),
      apiGet<PaginatedMovimientos>(
        `/api/v1/cajas/${cajaId}/movimientos?page=${currentPage}`,
      ),
    ]);

    setSaldo(saldoResponse);
    setMovimientos(movimientosResponse.items);
    setPage(movimientosResponse.page);
    setTotalPages(movimientosResponse.total_pages);
  }, []);

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
      await loadCajaData(selectedCajaId, nextPage);
    } catch {
      setError("No se pudieron cargar los movimientos.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateMovimiento(payload: CreateMovimientoPayload) {
    if (!selectedCajaId) {
      return;
    }

    await apiPost<Movimiento>(
      `/api/v1/cajas/${selectedCajaId}/movimientos`,
      payload,
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
    <main className="app-shell registro-caja-page">
      <h1>Registro de caja</h1>

      {error ? <p className="form-error">{error}</p> : null}

      <CajaSelector
        cajas={cajas}
        selectedCajaId={selectedCajaId}
        onChange={handleCajaChange}
        disabled={loading}
      />

      <section className="saldo-panel" aria-live="polite">
        <h2>Valor de caja</h2>
        <p className="saldo-valor">
          {saldo ? `$ ${saldo.saldo_actual}` : loading ? "Cargando…" : "—"}
        </p>
      </section>

      <MovimientoForm onSubmit={handleCreateMovimiento} disabled={loading} />

      {editingMovimiento ? (
        <section className="movimiento-edit-panel">
          <h2>Editar movimiento</h2>
          <form onSubmit={handleSaveEdit}>
            <label htmlFor="edit-descripcion">Descripción</label>
            <input
              id="edit-descripcion"
              name="edit-descripcion"
              type="text"
              value={editDescripcion}
              disabled={loading}
              onChange={(event) => setEditDescripcion(event.target.value)}
              required
            />

            <label htmlFor="edit-monto">Monto</label>
            <input
              id="edit-monto"
              name="edit-monto"
              type="text"
              inputMode="decimal"
              value={editMonto}
              disabled={loading}
              onChange={(event) => setEditMonto(event.target.value)}
              required
            />

            <label htmlFor="edit-tipo">Tipo</label>
            <select
              id="edit-tipo"
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

            <div className="movimiento-edit-actions">
              <button type="submit" disabled={loading}>
                Guardar
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={loading}
                onClick={handleCancelEdit}
              >
                Cancelar
              </button>
            </div>
          </form>
        </section>
      ) : null}

      <MovimientoTable
        movimientos={movimientos}
        onEdit={handleStartEdit}
        onDelete={handleDelete}
      />

      <Pagination
        page={page}
        totalPages={totalPages}
        onPageChange={handlePageChange}
        disabled={loading}
      />
    </main>
  );
}

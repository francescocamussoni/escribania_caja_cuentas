import { FormEvent, useCallback, useEffect, useState } from "react";

import CajaSelector from "../components/CajaSelector";
import PlazoFijoForm from "../components/PlazoFijoForm";
import PlazoFijoTable from "../components/PlazoFijoTable";
import PlazosFijosResumenPanel from "../components/PlazosFijosResumenPanel";
import Pagination from "../components/Pagination";
import {
  apiGet,
  apiPost,
  deletePlazoFijo,
  updatePlazoFijo,
  type Caja,
  type CreatePlazoFijoPayload,
  type PaginatedPlazosFijos,
  type PlazoFijo,
  type PlazosFijosResumen,
  type UpdatePlazoFijoPayload,
} from "../services/api";

export default function PlazosFijosPage() {
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [selectedCajaId, setSelectedCajaId] = useState<number | null>(null);
  const [resumen, setResumen] = useState<PlazosFijosResumen | null>(null);
  const [plazosFijos, setPlazosFijos] = useState<PlazoFijo[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingPlazoFijo, setEditingPlazoFijo] = useState<PlazoFijo | null>(null);
  const [editMontoIngresado, setEditMontoIngresado] = useState("");
  const [editMontoAVencimiento, setEditMontoAVencimiento] = useState("");
  const [editFechaVencimiento, setEditFechaVencimiento] = useState("");

  const loadCajaData = useCallback(async (cajaId: number, currentPage: number) => {
    const [resumenResponse, plazosFijosResponse] = await Promise.all([
      apiGet<PlazosFijosResumen>(`/api/v1/cajas/${cajaId}/plazos-fijos/resumen`),
      apiGet<PaginatedPlazosFijos>(
        `/api/v1/cajas/${cajaId}/plazos-fijos?page=${currentPage}`,
      ),
    ]);

    setResumen(resumenResponse);
    setPlazosFijos(plazosFijosResponse.items);
    setPage(plazosFijosResponse.page);
    setTotalPages(plazosFijosResponse.total_pages);
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
    handleCancelEdit();

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
      setError("No se pudieron cargar los plazos fijos.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreatePlazoFijo(payload: CreatePlazoFijoPayload) {
    if (!selectedCajaId) {
      return;
    }

    await apiPost<PlazoFijo>(
      `/api/v1/cajas/${selectedCajaId}/plazos-fijos`,
      payload,
    );
    await loadCajaData(selectedCajaId, 1);
  }

  function handleStartEdit(plazoFijo: PlazoFijo) {
    setEditingPlazoFijo(plazoFijo);
    setEditMontoIngresado(plazoFijo.monto_ingresado);
    setEditMontoAVencimiento(plazoFijo.monto_a_vencimiento);
    setEditFechaVencimiento(plazoFijo.fecha_vencimiento);
    setError(null);
  }

  function handleCancelEdit() {
    setEditingPlazoFijo(null);
    setEditMontoIngresado("");
    setEditMontoAVencimiento("");
    setEditFechaVencimiento("");
  }

  async function handleSaveEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCajaId || !editingPlazoFijo) {
      return;
    }

    setLoading(true);
    setError(null);

    const payload: UpdatePlazoFijoPayload = {};

    if (editMontoIngresado !== editingPlazoFijo.monto_ingresado) {
      payload.monto_ingresado = editMontoIngresado;
    }
    if (editMontoAVencimiento !== editingPlazoFijo.monto_a_vencimiento) {
      payload.monto_a_vencimiento = editMontoAVencimiento;
    }
    if (editFechaVencimiento !== editingPlazoFijo.fecha_vencimiento) {
      payload.fecha_vencimiento = editFechaVencimiento;
    }

    try {
      await updatePlazoFijo(selectedCajaId, editingPlazoFijo.id, payload);
      handleCancelEdit();
      await loadCajaData(selectedCajaId, page);
    } catch {
      setError("No se pudo actualizar el plazo fijo.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(plazoFijo: PlazoFijo) {
    if (!selectedCajaId) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await deletePlazoFijo(selectedCajaId, plazoFijo.id);
      if (editingPlazoFijo?.id === plazoFijo.id) {
        handleCancelEdit();
      }
      await loadCajaData(selectedCajaId, page);
    } catch {
      setError("No se pudo eliminar el plazo fijo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header page-block" data-block="titulo">
        <h1>Plazos fijos</h1>
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

      <div className="page-block" data-block="resumen">
        <PlazosFijosResumenPanel
          totalMontoIngresado={resumen?.total_monto_ingresado_activos ?? null}
          totalMontoAVencimiento={resumen?.total_monto_a_vencimiento_activos ?? null}
          loading={loading && !resumen}
        />
      </div>

      <div className="page-block" data-block="formulario">
        <PlazoFijoForm onSubmit={handleCreatePlazoFijo} disabled={loading} />
      </div>

      {editingPlazoFijo ? (
        <section className="movimiento-edit-panel plazo-fijo-edit-panel page-block" data-block="edicion">
          <h2>Editar plazo fijo</h2>
          <form onSubmit={handleSaveEdit}>
            <label className="field">
              <span>Monto ingresado</span>
              <input
                name="edit-monto-ingresado"
                type="text"
                inputMode="decimal"
                value={editMontoIngresado}
                disabled={loading}
                onChange={(event) => setEditMontoIngresado(event.target.value)}
                required
              />
            </label>

            <label className="field">
              <span>Fecha de vencimiento</span>
              <input
                name="edit-fecha-vencimiento"
                type="date"
                value={editFechaVencimiento}
                disabled={loading}
                onChange={(event) => setEditFechaVencimiento(event.target.value)}
                required
              />
            </label>

            <label className="field">
              <span>Monto a vencimiento</span>
              <input
                name="edit-monto-a-vencimiento"
                type="text"
                inputMode="decimal"
                value={editMontoAVencimiento}
                disabled={loading}
                onChange={(event) => setEditMontoAVencimiento(event.target.value)}
                required
              />
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

      <div className="page-block" data-block="listado">
        <PlazoFijoTable
          plazosFijos={plazosFijos}
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

import { useCallback, useEffect, useState } from "react";

import CajaSelector from "../components/CajaSelector";
import MovimientoTable from "../components/MovimientoTable";
import Pagination from "../components/Pagination";
import {
  apiGet,
  type Caja,
  type CajaSaldo,
  type Movimiento,
  type PaginatedMovimientos,
} from "../services/api";

export default function ConsultaCajaPage() {
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [selectedCajaId, setSelectedCajaId] = useState<number | null>(null);
  const [saldo, setSaldo] = useState<CajaSaldo | null>(null);
  const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loadingCajas, setLoadingCajas] = useState(true);
  const [loadingConsulta, setLoadingConsulta] = useState(false);
  const [hasConsulted, setHasConsulted] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    setHasConsulted(true);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadCajas() {
      setLoadingCajas(true);
      setError(null);

      try {
        const cajasResponse = await apiGet<Caja[]>("/api/v1/cajas");
        if (cancelled) {
          return;
        }

        setCajas(cajasResponse);
        setSelectedCajaId(cajasResponse[0]?.id ?? null);
      } catch {
        if (!cancelled) {
          setError("No se pudieron cargar las cajas.");
        }
      } finally {
        if (!cancelled) {
          setLoadingCajas(false);
        }
      }
    }

    void loadCajas();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleConsulta() {
    if (!selectedCajaId) {
      return;
    }

    setLoadingConsulta(true);
    setError(null);

    try {
      await loadCajaData(selectedCajaId, 1);
    } catch {
      setError("No se pudieron cargar los datos de la caja.");
    } finally {
      setLoadingConsulta(false);
    }
  }

  async function handleCajaChange(cajaId: number) {
    setSelectedCajaId(cajaId);
    setSaldo(null);
    setMovimientos([]);
    setPage(1);
    setTotalPages(0);
    setHasConsulted(false);
  }

  async function handlePageChange(nextPage: number) {
    if (!selectedCajaId) {
      return;
    }

    setLoadingConsulta(true);
    setError(null);

    try {
      await loadCajaData(selectedCajaId, nextPage);
    } catch {
      setError("No se pudieron cargar los movimientos.");
    } finally {
      setLoadingConsulta(false);
    }
  }

  const isBusy = loadingCajas || loadingConsulta;

  return (
    <>
      <header className="page-header">
        <h1>Consulta de caja</h1>
      </header>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="consulta-controls">
        <CajaSelector
          cajas={cajas}
          selectedCajaId={selectedCajaId}
          onChange={handleCajaChange}
          disabled={isBusy}
        />
        <button
          type="button"
          className="button button--primary"
          disabled={isBusy || !selectedCajaId}
          onClick={handleConsulta}
        >
          Consulta
        </button>
      </div>

      {hasConsulted ? (
        <>
          <section className="saldo-panel" aria-live="polite">
            <h2>Valor de caja</h2>
            <p className="saldo-valor">
              {saldo ? `$ ${saldo.saldo_actual}` : loadingConsulta ? "Cargando…" : "—"}
            </p>
          </section>

          <MovimientoTable movimientos={movimientos} />

          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            disabled={loadingConsulta}
          />
        </>
      ) : null}
    </>
  );
}

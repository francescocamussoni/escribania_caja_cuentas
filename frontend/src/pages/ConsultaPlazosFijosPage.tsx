import { useCallback, useEffect, useState } from "react";

import CajaSelector from "../components/CajaSelector";
import PlazoFijoTable from "../components/PlazoFijoTable";
import PlazosFijosResumenPanel from "../components/PlazosFijosResumenPanel";
import Pagination from "../components/Pagination";
import {
  apiGet,
  type Caja,
  type PaginatedPlazosFijos,
  type PlazoFijo,
  type PlazosFijosResumen,
} from "../services/api";

export default function ConsultaPlazosFijosPage() {
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [selectedCajaId, setSelectedCajaId] = useState<number | null>(null);
  const [resumen, setResumen] = useState<PlazosFijosResumen | null>(null);
  const [plazosFijos, setPlazosFijos] = useState<PlazoFijo[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loadingCajas, setLoadingCajas] = useState(true);
  const [loadingConsulta, setLoadingConsulta] = useState(false);
  const [hasConsulted, setHasConsulted] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      setError("No se pudieron cargar los plazos fijos.");
    } finally {
      setLoadingConsulta(false);
    }
  }

  function handleCajaChange(cajaId: number) {
    setSelectedCajaId(cajaId);
    setResumen(null);
    setPlazosFijos([]);
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
      setError("No se pudieron cargar los plazos fijos.");
    } finally {
      setLoadingConsulta(false);
    }
  }

  const isBusy = loadingCajas || loadingConsulta;

  return (
    <>
      <header className="page-header">
        <h1>Consulta plazos fijos</h1>
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
          <PlazosFijosResumenPanel
            totalMontoIngresado={resumen?.total_monto_ingresado_activos ?? null}
            totalMontoAVencimiento={
              resumen?.total_monto_a_vencimiento_activos ?? null
            }
            loading={loadingConsulta && !resumen}
          />

          <PlazoFijoTable plazosFijos={plazosFijos} />

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

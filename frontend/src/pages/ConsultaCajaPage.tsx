import { useCallback, useEffect, useRef, useState } from "react";

import CajaConsultaSolapa from "../components/CajaConsultaSolapa";
import CajaSelector from "../components/CajaSelector";
import CajasAdicionalesSelector from "../components/CajasAdicionalesSelector";
import ChequesPendientesBlock from "../components/ChequesPendientesBlock";
import MovimientoTable from "../components/MovimientoTable";
import Pagination from "../components/Pagination";
import SaldoFuturoDesplegable from "../components/SaldoFuturoDesplegable";
import ValorCajaTotal from "../components/ValorCajaTotal";
import { useAuth } from "../hooks/useAuth";
import {
  apiGet,
  type Caja,
  type CajaSaldo,
  type CajaSaldoGeneral,
  type Movimiento,
  type MovimientoFiltros,
  type PaginatedMovimientos,
} from "../services/api";

function jointCajaIds(
  principalId: number,
  adicionalesIds: number[],
  cajas: Caja[],
): number[] {
  const additional = cajas
    .filter((caja) => caja.id !== principalId && adicionalesIds.includes(caja.id))
    .map((caja) => caja.id);
  return [principalId, ...additional];
}

function sumSaldoArs(saldos: CajaSaldo[]): string {
  const totalCents = saldos.reduce((acc, item) => {
    const negative = item.saldo_ars.trim().startsWith("-");
    const [whole = "0", fraction = ""] = item.saldo_ars
      .trim()
      .replace("-", "")
      .split(".");
    const cents = Number(whole) * 100 + Number((fraction + "00").slice(0, 2));
    return acc + (negative ? -cents : cents);
  }, 0);
  const sign = totalCents < 0 ? "-" : "";
  const abs = Math.abs(totalCents);
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, "0")}`;
}

export default function ConsultaCajaPage() {
  const { rol } = useAuth();
  const isSecretaria = rol === "secretaria";
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [selectedCajaId, setSelectedCajaId] = useState<number | null>(null);
  const [adicionalesIds, setAdicionalesIds] = useState<number[]>([]);
  const [saldo, setSaldo] = useState<CajaSaldo | null>(null);
  const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [saldosConjunto, setSaldosConjunto] = useState<CajaSaldo[]>([]);
  const [consultaKey, setConsultaKey] = useState(0);
  const [jointMode, setJointMode] = useState(false);
  const [loadingCajas, setLoadingCajas] = useState(true);
  const [loadingConsulta, setLoadingConsulta] = useState(false);
  const [hasConsulted, setHasConsulted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saldoGeneral, setSaldoGeneral] = useState<CajaSaldoGeneral | null>(null);
  const adicionalesDetailsRef = useRef<HTMLDetailsElement>(null);

  // ── Filtros US3 ──────────────────────────────────────────────────────────
  const [filtroMoneda, setFiltroMoneda] = useState<"ARS" | "USD" | "">("");
  const [filtroFechaDesde, setFiltroFechaDesde] = useState("");
  const [filtroFechaHasta, setFiltroFechaHasta] = useState("");

  const buildFiltros = useCallback((): MovimientoFiltros => {
    const f: MovimientoFiltros = {};
    if (filtroMoneda) f.moneda = filtroMoneda;
    if (filtroFechaDesde) f.fecha_desde = filtroFechaDesde;
    if (filtroFechaHasta) f.fecha_hasta = filtroFechaHasta;
    return f;
  }, [filtroMoneda, filtroFechaDesde, filtroFechaHasta]);

  const loadCajaData = useCallback(async (cajaId: number, currentPage: number, filtros?: MovimientoFiltros) => {
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
    setJointMode(false);
    setSaldosConjunto([]);
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

  function clearConsultaResult() {
    setSaldo(null);
    setMovimientos([]);
    setPage(1);
    setTotalPages(0);
    setSaldosConjunto([]);
    setJointMode(false);
    setHasConsulted(false);
    setSaldoGeneral(null);
  }

  async function handleConsulta() {
    if (!selectedCajaId) {
      return;
    }

    setLoadingConsulta(true);
    setError(null);
    clearConsultaResult();
    if (adicionalesDetailsRef.current) {
      adicionalesDetailsRef.current.open = false;
    }

    try {
      if (adicionalesIds.length === 0) {
        await loadCajaData(selectedCajaId, 1);
        return;
      }

      const ids = jointCajaIds(selectedCajaId, adicionalesIds, cajas);
      const saldos = await Promise.all(
        ids.map((cajaId) => apiGet<CajaSaldo>(`/api/v1/cajas/${cajaId}/saldo`)),
      );
      setSaldosConjunto(saldos);
      setJointMode(true);
      setConsultaKey((key) => key + 1);
      setHasConsulted(true);
    } catch {
      setError("No se pudieron cargar los datos de la caja.");
    } finally {
      setLoadingConsulta(false);
    }
  }

  async function handleCajaChange(cajaId: number) {
    setSelectedCajaId(cajaId);
    setAdicionalesIds((ids) => ids.filter((id) => id !== cajaId));
    setFiltroMoneda("");
    setFiltroFechaDesde("");
    setFiltroFechaHasta("");
    clearConsultaResult();
  }

  async function handlePageChange(nextPage: number) {
    if (!selectedCajaId) {
      return;
    }

    setLoadingConsulta(true);
    setError(null);

    try {
      await loadCajaData(selectedCajaId, nextPage, buildFiltros());
    } catch {
      setError("No se pudieron cargar los movimientos.");
    } finally {
      setLoadingConsulta(false);
    }
  }

  async function handleFiltroChange(newFiltros: MovimientoFiltros) {
    if (!selectedCajaId || !hasConsulted) return;
    setLoadingConsulta(true);
    setError(null);
    try {
      await loadCajaData(selectedCajaId, 1, newFiltros);
    } catch {
      setError("No se pudieron cargar los movimientos.");
    } finally {
      setLoadingConsulta(false);
    }
  }

  async function handleSaldoGeneral() {
    setLoadingConsulta(true);
    setError(null);
    clearConsultaResult();
    if (adicionalesDetailsRef.current) {
      adicionalesDetailsRef.current.open = false;
    }
    try {
      const response = await apiGet<CajaSaldoGeneral>("/api/v1/cajas/saldo-general");
      setSaldoGeneral(response);
    } catch {
      setSaldoGeneral(null);
      setError("No se pudo cargar el subtotal general.");
    } finally {
      setLoadingConsulta(false);
    }
  }

  const isBusy = loadingCajas || loadingConsulta;

  return (
    <div className="page-stack">
      <header className="page-header page-block" data-block="titulo">
        <h1>Consulta de caja</h1>
      </header>

      {error ? (
        <p className="form-error page-block" data-block="error">
          {error}
        </p>
      ) : null}

      <div className="consulta-controls consulta-controls--stack page-block" data-block="controles">
        <div className="consulta-controls__row">
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
          {isSecretaria ? (
            <button
              type="button"
              className="button button--secondary"
              disabled={isBusy}
              onClick={() => void handleSaldoGeneral()}
            >
              Subtotal general
            </button>
          ) : null}
        </div>
        <CajasAdicionalesSelector
          cajas={cajas}
          activeCajaId={selectedCajaId}
          selectedCajaIds={adicionalesIds}
          onChange={setAdicionalesIds}
          disabled={isBusy}
          summary="Ver en conjunto con otras cajas"
          detailsRef={adicionalesDetailsRef}
        />
      </div>

      {saldoGeneral ? (
        <section className="consulta-conjunto page-block" data-block="saldo" aria-live="polite">
          <section className="saldo-panel">
            <h2>Subtotal general</h2>
            <div className="saldo-dual">
              <p className="saldo-valor">
                <span className="saldo-moneda-label">ARS</span>
                {` $ ${saldoGeneral.subtotal_general_ars}`}
              </p>
              <p className="saldo-valor">
                <span className="saldo-moneda-label">USD</span>
                {` $ ${saldoGeneral.subtotal_general_usd}`}
              </p>
            </div>
          </section>
          <table className="movimiento-table">
            <thead>
              <tr>
                <th>Caja</th>
                <th>Saldo ARS</th>
                <th>Saldo USD</th>
              </tr>
            </thead>
            <tbody>
              {saldoGeneral.cajas.map((item) => (
                <tr key={item.caja.id}>
                  <td data-label="Caja">{item.caja.nombre}</td>
                  <td data-label="Saldo ARS">$ {item.saldo_ars}</td>
                  <td data-label="Saldo USD">$ {item.saldo_usd}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {hasConsulted && jointMode ? (
        <section className="consulta-conjunto page-block" data-block="solapas" aria-live="polite">
          <section className="saldo-panel">
            <h2>Valor en conjunto</h2>
            <p className="saldo-valor">$ {sumSaldoArs(saldosConjunto)}</p>
          </section>
          {saldosConjunto.map((item) => (
            <CajaConsultaSolapa
              key={`${consultaKey}-${item.caja.id}`}
              caja={item.caja}
              saldoActual={item.saldo_ars}
            />
          ))}
        </section>
      ) : null}

      {hasConsulted && !jointMode ? (
        <>
          <section className="saldo-panel page-block" data-block="saldo" aria-live="polite">
            <div className="saldo-panel__row">
              <div className="saldo-panel__actual">
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
                  <p className="saldo-valor">{loadingConsulta ? "Cargando…" : "—"}</p>
                )}
              </div>
              <ValorCajaTotal cajaId={selectedCajaId} fecha={filtroFechaHasta} />
            </div>
            <SaldoFuturoDesplegable cajaId={selectedCajaId} />
          </section>

          <div className="page-block" data-block="cheques-pendientes">
            {selectedCajaId ? (
              <ChequesPendientesBlock cajaId={selectedCajaId} readOnly />
            ) : null}
          </div>

          <div className="page-block movimiento-filtros" data-block="filtros">
            <label className="field field--inline" htmlFor="filtro-moneda">
              <span>Moneda</span>
              <select
                id="filtro-moneda"
                aria-label="Filtrar por moneda"
                value={filtroMoneda}
                disabled={loadingConsulta}
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
            </label>

            <label className="field field--inline" htmlFor="filtro-fecha-desde">
              <span>Desde</span>
              <input
                id="filtro-fecha-desde"
                type="date"
                value={filtroFechaDesde}
                disabled={loadingConsulta}
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
                disabled={loadingConsulta}
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
            <MovimientoTable movimientos={movimientos} />
          </div>

          <div className="page-block" data-block="paginacion">
            <Pagination
              page={page}
              totalPages={totalPages}
              onPageChange={handlePageChange}
              disabled={loadingConsulta}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}

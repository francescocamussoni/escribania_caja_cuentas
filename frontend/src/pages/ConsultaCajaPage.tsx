import { useCallback, useEffect, useRef, useState } from "react";

import CajaConsultaSolapa from "../components/CajaConsultaSolapa";
import CajaSelector from "../components/CajaSelector";
import CajasAdicionalesSelector from "../components/CajasAdicionalesSelector";
import MovimientoTable from "../components/MovimientoTable";
import Pagination from "../components/Pagination";
import { useAuth } from "../hooks/useAuth";
import {
  apiGet,
  type Caja,
  type CajaSaldo,
  type CajaSaldoGeneral,
  type Movimiento,
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

function sumSaldoActual(saldos: CajaSaldo[]): string {
  const totalCents = saldos.reduce((acc, item) => {
    const negative = item.saldo_actual.trim().startsWith("-");
    const [whole = "0", fraction = ""] = item.saldo_actual
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
    clearConsultaResult();
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
            <p className="saldo-valor">$ {saldoGeneral.subtotal_general}</p>
          </section>
          <table className="movimiento-table">
            <thead>
              <tr>
                <th>Caja</th>
                <th>Subtotal</th>
              </tr>
            </thead>
            <tbody>
              {saldoGeneral.cajas.map((item) => (
                <tr key={item.caja.id}>
                  <td data-label="Caja">{item.caja.nombre}</td>
                  <td data-label="Subtotal">$ {item.saldo_actual}</td>
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
            <p className="saldo-valor">$ {sumSaldoActual(saldosConjunto)}</p>
          </section>
          {saldosConjunto.map((item) => (
            <CajaConsultaSolapa
              key={`${consultaKey}-${item.caja.id}`}
              caja={item.caja}
              saldoActual={item.saldo_actual}
            />
          ))}
        </section>
      ) : null}

      {hasConsulted && !jointMode ? (
        <>
          <section className="saldo-panel page-block" data-block="saldo" aria-live="polite">
            <h2>Valor de caja</h2>
            <p className="saldo-valor">
              {saldo ? `$ ${saldo.saldo_actual}` : loadingConsulta ? "Cargando…" : "—"}
            </p>
          </section>

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

import { useEffect, useState } from "react";

import { useAuth } from "../hooks/useAuth";
import { fetchSaldoProyectado, type SaldoProyectado } from "../services/api";
import { formatFechaIso, mananaAr } from "../utils/fechas";

type ValorCajaTotalProps = {
  cajaId: number | null;
  /** Value of the "Hasta" filter (YYYY-MM-DD, or empty). Drives the calculation. */
  fecha: string;
  /** Bump after any change that affects pending cheques or the balance. */
  refreshKey?: number;
};

/**
 * "Valor de caja total" (Secretaria only): follows the "Hasta" filter. For a future date it
 * shows, per moneda, today's balance plus/minus the pending cheques that settle on or
 * before that date. The server does all the math; this component only shows the result.
 */
export default function ValorCajaTotal({ cajaId, fecha, refreshKey = 0 }: ValorCajaTotalProps) {
  const { rol } = useAuth();
  const [data, setData] = useState<SaldoProyectado | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const esSecretaria = rol === "secretaria";
  const minFecha = mananaAr();
  // No date = every pending cheque (the last possible sum); past dates have no projection.
  const fechaValida = fecha === "" || fecha >= minFecha;

  useEffect(() => {
    setData(null);
    setError(null);
  }, [cajaId]);

  useEffect(() => {
    if (!esSecretaria || cajaId === null || !fechaValida) {
      setData(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchSaldoProyectado(cajaId, fecha || undefined)
      .then((response) => {
        if (!cancelled) {
          setData(response);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          setError("No se pudo calcular el valor de caja total.");
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
  }, [esSecretaria, cajaId, fecha, fechaValida, refreshKey]);

  if (!esSecretaria) {
    return null;
  }

  return (
    <div className="valor-caja-total" data-testid="valor-caja-total">
      <h2>Valor de caja total</h2>
      {error ? (
        <p className="valor-caja-total__error" role="alert">
          {error}
        </p>
      ) : null}

      {!fechaValida ? (
        <p className="valor-caja-total__hint">
          El valor de caja total solo se calcula con una fecha futura en "Hasta".
        </p>
      ) : loading && data === null ? (
        <p className="valor-caja-total__hint">Calculando…</p>
      ) : data ? (
        <>
          <div className="saldo-dual">
            {data.monedas.map((m) => (
              <p
                key={m.moneda}
                className="saldo-valor"
                data-testid={`valor-caja-total-${m.moneda}`}
              >
                <span className="saldo-moneda-label">{m.moneda}</span>
                {` $ ${m.saldo_proyectado}`}
              </p>
            ))}
          </div>
          <p className="valor-caja-total__hint">
            {data.fecha ? `Al ${formatFechaIso(data.fecha)}` : "Con todos los cheques pendientes"}
            : valor de caja ± cheques pendientes de liquidar ({data.monedas.map((m) => `${m.moneda} ${m.cheques}`).join(" · ")}).
          </p>
        </>
      ) : null}
    </div>
  );
}

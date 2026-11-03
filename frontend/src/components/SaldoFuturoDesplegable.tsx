import { useEffect, useState } from "react";

import { fetchSaldoFuturo, type SaldoFuturo } from "../services/api";
import { formatFechaIso } from "../utils/fechas";

type SaldoFuturoDesplegableProps = {
  cajaId: number | null;
  /** Bump after any change that affects pending cheques or the balance. */
  refreshKey?: number;
};

function money(value: string): string {
  return `$ ${value}`;
}

/**
 * "Saldo a futuro": today's balance plus the projected balance for each fecha de
 * liquidación of the pending cheques, per moneda. The server does all the math.
 * Closed by default; data is loaded lazily when expanded and kept fresh while open.
 */
export default function SaldoFuturoDesplegable({
  cajaId,
  refreshKey = 0,
}: SaldoFuturoDesplegableProps) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<SaldoFuturo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || cajaId === null) {
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchSaldoFuturo(cajaId)
      .then((response) => {
        if (!cancelled) {
          setData(response);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          setError("No se pudo cargar el saldo a futuro.");
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
  }, [open, cajaId, refreshKey]);

  const sinCheques =
    data !== null && data.monedas.every((moneda) => moneda.filas.length === 0);

  return (
    <details className="saldo-futuro" open={open}>
      <summary
        onClick={(event) => {
          // Controlled toggle: the open state drives the lazy loading deterministically.
          event.preventDefault();
          setOpen((current) => !current);
        }}
      >
        Saldo a futuro
      </summary>

      {open ? (
        <div className="saldo-futuro__body" aria-live="polite">
          {loading ? <p className="saldo-futuro__status">Cargando…</p> : null}
          {error ? <p className="form-error">{error}</p> : null}

          {data && !error ? (
            <>
              {sinCheques ? (
                <p className="saldo-futuro__status">
                  No hay cheques pendientes: el saldo a futuro coincide con el de hoy.
                </p>
              ) : null}
              {data.monedas.map((moneda) => (
                <section
                  key={moneda.moneda}
                  className="saldo-futuro__moneda"
                  aria-label={`Saldo a futuro ${moneda.moneda}`}
                >
                  <h3>{moneda.moneda}</h3>
                  <table className="movimiento-table saldo-futuro-table">
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Detalle</th>
                        <th>Efecto</th>
                        <th>Saldo proyectado</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="saldo-futuro-table__hoy">
                        <td data-label="Fecha">Hoy</td>
                        <td data-label="Detalle">—</td>
                        <td data-label="Efecto">—</td>
                        <td data-label="Saldo proyectado">{money(moneda.saldo_actual)}</td>
                      </tr>
                      {moneda.filas.map((fila) => (
                        <tr key={fila.fecha_liquidacion}>
                          <td data-label="Fecha">
                            {formatFechaIso(fila.fecha_liquidacion)}
                            {fila.vencido ? (
                              <>
                                {" "}
                                <span className="estado-badge estado-badge--vencido">
                                  Vencido
                                </span>
                              </>
                            ) : null}
                          </td>
                          <td data-label="Detalle">
                            <ul className="saldo-futuro-detalle">
                              {(fila.detalle ?? []).map((item, index) => (
                                <li key={index} className="saldo-futuro-detalle__item">
                                  <span className="saldo-futuro-detalle__descripcion">
                                    {item.descripcion}
                                  </span>{" "}
                                  <span className="instrumento-badge">
                                    {item.instrumento === "echeque" ? "Echeque" : "Cheque"}
                                  </span>{" "}
                                  <span
                                    className={
                                      item.tipo === "salida"
                                        ? "movimiento-salida"
                                        : "movimiento-entrada"
                                    }
                                  >
                                    {item.tipo === "salida" ? "-" : "+"}
                                    {item.monto}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </td>
                          <td
                            data-label="Efecto"
                            className={
                              fila.efecto_neto.startsWith("-")
                                ? "movimiento-salida"
                                : "movimiento-entrada"
                            }
                          >
                            {fila.efecto_neto.startsWith("-") ? "" : "+"}
                            {fila.efecto_neto}
                          </td>
                          <td data-label="Saldo proyectado">{money(fila.saldo_proyectado)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              ))}
            </>
          ) : null}
        </div>
      ) : null}
    </details>
  );
}

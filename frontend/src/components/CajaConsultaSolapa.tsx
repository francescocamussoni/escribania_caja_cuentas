import { useState, type SyntheticEvent } from "react";

import {
  apiGet,
  type Caja,
  type Movimiento,
  type PaginatedMovimientos,
} from "../services/api";
import MovimientoTable from "./MovimientoTable";
import Pagination from "./Pagination";

type CajaConsultaSolapaProps = {
  caja: Caja;
  saldoActual: string;
};

export default function CajaConsultaSolapa({
  caja,
  saldoActual,
}: CajaConsultaSolapaProps) {
  const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadPage(nextPage: number) {
    setLoading(true);
    setError(null);

    try {
      const response = await apiGet<PaginatedMovimientos>(
        `/api/v1/cajas/${caja.id}/movimientos?page=${nextPage}`,
      );
      setMovimientos(response.items);
      setPage(response.page);
      setTotalPages(response.total_pages);
      setLoaded(true);
    } catch {
      setError("No se pudieron cargar los movimientos.");
    } finally {
      setLoading(false);
    }
  }

  function handleToggle(event: SyntheticEvent<HTMLDetailsElement>) {
    if (event.currentTarget.open && !loaded && !loading) {
      void loadPage(1);
    }
  }

  return (
    <details className="caja-consulta-solapa" onToggle={handleToggle}>
      <summary className="caja-consulta-solapa__summary">
        <span>{caja.nombre}</span>
        <span className="saldo-valor">$ {saldoActual}</span>
      </summary>
      <div className="caja-consulta-solapa__body">
        {error ? <p className="form-error">{error}</p> : null}
        {loading && !loaded ? <p>Cargando…</p> : null}
        {loaded ? (
          <>
            <MovimientoTable movimientos={movimientos} />
            <Pagination
              page={page}
              totalPages={totalPages}
              onPageChange={loadPage}
              disabled={loading}
            />
          </>
        ) : null}
      </div>
    </details>
  );
}

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  archiveCaja,
  createCaja,
  listCajasConfig,
  unarchiveCaja,
  type Caja,
} from "../services/api";

export default function ConfiguracionCajasPage() {
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [nombre, setNombre] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadCajas = useCallback(async () => {
    const response = await listCajasConfig();
    setCajas(response);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        await loadCajas();
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

    void load();
    return () => {
      cancelled = true;
    };
  }, [loadCajas]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      await createCaja(nombre);
      setNombre("");
      setSuccess("Caja creada.");
      await loadCajas();
    } catch {
      setError("No se pudo crear la caja.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleArchive(cajaId: number) {
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      await archiveCaja(cajaId);
      setSuccess("Caja archivada.");
      await loadCajas();
    } catch {
      setError("No se pudo archivar la caja.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUnarchive(cajaId: number) {
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      await unarchiveCaja(cajaId);
      setSuccess("Caja desarchivada.");
      await loadCajas();
    } catch {
      setError("No se pudo desarchivar la caja.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page">
      <h1>Configuración</h1>
      <p>
        Alta y archivo de cajas. Las archivadas conservan su historial y se
        pueden desarchivar para volver a operar.
      </p>

      <form className="form-card config-cajas-form" onSubmit={handleCreate}>
        <div className="config-cajas-form__row">
          <label className="field">
            Nombre de la caja
            <input
              value={nombre}
              onChange={(event) => setNombre(event.target.value)}
              maxLength={120}
              required
            />
          </label>
          <button
            type="submit"
            className="button button--primary"
            disabled={submitting}
          >
            Agregar
          </button>
        </div>
      </form>

      {success ? <p className="form-success">{success}</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
      {loading ? <p>Cargando cajas…</p> : null}

      <table className="movimiento-table">
        <thead>
          <tr>
            <th>Caja</th>
            <th>Estado</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {cajas.map((caja) => (
            <tr key={caja.id}>
              <td>{caja.nombre}</td>
              <td>{caja.estado ?? "activa"}</td>
              <td>
                {caja.estado !== "archivada" ? (
                  <button
                    type="button"
                    className="button button--secondary"
                    disabled={submitting}
                    onClick={() => void handleArchive(caja.id)}
                  >
                    Archivar
                  </button>
                ) : (
                  <button
                    type="button"
                    className="button button--secondary"
                    disabled={submitting}
                    onClick={() => void handleUnarchive(caja.id)}
                  >
                    Desarchivar
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

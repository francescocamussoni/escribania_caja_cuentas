import { FormEvent, useState } from "react";

import type { CreateMovimientoPayload } from "../services/api";

type MovimientoFormProps = {
  onSubmit: (payload: CreateMovimientoPayload) => Promise<void>;
  disabled?: boolean;
};

export default function MovimientoForm({
  onSubmit,
  disabled = false,
}: MovimientoFormProps) {
  const [descripcion, setDescripcion] = useState("");
  const [monto, setMonto] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
    tipo: CreateMovimientoPayload["tipo"],
  ) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await onSubmit({ descripcion, monto, tipo });
      setDescripcion("");
      setMonto("");
    } catch {
      setError("No se pudo registrar el movimiento.");
    } finally {
      setSubmitting(false);
    }
  }

  const isDisabled = disabled || submitting;

  return (
    <form className="movimiento-form">
      <label htmlFor="movimiento-descripcion">Descripción</label>
      <input
        id="movimiento-descripcion"
        name="descripcion"
        type="text"
        value={descripcion}
        disabled={isDisabled}
        onChange={(event) => setDescripcion(event.target.value)}
        required
      />

      <label htmlFor="movimiento-monto">Monto</label>
      <input
        id="movimiento-monto"
        name="monto"
        type="text"
        inputMode="decimal"
        value={monto}
        disabled={isDisabled}
        onChange={(event) => setMonto(event.target.value)}
        required
      />

      <div className="movimiento-form-actions">
        <button
          type="submit"
          className="btn-entrada"
          disabled={isDisabled}
          onClick={(event) => handleSubmit(event, "entrada")}
        >
          Entrada
        </button>
        <button
          type="submit"
          className="btn-salida"
          disabled={isDisabled}
          onClick={(event) => handleSubmit(event, "salida")}
        >
          Salida
        </button>
      </div>

      {error ? <p className="form-error">{error}</p> : null}
    </form>
  );
}

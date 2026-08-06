import { type FormEvent, useState } from "react";

import type { CreatePlazoFijoPayload } from "../services/api";

type PlazoFijoFormProps = {
  onSubmit: (payload: CreatePlazoFijoPayload) => Promise<void>;
  disabled?: boolean;
};

export default function PlazoFijoForm({
  onSubmit,
  disabled = false,
}: PlazoFijoFormProps) {
  const [montoIngresado, setMontoIngresado] = useState("");
  const [fechaVencimiento, setFechaVencimiento] = useState("");
  const [montoAVencimiento, setMontoAVencimiento] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await onSubmit({
        monto_ingresado: montoIngresado,
        monto_a_vencimiento: montoAVencimiento,
        fecha_vencimiento: fechaVencimiento,
      });
      setMontoIngresado("");
      setFechaVencimiento("");
      setMontoAVencimiento("");
    } catch {
      setError("No se pudo registrar el plazo fijo.");
    } finally {
      setSubmitting(false);
    }
  }

  const isDisabled = disabled || submitting;

  return (
    <section className="plazo-fijo-form-section">
      <form className="plazo-fijo-form" onSubmit={handleSubmit}>
        <label className="field plazo-fijo-form__monto-ingresado">
          <span>Monto ingresado</span>
          <input
            name="monto-ingresado"
            type="text"
            inputMode="decimal"
            value={montoIngresado}
            disabled={isDisabled}
            onChange={(event) => setMontoIngresado(event.target.value)}
            required
          />
        </label>

        <label className="field plazo-fijo-form__fecha-vencimiento">
          <span>Fecha de vencimiento</span>
          <input
            name="fecha-vencimiento"
            type="date"
            value={fechaVencimiento}
            disabled={isDisabled}
            onChange={(event) => setFechaVencimiento(event.target.value)}
            required
          />
        </label>

        <label className="field plazo-fijo-form__monto-a-vencimiento">
          <span>Monto a vencimiento</span>
          <input
            name="monto-a-vencimiento"
            type="text"
            inputMode="decimal"
            value={montoAVencimiento}
            disabled={isDisabled}
            onChange={(event) => setMontoAVencimiento(event.target.value)}
            required
          />
        </label>

        <button
          type="submit"
          className="button button--primary plazo-fijo-form__action"
          disabled={isDisabled}
        >
          Registrar
        </button>

        {error ? <p className="form-error plazo-fijo-form__error">{error}</p> : null}
      </form>
    </section>
  );
}

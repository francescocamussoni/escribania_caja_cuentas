import { useCallback, useEffect, useState } from "react";

import type { Caja, CreateMovimientoPayload } from "../services/api";
import CajasAdicionalesSelector from "./CajasAdicionalesSelector";

type MovimientoFormProps = {
  cajas?: Caja[];
  activeCajaId?: number | null;
  onSubmit: (
    payload: CreateMovimientoPayload,
    additionalCajaIds: number[],
  ) => Promise<void>;
  disabled?: boolean;
};

export default function MovimientoForm({
  cajas = [],
  activeCajaId = null,
  onSubmit,
  disabled = false,
}: MovimientoFormProps) {
  const [descripcion, setDescripcion] = useState("");
  const [monto, setMonto] = useState("");
  const [additionalCajaIds, setAdditionalCajaIds] = useState<number[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdditionalCajasChange = useCallback((selectedCajaIds: number[]) => {
    setAdditionalCajaIds(selectedCajaIds);
  }, []);

  useEffect(() => {
    setAdditionalCajaIds([]);
  }, [activeCajaId]);

  async function submitMovimiento(tipo: CreateMovimientoPayload["tipo"]) {
    setError(null);
    setSubmitting(true);

    try {
      await onSubmit({ descripcion, monto, tipo }, additionalCajaIds);
      setDescripcion("");
      setMonto("");
      setAdditionalCajaIds([]);
    } catch {
      setError("No se pudo registrar el movimiento.");
    } finally {
      setSubmitting(false);
    }
  }

  const isDisabled = disabled || submitting;

  return (
    <section className="movimiento-form-section">
      <form className="movimiento-form">
        <label className="field movimiento-form__descripcion">
          <span>Descripción</span>
          <input
            name="descripcion"
            type="text"
            value={descripcion}
            disabled={isDisabled}
            onChange={(event) => setDescripcion(event.target.value)}
            required
          />
        </label>

        <label className="field movimiento-form__monto">
          <span>Monto</span>
          <input
            name="monto"
            type="text"
            inputMode="decimal"
            value={monto}
            disabled={isDisabled}
            onChange={(event) => setMonto(event.target.value)}
            required
          />
        </label>

        <button
          type="button"
          className="button btn-entrada movimiento-form__action"
          disabled={isDisabled}
          onClick={() => void submitMovimiento("entrada")}
        >
          Entrada
        </button>

        <button
          type="button"
          className="button btn-salida movimiento-form__action"
          disabled={isDisabled}
          onClick={() => void submitMovimiento("salida")}
        >
          Salida
        </button>

        {error ? <p className="form-error movimiento-form__error">{error}</p> : null}
      </form>

      <CajasAdicionalesSelector
        cajas={cajas}
        activeCajaId={activeCajaId}
        selectedCajaIds={additionalCajaIds}
        onChange={handleAdditionalCajasChange}
        disabled={isDisabled}
      />
    </section>
  );
}

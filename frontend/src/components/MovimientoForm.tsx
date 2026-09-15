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
  const [moneda, setMoneda] = useState<"ARS" | "USD">("ARS");
  // T040 (US3): Estado de fecha manual — NO se resetea al cambiar de caja (T038)
  const [fechaManual, setFechaManual] = useState("");
  const [additionalCajaIds, setAdditionalCajaIds] = useState<number[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdditionalCajasChange = useCallback((selectedCajaIds: number[]) => {
    setAdditionalCajaIds(selectedCajaIds);
  }, []);

  useEffect(() => {
    setAdditionalCajaIds([]);
    setMoneda("ARS");
  }, [activeCajaId]);

  async function doSubmit(
    tipo: CreateMovimientoPayload["tipo"],
    registrar_complementario: boolean,
  ) {
    setError(null);
    setSubmitting(true);

    try {
      await onSubmit(
        {
          descripcion,
          monto,
          tipo,
          moneda,
          registrar_complementario,
          // T042 (US3): incluir fecha_manual solo cuando tiene valor
          ...(fechaManual ? { fecha_manual: fechaManual } : {}),
        },
        additionalCajaIds,
      );
      setDescripcion("");
      setMonto("");
      setAdditionalCajaIds([]);
      setFechaManual("");
    } catch {
      setError("No se pudo registrar el movimiento.");
    } finally {
      setSubmitting(false);
    }
  }

  // T018: handleButtonClick va directo a doSubmit sin bifurcación por moneda (US2)
  function handleButtonClick(tipo: CreateMovimientoPayload["tipo"]) {
    // Validate before submitting (FR-011)
    if (!descripcion.trim() || !monto.trim()) {
      return; // HTML required will handle native validation
    }
    void doSubmit(tipo, false);
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

        <label className="field movimiento-form__moneda" htmlFor="moneda-select">
          <span>Moneda</span>
          <select
            id="moneda-select"
            name="moneda"
            value={moneda}
            disabled={isDisabled}
            onChange={(event) => setMoneda(event.target.value as "ARS" | "USD")}
          >
            <option value="ARS">ARS</option>
            <option value="USD">USD</option>
          </select>
        </label>

        {/* T041 (US3): Selector de fecha manual — NO se resetea con activeCajaId */}
        <label className="field movimiento-form__fecha" htmlFor="fecha-manual-input">
          <span>Fecha (opcional)</span>
          <input
            id="fecha-manual-input"
            name="fecha_manual"
            type="date"
            value={fechaManual}
            disabled={isDisabled}
            onChange={(event) => setFechaManual(event.target.value)}
          />
        </label>

        <button
          type="button"
          className="button btn-entrada movimiento-form__action"
          disabled={isDisabled}
          onClick={() => handleButtonClick("entrada")}
        >
          Entrada
        </button>

        <button
          type="button"
          className="button btn-salida movimiento-form__action"
          disabled={isDisabled}
          onClick={() => handleButtonClick("salida")}
        >
          Salida
        </button>

        {/* T019: Botón "Entrada y Salida" — registra el par atómico (US1) */}
        <button
          type="button"
          className="button btn-entrada-salida movimiento-form__action"
          disabled={isDisabled}
          onClick={() => {
            if (!descripcion.trim() || !monto.trim()) return;
            void doSubmit("entrada", true);
          }}
        >
          Entrada y Salida
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

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
  const [additionalCajaIds, setAdditionalCajaIds] = useState<number[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Dialog state: null = closed; "entrada" | "salida" = waiting for USD confirmation
  const [pendingTipo, setPendingTipo] = useState<"entrada" | "salida" | null>(null);

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
        { descripcion, monto, tipo, moneda, registrar_complementario },
        additionalCajaIds,
      );
      setDescripcion("");
      setMonto("");
      setAdditionalCajaIds([]);
    } catch {
      setError("No se pudo registrar el movimiento.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleButtonClick(tipo: CreateMovimientoPayload["tipo"]) {
    // Validate before showing dialog (FR-011)
    if (!descripcion.trim() || !monto.trim()) {
      return; // HTML required will handle native validation
    }

    if (moneda === "USD") {
      // Show complementario dialog (FR-006, FR-007)
      setPendingTipo(tipo);
    } else {
      // ARS goes straight through without dialog (FR-005, FR-010)
      void doSubmit(tipo, false);
    }
  }

  async function handleDialogConfirm() {
    const tipo = pendingTipo!;
    setPendingTipo(null);
    await doSubmit(tipo, true);
  }

  async function handleDialogCancel() {
    const tipo = pendingTipo!;
    setPendingTipo(null);
    await doSubmit(tipo, false);
  }

  const isDisabled = disabled || submitting;
  const dialogText =
    pendingTipo === "entrada"
      ? "¿Registrar también como salida?"
      : "¿Registrar también como entrada?";

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

        {error ? <p className="form-error movimiento-form__error">{error}</p> : null}
      </form>

      {pendingTipo !== null ? (
        <div
          className="complementario-dialog-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="Confirmar movimiento complementario"
        >
          <div className="complementario-dialog">
            <p className="complementario-dialog__text">{dialogText}</p>
            <div className="complementario-dialog__actions">
              <button
                type="button"
                className="button button--primary"
                onClick={() => void handleDialogConfirm()}
              >
                Sí
              </button>
              <button
                type="button"
                className="button button--secondary"
                onClick={() => void handleDialogCancel()}
              >
                No
              </button>
            </div>
          </div>
        </div>
      ) : null}

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

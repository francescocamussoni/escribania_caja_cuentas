import { useCallback, useEffect, useState } from "react";

import type { Caja, CreateMovimientoPayload, Instrumento } from "../services/api";
import { hoyAr, mananaAr } from "../utils/fechas";
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
  // 010: "-" (ninguno) keeps the previous behaviour; Cheque/Echeque are settled later.
  const [instrumento, setInstrumento] = useState<Instrumento>("ninguno");
  const [fechaLiquidacion, setFechaLiquidacion] = useState("");
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

  const esCheque = instrumento !== "ninguno";

  function handleInstrumentoChange(next: Instrumento) {
    setInstrumento(next);
    if (next === "ninguno") {
      // The liquidation date only makes sense with an instrument: discard it.
      setFechaLiquidacion("");
    }
    setError(null);
  }

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
          // 010: instrumento y fecha de liquidación solo cuando corresponden
          ...(esCheque ? { instrumento, fecha_liquidacion: fechaLiquidacion } : {}),
        },
        additionalCajaIds,
      );
      setDescripcion("");
      setMonto("");
      setAdditionalCajaIds([]);
      setFechaManual("");
      setInstrumento("ninguno");
      setFechaLiquidacion("");
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
    if (esCheque) {
      // The server is authoritative; this only avoids a pointless round trip.
      if (!fechaLiquidacion) {
        setError("La fecha de liquidación es obligatoria.");
        return;
      }
      if (fechaLiquidacion <= hoyAr()) {
        setError("La fecha de liquidación debe ser posterior a hoy.");
        return;
      }
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

        {/* 010: Instrumento — a la derecha de la fecha y antes de Entrada */}
        <label className="field movimiento-form__instrumento" htmlFor="instrumento-select">
          <span>Instrumento</span>
          <select
            id="instrumento-select"
            name="instrumento"
            value={instrumento}
            disabled={isDisabled}
            onChange={(event) => handleInstrumentoChange(event.target.value as Instrumento)}
          >
            <option value="ninguno">-</option>
            <option value="cheque">Cheque</option>
            <option value="echeque">Echeque</option>
          </select>
        </label>

        {esCheque ? (
          <label
            className="field movimiento-form__fecha-liquidacion"
            htmlFor="fecha-liquidacion-input"
          >
            <span>Fecha de liquidación</span>
            <input
              id="fecha-liquidacion-input"
              name="fecha_liquidacion"
              type="date"
              value={fechaLiquidacion}
              min={mananaAr()}
              disabled={isDisabled}
              onChange={(event) => setFechaLiquidacion(event.target.value)}
              required
            />
          </label>
        ) : null}

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

        {/* T019: Botón "Entrada y Salida" — registra el par atómico (US1).
            Un cheque/echeque no admite "Entrada y Salida" (010, FR-005). */}
        {esCheque ? null : (
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
        )}

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

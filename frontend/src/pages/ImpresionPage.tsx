import { useEffect, useState } from "react";

import CajaSelector from "../components/CajaSelector";
import {
  apiGet,
  postInformePdf,
  type Caja,
  type InformeModo,
  type InformePdfRequest,
  type InformeTipo,
} from "../services/api";

const MONTHS = [
  { value: 1, label: "Enero" },
  { value: 2, label: "Febrero" },
  { value: 3, label: "Marzo" },
  { value: 4, label: "Abril" },
  { value: 5, label: "Mayo" },
  { value: 6, label: "Junio" },
  { value: 7, label: "Julio" },
  { value: 8, label: "Agosto" },
  { value: 9, label: "Septiembre" },
  { value: 10, label: "Octubre" },
  { value: 11, label: "Noviembre" },
  { value: 12, label: "Diciembre" },
];

function currentYear(): number {
  return new Date().getFullYear();
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function ImpresionPage() {
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [selectedCajaId, setSelectedCajaId] = useState<number | null>(null);
  const [tipo, setTipo] = useState<InformeTipo>("CAJA");
  const [modo, setModo] = useState<InformeModo>("MES_ANIO");
  const [hastaHoy, setHastaHoy] = useState(false);
  const [mes, setMes] = useState(new Date().getMonth() + 1);
  const [anio, setAnio] = useState(currentYear());
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [loadingCajas, setLoadingCajas] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadCajas() {
      setLoadingCajas(true);
      setError(null);

      try {
        const cajasResponse = await apiGet<Caja[]>("/api/v1/cajas");
        if (cancelled) {
          return;
        }
        setCajas(cajasResponse);
        setSelectedCajaId(cajasResponse[0]?.id ?? null);
      } catch {
        if (!cancelled) {
          setError("No se pudieron cargar las cajas.");
        }
      } finally {
        if (!cancelled) {
          setLoadingCajas(false);
        }
      }
    }

    void loadCajas();

    return () => {
      cancelled = true;
    };
  }, []);

  function validateForm(): string | null {
    if (!selectedCajaId) {
      return "Seleccione una caja.";
    }
    if (modo === "MES_ANIO") {
      if (!mes || !anio) {
        return "Ingrese mes y año.";
      }
      return null;
    }
    if (!fechaInicio) {
      return "Ingrese la fecha de inicio.";
    }
    if (!hastaHoy && !fechaFin) {
      return "Ingrese la fecha de fin o marque Hasta hoy.";
    }
    if (!hastaHoy && fechaInicio > fechaFin) {
      return "La fecha de inicio no puede ser posterior a la fecha de fin.";
    }
    return null;
  }

  function buildPayload(): InformePdfRequest {
    const payload: InformePdfRequest = {
      tipo,
      caja_id: selectedCajaId as number,
      modo,
      hasta_hoy: hastaHoy,
    };

    if (modo === "MES_ANIO") {
      payload.mes = mes;
      payload.anio = anio;
    } else {
      payload.fecha_inicio = fechaInicio;
      if (!hastaHoy) {
        payload.fecha_fin = fechaFin;
      }
    }

    return payload;
  }

  async function handleGenerarInforme() {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setGenerating(true);
    setError(null);

    try {
      const { blob, filename } = await postInformePdf(buildPayload());
      downloadBlob(blob, filename);
    } catch {
      setError("No se pudo generar el informe. Verifique los datos ingresados.");
    } finally {
      setGenerating(false);
    }
  }

  const isBusy = loadingCajas || generating;

  return (
    <>
      <header className="page-header">
        <h1>Impresión</h1>
      </header>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="consulta-controls impresion-form">
        <fieldset className="impresion-fieldset" disabled={isBusy}>
          <legend>Tipo de informe</legend>
          <label className="impresion-radio">
            <input
              type="radio"
              name="tipo-informe"
              value="CAJA"
              checked={tipo === "CAJA"}
              onChange={() => setTipo("CAJA")}
            />
            Caja
          </label>
          <label className="impresion-radio">
            <input
              type="radio"
              name="tipo-informe"
              value="PLAZO_FIJO"
              checked={tipo === "PLAZO_FIJO"}
              onChange={() => setTipo("PLAZO_FIJO")}
            />
            Plazo fijo
          </label>
        </fieldset>

        <CajaSelector
          cajas={cajas}
          selectedCajaId={selectedCajaId}
          onChange={setSelectedCajaId}
          disabled={isBusy}
        />

        <fieldset className="impresion-fieldset" disabled={isBusy}>
          <legend>Temporalidad</legend>
          <label className="impresion-radio">
            <input
              type="radio"
              name="modo-temporal"
              value="MES_ANIO"
              checked={modo === "MES_ANIO"}
              onChange={() => setModo("MES_ANIO")}
            />
            Mes y año
          </label>
          <label className="impresion-radio">
            <input
              type="radio"
              name="modo-temporal"
              value="PERIODO"
              checked={modo === "PERIODO"}
              onChange={() => setModo("PERIODO")}
            />
            Período específico
          </label>
        </fieldset>

        {modo === "MES_ANIO" ? (
          <div className="impresion-date-row">
            <label htmlFor="impresion-mes">
              Mes
              <select
                id="impresion-mes"
                value={mes}
                onChange={(event) => setMes(Number(event.target.value))}
                disabled={isBusy}
              >
                {MONTHS.map((month) => (
                  <option key={month.value} value={month.value}>
                    {month.label}
                  </option>
                ))}
              </select>
            </label>
            <label htmlFor="impresion-anio">
              Año
              <input
                id="impresion-anio"
                type="number"
                min={2000}
                max={2100}
                value={anio}
                onChange={(event) => setAnio(Number(event.target.value))}
                disabled={isBusy}
              />
            </label>
          </div>
        ) : (
          <div className="impresion-date-row">
            <label htmlFor="impresion-fecha-inicio">
              Fecha inicio
              <input
                id="impresion-fecha-inicio"
                type="date"
                value={fechaInicio}
                onChange={(event) => setFechaInicio(event.target.value)}
                disabled={isBusy}
              />
            </label>
            {!hastaHoy ? (
              <label htmlFor="impresion-fecha-fin">
                Fecha fin
                <input
                  id="impresion-fecha-fin"
                  type="date"
                  value={fechaFin}
                  onChange={(event) => setFechaFin(event.target.value)}
                  disabled={isBusy}
                />
              </label>
            ) : null}
          </div>
        )}

        <label className="impresion-checkbox">
          <input
            type="checkbox"
            checked={hastaHoy}
            onChange={(event) => setHastaHoy(event.target.checked)}
            disabled={isBusy}
          />
          Hasta hoy
        </label>

        <button
          type="button"
          className="button button--primary"
          disabled={isBusy || !selectedCajaId}
          onClick={handleGenerarInforme}
        >
          {generating
            ? "Generando…"
            : tipo === "PLAZO_FIJO"
              ? "Generar informe de plazos fijos"
              : "Generar informe de caja"}
        </button>
      </div>
    </>
  );
}

import { KeyboardEvent, useEffect, useId, useRef, useState } from "react";

import { fetchCajas, type Caja } from "../services/api";

type EndoseDialogProps = {
  cajaOrigenId: number;
  /** Must reject on failure; the dialog shows a generic message and stays open. */
  onConfirm: (cajaDestinoId: number) => Promise<void> | void;
  onCancel: () => void;
};

export default function EndoseDialog({
  cajaOrigenId,
  onConfirm,
  onCancel,
}: EndoseDialogProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const submittingRef = useRef(false);

  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchCajas()
      .then((response) => {
        if (!cancelled) {
          setCajas(response.filter((caja) => caja.id !== cajaOrigenId));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError("No se pudieron cargar las cajas.");
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
  }, [cajaOrigenId]);

  async function handleConfirm() {
    if (selectedId === null || submittingRef.current) {
      return;
    }
    submittingRef.current = true;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await onConfirm(selectedId);
    } catch {
      setSubmitError("No se pudo endosar el cheque.");
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape" && !submittingRef.current) {
      event.stopPropagation();
      onCancel();
    }
  }

  return (
    <div className="complementario-dialog-backdrop" onKeyDown={handleKeyDown}>
      <div
        ref={dialogRef}
        className="complementario-dialog endose-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        <p id={titleId} className="complementario-dialog__text">
          Endosar cheque: elegí la caja destino
        </p>

        {loading ? <p>Cargando cajas…</p> : null}
        {loadError ? (
          <p className="form-error" role="alert">
            {loadError}
          </p>
        ) : null}
        {!loading && !loadError && cajas.length === 0 ? (
          <p>No hay otras cajas disponibles.</p>
        ) : null}

        {cajas.length > 0 ? (
          <div className="endose-dialog__list" role="radiogroup" aria-labelledby={titleId}>
            {cajas.map((caja) => (
              <label key={caja.id} className="endose-dialog__option">
                <input
                  type="radio"
                  name="caja-destino"
                  value={caja.id}
                  checked={selectedId === caja.id}
                  onChange={() => setSelectedId(caja.id)}
                  disabled={submitting}
                />
                <span>{caja.nombre}</span>
              </label>
            ))}
          </div>
        ) : null}

        {submitError ? (
          <p className="form-error" role="alert">
            {submitError}
          </p>
        ) : null}

        <div className="complementario-dialog__actions">
          <button type="button" className="button button--secondary" onClick={onCancel} disabled={submitting}>
            Cancelar
          </button>
          <button
            type="button"
            className="button button--primary"
            onClick={() => void handleConfirm()}
            disabled={selectedId === null || submitting}
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}

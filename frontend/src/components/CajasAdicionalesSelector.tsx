import type { Caja } from "../services/api";

type CajasAdicionalesSelectorProps = {
  cajas: Caja[];
  activeCajaId: number | null;
  selectedCajaIds: number[];
  onChange: (selectedCajaIds: number[]) => void;
  disabled?: boolean;
};

export default function CajasAdicionalesSelector({
  cajas,
  activeCajaId,
  selectedCajaIds,
  onChange,
  disabled = false,
}: CajasAdicionalesSelectorProps) {
  const otherCajas = cajas.filter((caja) => caja.id !== activeCajaId);

  if (otherCajas.length === 0) {
    return null;
  }

  function toggleCaja(cajaId: number) {
    if (selectedCajaIds.includes(cajaId)) {
      onChange(selectedCajaIds.filter((id) => id !== cajaId));
      return;
    }
    onChange([...selectedCajaIds, cajaId]);
  }

  return (
    <details className="cajas-adicionales">
      <summary className="cajas-adicionales__summary">
        Registrar también en otras cajas
        {selectedCajaIds.length > 0 ? (
          <span className="cajas-adicionales__count">
            {selectedCajaIds.length} seleccionada
            {selectedCajaIds.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </summary>
      <div className="cajas-adicionales__grid" role="group" aria-label="Cajas adicionales">
        {otherCajas.map((caja) => {
          const isSelected = selectedCajaIds.includes(caja.id);

          return (
            <label
              key={caja.id}
              className={
                isSelected
                  ? "cajas-adicionales__box cajas-adicionales__box--selected"
                  : "cajas-adicionales__box"
              }
            >
              <input
                type="checkbox"
                className="cajas-adicionales__checkbox"
                checked={isSelected}
                disabled={disabled}
                onChange={() => toggleCaja(caja.id)}
              />
              <span>{caja.nombre}</span>
            </label>
          );
        })}
      </div>
    </details>
  );
}

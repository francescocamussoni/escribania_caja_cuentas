import type { Caja } from "../services/api";

type CajaSelectorProps = {
  cajas: Caja[];
  selectedCajaId: number | null;
  onChange: (cajaId: number) => void;
  disabled?: boolean;
};

export default function CajaSelector({
  cajas,
  selectedCajaId,
  onChange,
  disabled = false,
}: CajaSelectorProps) {
  return (
    <label className="field caja-selector">
      <span>Caja</span>
      <select
        value={selectedCajaId ?? ""}
        disabled={disabled || cajas.length === 0}
        onChange={(event) => onChange(Number(event.target.value))}
      >
        {cajas.length === 0 ? (
          <option value="">Sin cajas disponibles</option>
        ) : null}
        {cajas.map((caja) => (
          <option key={caja.id} value={caja.id}>
            {caja.nombre}
          </option>
        ))}
      </select>
    </label>
  );
}

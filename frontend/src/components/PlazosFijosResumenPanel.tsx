type PlazosFijosResumenPanelProps = {
  totalMontoIngresado: string | null;
  totalMontoAVencimiento: string | null;
  loading?: boolean;
};

export default function PlazosFijosResumenPanel({
  totalMontoIngresado,
  totalMontoAVencimiento,
  loading = false,
}: PlazosFijosResumenPanelProps) {
  return (
    <section className="plazos-fijos-resumen" aria-live="polite">
      <div className="plazos-fijos-resumen__item">
        <h2>Dinero ingresado en plazos activos</h2>
        <p className="plazos-fijos-resumen__valor">
          {loading
            ? "Cargando…"
            : totalMontoIngresado
              ? `$ ${totalMontoIngresado}`
              : "—"}
        </p>
      </div>
      <div className="plazos-fijos-resumen__item">
        <h2>Dinero a cobrar al vencer</h2>
        <p className="plazos-fijos-resumen__valor">
          {loading
            ? "Cargando…"
            : totalMontoAVencimiento
              ? `$ ${totalMontoAVencimiento}`
              : "—"}
        </p>
      </div>
    </section>
  );
}

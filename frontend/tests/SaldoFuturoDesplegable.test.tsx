/**
 * T055 — TDD: desplegable "Saldo a futuro" (feature 010, US4).
 *
 * Dentro de "Valor de caja": cerrado por defecto, carga al expandirse y muestra el saldo
 * de hoy más el saldo proyectado acumulado por fecha de liquidación, por moneda. El
 * cálculo lo hace el servidor (el frontend solo muestra).
 */

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SaldoFuturoDesplegable from "../src/components/SaldoFuturoDesplegable";
import type { SaldoFuturo } from "../src/services/api";

const fetchSaldoFuturo = vi.fn();

vi.mock("../src/services/api", () => ({
  fetchSaldoFuturo: (...args: unknown[]) => fetchSaldoFuturo(...args),
}));

const caja = { id: 1, nombre: "Bambina", slug: "bambina" };

function data(overrides: Partial<SaldoFuturo> = {}): SaldoFuturo {
  return {
    caja,
    fecha_calculo: "2026-10-21",
    monedas: [
      {
        moneda: "ARS",
        saldo_actual: "1000.00",
        filas: [
          {
            fecha_liquidacion: "2026-10-15",
            vencido: true,
            cheques: 1,
            efecto_neto: "100.00",
            saldo_proyectado: "1100.00",
            detalle: [
              { descripcion: "Cheque Galicia 0078", instrumento: "cheque", tipo: "entrada", monto: "100.00" },
            ],
          },
          {
            fecha_liquidacion: "2026-11-05",
            vencido: false,
            cheques: 2,
            efecto_neto: "400.00",
            saldo_proyectado: "1500.00",
            detalle: [
              { descripcion: "Honorarios Pérez", instrumento: "cheque", tipo: "entrada", monto: "500.00" },
              { descripcion: "Pago sellado", instrumento: "echeque", tipo: "salida", monto: "100.00" },
            ],
          },
          {
            fecha_liquidacion: "2026-11-20",
            vencido: false,
            cheques: 1,
            efecto_neto: "-200.00",
            saldo_proyectado: "1300.00",
            detalle: [
              { descripcion: "Pago seguro", instrumento: "echeque", tipo: "salida", monto: "200.00" },
            ],
          },
        ],
      },
      { moneda: "USD", saldo_actual: "50.00", filas: [] },
    ],
    ...overrides,
  };
}

function expand() {
  fireEvent.click(screen.getByText("Saldo a futuro"));
}

describe("SaldoFuturoDesplegable (T055)", () => {
  beforeEach(() => {
    fetchSaldoFuturo.mockReset();
    fetchSaldoFuturo.mockResolvedValue(data());
  });

  it("está colapsado por defecto y no consulta hasta expandirse", () => {
    render(<SaldoFuturoDesplegable cajaId={1} />);

    const details = screen.getByText("Saldo a futuro").closest("details");
    expect(details).not.toBeNull();
    expect(details).not.toHaveAttribute("open");
    expect(fetchSaldoFuturo).not.toHaveBeenCalled();
  });

  it("carga al expandirse", async () => {
    render(<SaldoFuturoDesplegable cajaId={1} />);

    expand();

    await waitFor(() => expect(fetchSaldoFuturo).toHaveBeenCalledWith(1));
    expect(screen.getByText("Saldo a futuro").closest("details")).toHaveAttribute("open");
  });

  it("muestra la fila Hoy y las filas proyectadas acumuladas de ARS", async () => {
    render(<SaldoFuturoDesplegable cajaId={1} />);
    expand();

    const ars = await screen.findByRole("region", { name: /saldo a futuro ars/i });
    const rows = within(ars).getAllByRole("row").slice(1); // sin encabezado

    expect(rows).toHaveLength(4);
    expect(within(rows[0]).getByText("Hoy")).toBeInTheDocument();
    expect(within(rows[0]).getByText(/1000\.00/)).toBeInTheDocument();
    expect(within(rows[1]).getByText("15/10/2026")).toBeInTheDocument();
    expect(within(rows[1]).getByText(/1100\.00/)).toBeInTheDocument();
    expect(within(rows[2]).getByText("05/11/2026")).toBeInTheDocument();
    expect(within(rows[2]).getByText(/1500\.00/)).toBeInTheDocument();
    expect(within(rows[3]).getByText("20/11/2026")).toBeInTheDocument();
    expect(within(rows[3]).getByText(/1300\.00/)).toBeInTheDocument();
    expect(within(rows[3]).getAllByText(/-200\.00/).length).toBeGreaterThan(0);
  });

  it("muestra la descripción, el instrumento y el monto de cada cheque de la fecha", async () => {
    render(<SaldoFuturoDesplegable cajaId={1} />);
    expand();

    const ars = await screen.findByRole("region", { name: /saldo a futuro ars/i });
    const rows = within(ars).getAllByRole("row").slice(1);

    const items = within(rows[2]).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(items[0]).getByText("Honorarios Pérez")).toBeInTheDocument();
    expect(within(items[0]).getByText("Cheque")).toBeInTheDocument();
    expect(within(items[0]).getByText("+500.00")).toBeInTheDocument();
    expect(within(items[1]).getByText("Pago sellado")).toBeInTheDocument();
    expect(within(items[1]).getByText("Echeque")).toBeInTheDocument();
    expect(within(items[1]).getByText("-100.00")).toBeInTheDocument();
    expect(within(rows[0]).queryByRole("listitem")).not.toBeInTheDocument();
  });

  it("no se rompe si el servidor todavía no envía el detalle de los cheques", async () => {
    const legacy = data();
    for (const moneda of legacy.monedas) {
      for (const fila of moneda.filas) {
        delete (fila as { detalle?: unknown }).detalle;
      }
    }
    fetchSaldoFuturo.mockResolvedValue(legacy);
    render(<SaldoFuturoDesplegable cajaId={1} />);
    expand();

    const ars = await screen.findByRole("region", { name: /saldo a futuro ars/i });
    expect(within(ars).getAllByRole("row")).toHaveLength(5);
    expect(within(ars).queryByRole("listitem")).not.toBeInTheDocument();
  });

  it("marca Vencido solo en las fechas vencidas", async () => {
    render(<SaldoFuturoDesplegable cajaId={1} />);
    expand();

    const ars = await screen.findByRole("region", { name: /saldo a futuro ars/i });
    const rows = within(ars).getAllByRole("row").slice(1);

    expect(within(rows[1]).getByText(/vencido/i)).toBeInTheDocument();
    expect(within(rows[2]).queryByText(/vencido/i)).not.toBeInTheDocument();
    expect(within(rows[3]).queryByText(/vencido/i)).not.toBeInTheDocument();
  });

  it("muestra ARS y USD por separado, cada uno con su fila Hoy", async () => {
    render(<SaldoFuturoDesplegable cajaId={1} />);
    expand();

    const usd = await screen.findByRole("region", { name: /saldo a futuro usd/i });
    const rows = within(usd).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(1);
    expect(within(rows[0]).getByText("Hoy")).toBeInTheDocument();
    expect(within(rows[0]).getByText(/50\.00/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /saldo a futuro ars/i })).toBeInTheDocument();
  });

  it("sin cheques pendientes muestra solo el saldo de hoy y un aviso", async () => {
    fetchSaldoFuturo.mockResolvedValue(
      data({
        monedas: [
          { moneda: "ARS", saldo_actual: "10.00", filas: [] },
          { moneda: "USD", saldo_actual: "0.00", filas: [] },
        ],
      }),
    );
    render(<SaldoFuturoDesplegable cajaId={1} />);
    expand();

    expect(await screen.findByText(/no hay cheques pendientes/i)).toBeInTheDocument();
    expect(screen.getAllByText("Hoy")).toHaveLength(2);
    expect(screen.queryByText(/vencido/i)).not.toBeInTheDocument();
  });

  it("muestra cargando y luego el contenido", async () => {
    let resolve!: (value: SaldoFuturo) => void;
    fetchSaldoFuturo.mockReturnValue(new Promise<SaldoFuturo>((r) => { resolve = r; }));
    render(<SaldoFuturoDesplegable cajaId={1} />);
    expand();

    expect(await screen.findByText(/cargando/i)).toBeInTheDocument();
    resolve(data());

    expect(await screen.findByRole("region", { name: /saldo a futuro ars/i })).toBeInTheDocument();
    expect(screen.queryByText(/cargando/i)).not.toBeInTheDocument();
  });

  it("muestra un error genérico si falla", async () => {
    fetchSaldoFuturo.mockRejectedValue(new Error('{"detail":"interno"}'));
    render(<SaldoFuturoDesplegable cajaId={1} />);
    expand();

    expect(
      await screen.findByText(/no se pudo cargar el saldo a futuro/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/interno/)).not.toBeInTheDocument();
  });

  it("recarga al cambiar refreshKey o cajaId mientras está abierto", async () => {
    const { rerender } = render(<SaldoFuturoDesplegable cajaId={1} refreshKey={0} />);
    expand();
    await waitFor(() => expect(fetchSaldoFuturo).toHaveBeenCalledTimes(1));

    rerender(<SaldoFuturoDesplegable cajaId={1} refreshKey={1} />);
    await waitFor(() => expect(fetchSaldoFuturo).toHaveBeenCalledTimes(2));

    rerender(<SaldoFuturoDesplegable cajaId={2} refreshKey={1} />);
    await waitFor(() => expect(fetchSaldoFuturo).toHaveBeenCalledTimes(3));
    expect(fetchSaldoFuturo).toHaveBeenLastCalledWith(2);
  });

  it("no consulta mientras está cerrado aunque cambie refreshKey, y carga al abrir", async () => {
    const { rerender } = render(<SaldoFuturoDesplegable cajaId={1} refreshKey={0} />);

    rerender(<SaldoFuturoDesplegable cajaId={1} refreshKey={1} />);
    rerender(<SaldoFuturoDesplegable cajaId={2} refreshKey={1} />);
    expect(fetchSaldoFuturo).not.toHaveBeenCalled();

    expand();
    await waitFor(() => expect(fetchSaldoFuturo).toHaveBeenCalledTimes(1));
    expect(fetchSaldoFuturo).toHaveBeenCalledWith(2);
  });

  it("no consulta sin caja seleccionada", async () => {
    render(<SaldoFuturoDesplegable cajaId={null} />);
    expand();

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetchSaldoFuturo).not.toHaveBeenCalled();
  });

  it("al colapsar y volver a expandir pide datos frescos", async () => {
    render(<SaldoFuturoDesplegable cajaId={1} />);
    expand();
    await waitFor(() => expect(fetchSaldoFuturo).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByText("Saldo a futuro")); // colapsa
    expect(screen.getByText("Saldo a futuro").closest("details")).not.toHaveAttribute("open");
    fireEvent.click(screen.getByText("Saldo a futuro")); // expande
    await waitFor(() => expect(fetchSaldoFuturo).toHaveBeenCalledTimes(2));
  });
});

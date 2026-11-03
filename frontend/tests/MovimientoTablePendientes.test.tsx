/**
 * Registro: los cheques pendientes figuran en el listado habitual junto a los movimientos
 * que impactan el saldo, con su estado, su fecha de liquidación prevista y sus acciones.
 */

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import MovimientoTable from "../src/components/MovimientoTable";
import type { Movimiento } from "../src/services/api";

const caja = { id: 1, nombre: "Ebel", slug: "ebel" };

const comun: Movimiento = {
  id: 1,
  descripcion: "Honorarios",
  monto: "100.00",
  tipo: "entrada",
  moneda: "ARS",
  subtotal: "100.00",
  fecha: "2026-10-20T12:00:00-03:00",
  editable: true,
  caja,
  instrumento: "ninguno",
  estado: null,
  fecha_carga: "2026-10-20T12:00:00-03:00",
  fecha_liquidacion: null,
  fecha_liquidado: null,
  liquidable: false,
};

const pendiente: Movimiento = {
  ...comun,
  id: 2,
  descripcion: "Cheque Macro 0044",
  subtotal: null,
  instrumento: "cheque",
  estado: "pendiente",
  fecha_liquidacion: "2020-01-01",
  liquidable: true,
};

// Fecha de liquidación todavía no alcanzada.
const futuro: Movimiento = { ...pendiente, id: 4, descripcion: "Cheque a futuro", fecha_liquidacion: "2999-01-01" };

const liquidado: Movimiento = {
  ...pendiente,
  id: 3,
  descripcion: "Cheque ya cobrado",
  subtotal: "600.00",
  estado: "liquidado",
  fecha_liquidado: "2026-10-21T10:00:00-03:00",
  liquidable: false,
};

function row(text: string): HTMLElement {
  return screen.getByText(text).closest("tr") as HTMLElement;
}

describe("MovimientoTable — cheques pendientes en el listado", () => {
  it("distingue pendiente, liquidado y común", () => {
    render(
      <MovimientoTable movimientos={[comun, pendiente, liquidado]} onLiquidar={vi.fn()} />,
    );

    expect(within(row("Cheque Macro 0044")).getByText("Pendiente")).toBeInTheDocument();
    expect(within(row("Cheque Macro 0044")).queryByText("Liquidado")).not.toBeInTheDocument();
    expect(within(row("Cheque ya cobrado")).getByText("Liquidado")).toBeInTheDocument();
    expect(within(row("Honorarios")).queryByText(/pendiente|liquidado/i)).not.toBeInTheDocument();
  });

  it("el pendiente no tiene subtotal y muestra su fecha de liquidación prevista", () => {
    render(<MovimientoTable movimientos={[pendiente]} onLiquidar={vi.fn()} />);

    const fila = row("Cheque Macro 0044");
    expect(within(fila).getByText("—")).toBeInTheDocument();
    expect(within(fila).getByText(/liquida el 01\/01\/2020/i)).toBeInTheDocument();
  });

  it("solo el pendiente liquidable ofrece Liquidar y dispara onLiquidar", () => {
    const onLiquidar = vi.fn();
    render(
      <MovimientoTable
        movimientos={[comun, pendiente, liquidado]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onLiquidar={onLiquidar}
      />,
    );

    expect(screen.getAllByRole("button", { name: /^liquidar$/i })).toHaveLength(1);
    fireEvent.click(within(row("Cheque Macro 0044")).getByRole("button", { name: /^liquidar$/i }));
    expect(onLiquidar).toHaveBeenCalledWith(pendiente);
  });

  it("sin onLiquidar (Consulta) no hay botón Liquidar", () => {
    render(<MovimientoTable movimientos={[pendiente]} />);

    expect(screen.queryByRole("button", { name: /liquidar/i })).not.toBeInTheDocument();
  });

  it("antes de la fecha de liquidación Liquidar queda deshabilitado (en gris) y no dispara nada", () => {
    const onLiquidar = vi.fn();
    render(<MovimientoTable movimientos={[futuro, pendiente]} onLiquidar={onLiquidar} />);

    const botonFuturo = within(row("Cheque a futuro")).getByRole("button", { name: /^liquidar$/i });
    expect(botonFuturo).toBeDisabled();
    expect(botonFuturo).toHaveAttribute("title", "Disponible desde el 01/01/2999");
    fireEvent.click(botonFuturo);
    expect(onLiquidar).not.toHaveBeenCalled();

    // Llegada la fecha (vencido o de hoy) el botón está habilitado.
    expect(
      within(row("Cheque Macro 0044")).getByRole("button", { name: /^liquidar$/i }),
    ).toBeEnabled();
  });
});

describe("MovimientoTable columna Valor de caja total", () => {
  const base = {
    descripcion: "x", monto: "1.00", tipo: "entrada" as const, moneda: "ARS" as const,
    subtotal: "1.00", fecha: "2026-10-01T10:00:00-03:00", editable: false,
    caja: { id: 1, nombre: "Ebel", slug: "ebel" },
  };

  it("se muestra solo cuando el servidor envía valor_total", () => {
    const { rerender } = render(
      <MovimientoTable movimientos={[{ ...base, id: 1, valor_total: "1500.00" } as never]} />,
    );
    expect(screen.getByText("Valor de caja total")).toBeInTheDocument();
    expect(screen.getByText("1500.00")).toBeInTheDocument();

    rerender(<MovimientoTable movimientos={[{ ...base, id: 1 } as never]} />);
    expect(screen.queryByText("Valor de caja total")).not.toBeInTheDocument();
  });
});

/**
 * T015 — feature 011: marcas de endose en el historial y acciones según `editable`.
 */

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import MovimientoTable from "../src/components/MovimientoTable";
import type { Movimiento } from "../src/services/api";

const cajaA = { id: 1, nombre: "Bambina", slug: "bambina" };
const cajaB = { id: 2, nombre: "Ebel", slug: "ebel" };

const base: Movimiento = {
  id: 1,
  descripcion: "Movimiento base",
  monto: "500.00",
  tipo: "entrada",
  moneda: "ARS",
  subtotal: "500.00",
  fecha: "2026-10-20T12:00:00-03:00",
  editable: true,
  caja: cajaA,
  instrumento: "ninguno",
  estado: null,
  fecha_carga: "2026-10-20T12:00:00-03:00",
  fecha_liquidacion: null,
  fecha_liquidado: null,
  liquidable: false,
  endosable: false,
  endosado_a: null,
  endose_origen: null,
};

const endosado: Movimiento = {
  ...base,
  id: 10,
  descripcion: "Cheque endosado",
  instrumento: "cheque",
  estado: "liquidado",
  fecha_liquidado: "2026-10-21T10:00:00-03:00",
  editable: false,
  endosado_a: cajaB,
};

const destino: Movimiento = {
  ...base,
  id: 11,
  descripcion: "Endose cheque: Cheque endosado (Caja Bambina)",
  tipo: "salida",
  caja: cajaB,
  editable: false,
  endose_origen: { caja: cajaA, cheque_id: 10 },
};

function row(text: string): HTMLElement {
  return screen.getByText(text).closest("tr") as HTMLElement;
}

describe("MovimientoTable — endose (T015)", () => {
  it("muestra 'Endosado → caja' en el cheque endosado", () => {
    render(<MovimientoTable movimientos={[endosado]} />);
    expect(within(row("Cheque endosado")).getByText("Endosado → Ebel")).toBeInTheDocument();
  });

  it("muestra 'Endose desde caja' en el movimiento destino", () => {
    render(<MovimientoTable movimientos={[destino]} />);
    expect(
      within(row(destino.descripcion)).getByText("Endose desde Bambina"),
    ).toBeInTheDocument();
  });

  it("no muestra marcas en un movimiento común", () => {
    render(<MovimientoTable movimientos={[base]} />);
    expect(screen.queryByText(/endosado →|endose desde/i)).not.toBeInTheDocument();
  });

  it("oculta Editar/Eliminar cuando editable es false y los muestra si es true", () => {
    render(
      <MovimientoTable
        movimientos={[base, endosado, destino]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(within(row("Movimiento base")).getByRole("button", { name: "Editar" })).toBeInTheDocument();
    expect(within(row("Movimiento base")).getByRole("button", { name: "Eliminar" })).toBeInTheDocument();
    for (const text of ["Cheque endosado", destino.descripcion]) {
      expect(within(row(text)).queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
      expect(within(row(text)).queryByRole("button", { name: "Eliminar" })).not.toBeInTheDocument();
    }
  });
});

/**
 * T022 — TDD: component tests para el diálogo complementario USD (US2)
 *
 * Regla de negocio (spec FR-006, FR-007, FR-010, FR-011):
 *   - USD + Entrada → cartel exacto "¿Registrar también como salida?"
 *   - USD + Salida  → cartel exacto "¿Registrar también como entrada?"
 *   - ARS nunca muestra el cartel
 *   - Validar descripcion y monto ANTES de mostrar el cartel
 *
 * Estos tests DEBEN FALLAR hasta que T025 implemente el diálogo en MovimientoForm.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MovimientoForm from "../src/components/MovimientoForm";

const onSubmit = vi.fn();

function renderForm() {
  return render(
    <MemoryRouter>
      <MovimientoForm
        cajas={[{ id: 1, nombre: "Bambina", slug: "bambina" }]}
        activeCajaId={1}
        onSubmit={onSubmit}
        disabled={false}
      />
    </MemoryRouter>,
  );
}

describe("MovimientoForm — diálogo complementario USD", () => {
  beforeEach(() => {
    onSubmit.mockReset();
    onSubmit.mockResolvedValue(undefined);
  });

  it("T022: USD + Entrada muestra el cartel '¿Registrar también como salida?'", async () => {
    renderForm();

    // Seleccionar USD
    const monedaSelect = screen.getByLabelText(/moneda/i) as HTMLSelectElement;
    fireEvent.change(monedaSelect, { target: { value: "USD" } });

    // Completar descripcion y monto
    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Cobro USD" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "100.00" },
    });

    // Presionar Entrada
    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    // El cartel debe aparecer
    await waitFor(() => {
      expect(
        screen.getByText(/¿Registrar también como salida\?/i),
      ).toBeInTheDocument();
    });
  });

  it("T022: USD + Salida muestra el cartel '¿Registrar también como entrada?'", async () => {
    renderForm();

    const monedaSelect = screen.getByLabelText(/moneda/i) as HTMLSelectElement;
    fireEvent.change(monedaSelect, { target: { value: "USD" } });

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Pago USD" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "50.00" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^salida$/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/¿Registrar también como entrada\?/i),
      ).toBeInTheDocument();
    });
  });

  it("T022: ARS + Entrada NO muestra el cartel de complementario", async () => {
    renderForm();

    // ARS es el default — no cambiar moneda
    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Cobro ARS" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "200.00" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    // Esperar que onSubmit sea llamado (ARS va directo)
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled();
    });

    // El cartel no debe existir
    expect(
      screen.queryByText(/¿Registrar también como/i),
    ).not.toBeInTheDocument();
  });

  it("T022: ARS + Salida NO muestra el cartel de complementario", async () => {
    renderForm();

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Gasto ARS" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "300.00" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^salida$/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled();
    });

    expect(
      screen.queryByText(/¿Registrar también como/i),
    ).not.toBeInTheDocument();
  });

  it("T022: confirmar el cartel llama onSubmit con registrar_complementario=true", async () => {
    renderForm();

    const monedaSelect = screen.getByLabelText(/moneda/i) as HTMLSelectElement;
    fireEvent.change(monedaSelect, { target: { value: "USD" } });
    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Par USD" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "75.00" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    // Esperar cartel
    await waitFor(() => {
      expect(
        screen.getByText(/¿Registrar también como salida\?/i),
      ).toBeInTheDocument();
    });

    // Confirmar
    fireEvent.click(screen.getByRole("button", { name: /confirmar|sí|si/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          moneda: "USD",
          tipo: "entrada",
          registrar_complementario: true,
        }),
        expect.any(Array),
      );
    });
  });

  it("T022: rechazar el cartel llama onSubmit con registrar_complementario=false", async () => {
    renderForm();

    const monedaSelect = screen.getByLabelText(/moneda/i) as HTMLSelectElement;
    fireEvent.change(monedaSelect, { target: { value: "USD" } });
    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Solo principal" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "60.00" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^salida$/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/¿Registrar también como entrada\?/i),
      ).toBeInTheDocument();
    });

    // Rechazar
    fireEvent.click(screen.getByRole("button", { name: /cancelar|no/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          moneda: "USD",
          tipo: "salida",
          registrar_complementario: false,
        }),
        expect.any(Array),
      );
    });
  });

  it("T022: el cartel no aparece si falta descripcion (validar antes)", async () => {
    renderForm();

    const monedaSelect = screen.getByLabelText(/moneda/i) as HTMLSelectElement;
    fireEvent.change(monedaSelect, { target: { value: "USD" } });

    // Monto sí, descripcion vacía
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "100.00" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    // Sin esperar demasiado, el cartel no debe aparecer
    await new Promise((r) => setTimeout(r, 100));
    expect(
      screen.queryByText(/¿Registrar también como/i),
    ).not.toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("T022: el cartel no aparece si falta monto (validar antes)", async () => {
    renderForm();

    const monedaSelect = screen.getByLabelText(/moneda/i) as HTMLSelectElement;
    fireEvent.change(monedaSelect, { target: { value: "USD" } });

    // Descripcion sí, monto vacío
    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Sin monto" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await new Promise((r) => setTimeout(r, 100));
    expect(
      screen.queryByText(/¿Registrar también como/i),
    ).not.toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

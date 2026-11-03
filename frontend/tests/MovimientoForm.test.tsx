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
 *
 * T013–T016 — TDD: tests para el nuevo comportamiento US1+US2 (feature 009):
 *   - T013: Botón "Entrada y Salida" existe en el DOM
 *   - T014: Botón "Entrada y Salida" llama onSubmit con registrar_complementario=true, tipo="entrada"
 *   - T015: USD + Entrada va directo a onSubmit SIN mostrar el modal
 *   - T016: el elemento complementario-dialog-backdrop NO está presente en el DOM
 *
 * T013–T016 DEBEN FALLAR hasta que T017–T019 implementen los cambios en MovimientoForm.tsx
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

  it("T022: USD + Entrada llama onSubmit directamente sin mostrar el cartel", async () => {
    renderForm();

    const monedaSelect = screen.getByLabelText(/moneda/i) as HTMLSelectElement;
    fireEvent.change(monedaSelect, { target: { value: "USD" } });

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Cobro USD" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "100.00" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    // El cartel NO debe aparecer — USD va directo (feature 009)
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled();
    });
    expect(
      screen.queryByText(/¿Registrar también como salida\?/i),
    ).not.toBeInTheDocument();
  });

  it("T022: USD + Salida llama onSubmit directamente sin mostrar el cartel", async () => {
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
      expect(onSubmit).toHaveBeenCalled();
    });
    expect(
      screen.queryByText(/¿Registrar también como entrada\?/i),
    ).not.toBeInTheDocument();
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

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Par USD" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "75.00" },
    });

    // Usar "Entrada y Salida" para registrar_complementario=true (feature 009)
    fireEvent.click(screen.getByRole("button", { name: /^entrada y salida$/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
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

    // Pulsar Salida directa (sin modal) → registrar_complementario=false
    fireEvent.click(screen.getByRole("button", { name: /^salida$/i }));

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

// ─────────────────────────────────────────────────────────────────────────────
// T013–T016 — TDD: Botón "Entrada y Salida" + eliminación del modal (feature 009)
// Estos tests DEBEN FALLAR hasta que T017–T019 implementen los cambios.
// ─────────────────────────────────────────────────────────────────────────────

describe("MovimientoForm — botón Entrada y Salida (T013–T016)", () => {
  beforeEach(() => {
    onSubmit.mockReset();
    onSubmit.mockResolvedValue(undefined);
  });

  /**
   * T013: El botón "Entrada y Salida" debe estar presente en el DOM.
   * Clase esperada: button btn-entrada-salida movimiento-form__action
   */
  it("T013: renderiza el botón 'Entrada y Salida' en el DOM", () => {
    renderForm();
    expect(
      screen.getByRole("button", { name: /^entrada y salida$/i }),
    ).toBeInTheDocument();
  });

  /**
   * T014: Al pulsar "Entrada y Salida", onSubmit se llama con
   * registrar_complementario=true y tipo="entrada".
   */
  it("T014: pulsar 'Entrada y Salida' llama onSubmit con registrar_complementario=true y tipo='entrada'", async () => {
    renderForm();

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Cobro USD entrada y salida" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "150.00" },
    });

    fireEvent.click(
      screen.getByRole("button", { name: /^entrada y salida$/i }),
    );

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          tipo: "entrada",
          registrar_complementario: true,
        }),
        expect.any(Array),
      );
    });
  });

  /**
   * T015: Al pulsar "Entrada" con moneda USD, onSubmit se llama directamente
   * (sin mostrar el diálogo modal).
   */
  it("T015: USD + Entrada llama onSubmit directamente sin mostrar el modal", async () => {
    renderForm();

    const monedaSelect = screen.getByLabelText(/moneda/i) as HTMLSelectElement;
    fireEvent.change(monedaSelect, { target: { value: "USD" } });

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Cobro USD directo" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "200.00" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    // onSubmit debe ser llamado directamente, sin esperar confirmación del modal
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          moneda: "USD",
          tipo: "entrada",
          registrar_complementario: false,
        }),
        expect.any(Array),
      );
    });

    // El modal NO debe aparecer en ningún momento
    expect(
      screen.queryByText(/¿Registrar también como/i),
    ).not.toBeInTheDocument();
  });

  /**
   * T016: El elemento complementario-dialog-backdrop NO debe estar presente
   * en el DOM para ninguna moneda (modal eliminado).
   */
  it("T016: el elemento complementario-dialog-backdrop NO existe en el DOM", () => {
    renderForm();

    // Sin interacción: el backdrop no debe estar en el DOM
    expect(
      document.querySelector(".complementario-dialog-backdrop"),
    ).not.toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T035–T038 — TDD: Selector de fecha manual (US3/feature 009)
//
// Estos tests DEBEN FALLAR hasta que T039–T042 implementen:
//   - T039: fecha_manual?: string en CreateMovimientoPayload (api.ts)
//   - T040: estado fechaManual en MovimientoForm.tsx
//   - T041: <input type="date"> con label "Fecha (opcional)"
//   - T042: doSubmit incluye fecha_manual en el payload
// ─────────────────────────────────────────────────────────────────────────────

describe("MovimientoForm — selector de fecha manual (T035–T038)", () => {
  beforeEach(() => {
    onSubmit.mockReset();
    onSubmit.mockResolvedValue(undefined);
  });

  /**
   * T035: El formulario debe renderizar un <input type="date">
   * con label "Fecha (opcional)".
   */
  it("T035: renderiza un campo de fecha con label 'Fecha (opcional)'", () => {
    renderForm();

    const label = screen.getByLabelText(/fecha \(opcional\)/i);
    expect(label).toBeInTheDocument();
    expect(label).toHaveAttribute("type", "date");
  });

  /**
   * T036: Al seleccionar una fecha y pulsar "Entrada", onSubmit recibe
   * el payload con fecha_manual: "YYYY-MM-DD".
   */
  it("T036: seleccionar fecha y pulsar Entrada incluye fecha_manual en el payload", async () => {
    renderForm();

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Cobro con fecha" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "100.00" },
    });
    fireEvent.change(screen.getByLabelText(/fecha \(opcional\)/i), {
      target: { value: "2026-09-01" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ fecha_manual: "2026-09-01" }),
        expect.any(Array),
      );
    });
  });

  /**
   * T037: Sin fecha seleccionada, onSubmit recibe payload sin campo
   * fecha_manual (undefined o ausente).
   */
  it("T037: sin fecha seleccionada, el payload NO incluye fecha_manual", async () => {
    renderForm();

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Cobro sin fecha" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "200.00" },
    });
    // No se cambia el selector de fecha — queda vacío

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled();
    });

    const [payload] = onSubmit.mock.calls[0] as [Record<string, unknown>, unknown[]];
    // fecha_manual debe ser undefined o no existir en el payload
    expect(payload.fecha_manual).toBeUndefined();
  });

  /**
   * T038: Cambiar activeCajaId NO resetea el valor del selector de fecha.
   * La fecha es un dato del movimiento a registrar, no de la caja.
   */
  it("T038: cambiar activeCajaId NO resetea el selector de fecha", () => {
    const { rerender } = render(
      <MemoryRouter>
        <MovimientoForm
          cajas={[
            { id: 1, nombre: "Bambina", slug: "bambina" },
            { id: 2, nombre: "Otra", slug: "otra" },
          ]}
          activeCajaId={1}
          onSubmit={onSubmit}
          disabled={false}
        />
      </MemoryRouter>,
    );

    const dateInput = screen.getByLabelText(/fecha \(opcional\)/i);
    fireEvent.change(dateInput, { target: { value: "2026-09-05" } });
    expect(dateInput).toHaveValue("2026-09-05");

    // Cambiar a otra caja (simula selección en la UI)
    rerender(
      <MemoryRouter>
        <MovimientoForm
          cajas={[
            { id: 1, nombre: "Bambina", slug: "bambina" },
            { id: 2, nombre: "Otra", slug: "otra" },
          ]}
          activeCajaId={2}
          onSubmit={onSubmit}
          disabled={false}
        />
      </MemoryRouter>,
    );

    // La fecha NO debe haber sido reseteada
    expect(screen.getByLabelText(/fecha \(opcional\)/i)).toHaveValue("2026-09-05");
  });

  /**
   * T038b: Tras un submit exitoso, el selector de fecha se resetea a vacío.
   * El monto y la descripción también se limpian — comportamiento consistente.
   */
  it("T038b: tras submit exitoso, el selector de fecha se resetea a vacío", async () => {
    renderForm();

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Cobro con fecha" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "500.00" },
    });
    fireEvent.change(screen.getByLabelText(/fecha \(opcional\)/i), {
      target: { value: "2026-09-10" },
    });

    expect(screen.getByLabelText(/fecha \(opcional\)/i)).toHaveValue("2026-09-10");

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled();
    });

    // Tras el submit exitoso, el selector debe volver a vacío
    expect(screen.getByLabelText(/fecha \(opcional\)/i)).toHaveValue("");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// T022 — feature 010 (US1): Instrumento (Cheque / Echeque) y Fecha de liquidación
// ─────────────────────────────────────────────────────────────────────────────

describe("MovimientoForm — instrumento cheque/echeque (T022, feature 010)", () => {
  beforeEach(() => {
    onSubmit.mockReset();
    onSubmit.mockResolvedValue(undefined);
    // "Hoy" fijo: 21/10/2026 en Argentina → mínimo de fecha de liquidación = 22/10/2026
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-10-21T15:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function fillBasics() {
    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Cheque cliente" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "500.00" },
    });
  }

  function selectInstrumento(value: "ninguno" | "cheque" | "echeque") {
    fireEvent.change(screen.getByLabelText(/instrumento/i), {
      target: { value },
    });
  }

  it("muestra un selector Instrumento con '-' por defecto, Cheque y Echeque", () => {
    renderForm();

    const select = screen.getByLabelText(/instrumento/i) as HTMLSelectElement;
    expect(select.tagName).toBe("SELECT");
    expect(select.value).toBe("ninguno");
    const options = Array.from(select.options).map((o) => [o.value, o.textContent]);
    expect(options).toEqual([
      ["ninguno", "-"],
      ["cheque", "Cheque"],
      ["echeque", "Echeque"],
    ]);
  });

  it("ubica Instrumento a la derecha de 'Fecha (opcional)' y antes de Entrada", () => {
    renderForm();

    const fecha = screen.getByLabelText(/fecha \(opcional\)/i);
    const instrumento = screen.getByLabelText(/instrumento/i);
    const entrada = screen.getByRole("button", { name: /^entrada$/i });

    expect(
      fecha.compareDocumentPosition(instrumento) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      instrumento.compareDocumentPosition(entrada) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("con '-' no muestra Fecha de liquidación y el payload es idéntico al anterior", async () => {
    renderForm();
    expect(screen.queryByLabelText(/fecha de liquidación/i)).not.toBeInTheDocument();

    fillBasics();
    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0]).toEqual({
      descripcion: "Cheque cliente",
      monto: "500.00",
      tipo: "entrada",
      moneda: "ARS",
      registrar_complementario: false,
    });
  });

  it.each(["cheque", "echeque"] as const)(
    "con %s aparece Fecha de liquidación (obligatoria, mínimo mañana)",
    (instrumento) => {
      renderForm();

      selectInstrumento(instrumento);

      const fecha = screen.getByLabelText(/fecha de liquidación/i);
      expect(fecha).toHaveAttribute("type", "date");
      expect(fecha).toBeRequired();
      expect(fecha).toHaveAttribute("min", "2026-10-22");
    },
  );

  it("descarta la fecha de liquidación al volver a '-'", () => {
    renderForm();
    selectInstrumento("cheque");
    fireEvent.change(screen.getByLabelText(/fecha de liquidación/i), {
      target: { value: "2026-11-15" },
    });

    selectInstrumento("ninguno");
    expect(screen.queryByLabelText(/fecha de liquidación/i)).not.toBeInTheDocument();

    selectInstrumento("cheque");
    expect(screen.getByLabelText(/fecha de liquidación/i)).toHaveValue("");
  });

  it("oculta 'Entrada y Salida' cuando hay un instrumento seleccionado", () => {
    renderForm();
    expect(screen.getByRole("button", { name: /entrada y salida/i })).toBeInTheDocument();

    selectInstrumento("echeque");
    expect(
      screen.queryByRole("button", { name: /entrada y salida/i }),
    ).not.toBeInTheDocument();

    selectInstrumento("ninguno");
    expect(screen.getByRole("button", { name: /entrada y salida/i })).toBeInTheDocument();
  });

  it("envía instrumento y fecha_liquidacion al pulsar Entrada con cheque", async () => {
    renderForm();
    fillBasics();
    selectInstrumento("cheque");
    fireEvent.change(screen.getByLabelText(/fecha de liquidación/i), {
      target: { value: "2026-11-15" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0]).toEqual({
      descripcion: "Cheque cliente",
      monto: "500.00",
      tipo: "entrada",
      moneda: "ARS",
      registrar_complementario: false,
      instrumento: "cheque",
      fecha_liquidacion: "2026-11-15",
    });
  });

  it("envía instrumento echeque y tipo salida al pulsar Salida", async () => {
    renderForm();
    fillBasics();
    selectInstrumento("echeque");
    fireEvent.change(screen.getByLabelText(/fecha de liquidación/i), {
      target: { value: "2026-12-01" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^salida$/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      tipo: "salida",
      instrumento: "echeque",
      fecha_liquidacion: "2026-12-01",
      registrar_complementario: false,
    });
  });

  it("no envía y avisa si falta la fecha de liquidación", async () => {
    renderForm();
    fillBasics();
    selectInstrumento("cheque");

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(
      await screen.findByText(/la fecha de liquidación es obligatoria/i),
    ).toBeInTheDocument();
  });

  it.each(["2026-10-21", "2026-10-01"])(
    "no envía y avisa si la fecha de liquidación (%s) no es posterior a hoy",
    async (fecha) => {
      renderForm();
      fillBasics();
      selectInstrumento("cheque");
      fireEvent.change(screen.getByLabelText(/fecha de liquidación/i), {
        target: { value: fecha },
      });

      fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

      expect(onSubmit).not.toHaveBeenCalled();
      expect(
        await screen.findByText(/la fecha de liquidación debe ser posterior a hoy/i),
      ).toBeInTheDocument();
    },
  );

  it("mantiene la fecha (opcional) como fecha de carga junto con el cheque", async () => {
    renderForm();
    fillBasics();
    fireEvent.change(screen.getByLabelText(/fecha \(opcional\)/i), {
      target: { value: "2026-10-15" },
    });
    selectInstrumento("cheque");
    fireEvent.change(screen.getByLabelText(/fecha de liquidación/i), {
      target: { value: "2026-11-15" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      fecha_manual: "2026-10-15",
      fecha_liquidacion: "2026-11-15",
      instrumento: "cheque",
    });
  });

  it("tras un envío exitoso vuelve a '-' y limpia la fecha de liquidación", async () => {
    renderForm();
    fillBasics();
    selectInstrumento("cheque");
    fireEvent.change(screen.getByLabelText(/fecha de liquidación/i), {
      target: { value: "2026-11-15" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    await waitFor(() => {
      expect((screen.getByLabelText(/instrumento/i) as HTMLSelectElement).value).toBe(
        "ninguno",
      );
    });
    expect(screen.queryByLabelText(/fecha de liquidación/i)).not.toBeInTheDocument();
  });

  it("muestra el error del servidor y conserva el cheque cargado en el formulario", async () => {
    onSubmit.mockRejectedValue(new Error("boom"));
    renderForm();
    fillBasics();
    selectInstrumento("cheque");
    fireEvent.change(screen.getByLabelText(/fecha de liquidación/i), {
      target: { value: "2026-11-15" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    expect(await screen.findByText(/no se pudo registrar el movimiento/i)).toBeInTheDocument();
    expect((screen.getByLabelText(/instrumento/i) as HTMLSelectElement).value).toBe("cheque");
    expect(screen.getByLabelText(/fecha de liquidación/i)).toHaveValue("2026-11-15");
  });
});

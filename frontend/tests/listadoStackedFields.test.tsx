import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ChequesPendientesBlock from "../src/components/ChequesPendientesBlock";
import MovimientoTable from "../src/components/MovimientoTable";
import PlazoFijoTable from "../src/components/PlazoFijoTable";
import SaldoFuturoDesplegable from "../src/components/SaldoFuturoDesplegable";
import ChequesPage from "../src/pages/ChequesPage";
import ConfiguracionCajasPage from "../src/pages/ConfiguracionCajasPage";
import type { Movimiento, PlazoFijo } from "../src/services/api";

const listCajasConfig = vi.fn();
const fetchCheques = vi.fn();
const fetchChequesPendientes = vi.fn();
const fetchSaldoFuturo = vi.fn();

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({
    token: "test-token",
    rol: "secretaria",
    username: "user",
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock("../src/services/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/services/api")>();
  return {
    ...actual,
    listCajasConfig: (...args: unknown[]) => listCajasConfig(...args),
    fetchCheques: (...args: unknown[]) => fetchCheques(...args),
    fetchChequesPendientes: (...args: unknown[]) => fetchChequesPendientes(...args),
    fetchSaldoFuturo: (...args: unknown[]) => fetchSaldoFuturo(...args),
    createCaja: vi.fn(),
    archiveCaja: vi.fn(),
    unarchiveCaja: vi.fn(),
  };
});

const caja = { id: 1, nombre: "Bambina", slug: "bambina" };

const movimiento: Movimiento = {
  id: 10,
  descripcion: "Pago cliente con texto largo para envolver",
  monto: "5000.00",
  tipo: "entrada",
  moneda: "ARS",
  subtotal: "5000.00",
  fecha: "2026-08-03T14:30:00-03:00",
  editable: true,
  caja,
  instrumento: "ninguno",
  estado: null,
  fecha_carga: "2026-08-03T14:30:00-03:00",
  fecha_liquidacion: null,
  fecha_liquidado: null,
  liquidable: false,
  endosable: false,
  endosado_a: null,
  endose_origen: null,
};

const plazoFijo: PlazoFijo = {
  id: 20,
  monto_ingresado: "10000.00",
  monto_a_vencimiento: "11000.00",
  fecha_vencimiento: "2026-12-01",
  vencido: false,
  created_at: "2026-08-01T10:00:00-03:00",
  caja,
};

function labelsOfFirstDataRow(container: HTMLElement): string[] {
  const row = Array.from(container.querySelectorAll("tbody tr")).find((candidate) =>
    candidate.querySelector("td[data-label]"),
  );
  if (!row) {
    return [];
  }
  return Array.from(row.querySelectorAll("td")).map(
    (cell) => cell.getAttribute("data-label") ?? "",
  );
}

describe("listadoStackedFields", () => {
  it("exposes movimiento field labels in PC column order including Acciones", () => {
    const { container } = render(
      <MovimientoTable
        movimientos={[movimiento]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(labelsOfFirstDataRow(container)).toEqual([
      "Descripción",
      "Monto",
      "Subtotal",
      "Fecha",
      "Acciones",
    ]);
  });

  it("omits Acciones on consulta-style movimiento rows without callbacks", () => {
    const { container } = render(
      <MovimientoTable movimientos={[movimiento]} />,
    );

    expect(labelsOfFirstDataRow(container)).toEqual([
      "Descripción",
      "Monto",
      "Subtotal",
      "Fecha",
    ]);
  });

  it("does not split the empty movimientos state into field blocks", () => {
    const { container } = render(<MovimientoTable movimientos={[]} />);
    const empty = container.querySelector(".movimiento-table-empty");
    expect(empty).not.toBeNull();
    expect(empty?.getAttribute("data-label")).toBeNull();
    expect(empty?.textContent).toMatch(/no hay movimientos/i);
  });

  it("exposes plazo fijo field labels in PC column order including Acciones", () => {
    const { container } = render(
      <PlazoFijoTable
        plazosFijos={[plazoFijo]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(labelsOfFirstDataRow(container)).toEqual([
      "Monto ingresado",
      "Fecha de vencimiento",
      "Monto a vencimiento",
      "Acciones",
    ]);
  });
});

// ---------------------------------------------------------------------------
// T028 — TDD component tests US3
// Deben FALLAR hasta que T031 y T032 implementen las funcionalidades.
// ---------------------------------------------------------------------------

describe("listadoStackedFields — moneda en monto (T028)", () => {
  it("shows the moneda label next to the monto for ARS", () => {
    const movimientoARS: Movimiento = { ...movimiento, moneda: "ARS" };
    render(<MovimientoTable movimientos={[movimientoARS]} />);

    const montoCell = screen.getByText((_content, element) => {
      return (
        element?.getAttribute("data-label") === "Monto" &&
        (element?.textContent?.includes("ARS") ?? false)
      );
    });
    expect(montoCell).toBeInTheDocument();
  });

  it("shows the moneda label next to the monto for USD", () => {
    const movimientoUSD: Movimiento = { ...movimiento, moneda: "USD" };
    render(<MovimientoTable movimientos={[movimientoUSD]} />);

    const montoCell = screen.getByText((_content, element) => {
      return (
        element?.getAttribute("data-label") === "Monto" &&
        (element?.textContent?.includes("USD") ?? false)
      );
    });
    expect(montoCell).toBeInTheDocument();
  });

  it("keeps entrada color class when moneda ARS is shown", () => {
    const movimientoARS: Movimiento = { ...movimiento, tipo: "entrada", moneda: "ARS" };
    const { container } = render(<MovimientoTable movimientos={[movimientoARS]} />);

    const montoCell = container.querySelector(".movimiento-entrada");
    expect(montoCell).not.toBeNull();
    expect(montoCell?.textContent).toContain("ARS");
  });

  it("keeps salida color class when moneda USD is shown", () => {
    const movimientoUSD: Movimiento = {
      ...movimiento,
      tipo: "salida",
      moneda: "USD",
    };
    const { container } = render(<MovimientoTable movimientos={[movimientoUSD]} />);

    const montoCell = container.querySelector(".movimiento-salida");
    expect(montoCell).not.toBeNull();
    expect(montoCell?.textContent).toContain("USD");
  });
});

describe("listadoStackedFields — configuracion", () => {
  beforeEach(() => {
    listCajasConfig.mockReset();
    listCajasConfig.mockResolvedValue([
      { id: 1, nombre: "Bambina", slug: "bambina", estado: "activa" },
    ]);
  });

  it("exposes caja config field labels in PC column order", async () => {
    const { container } = render(
      <MemoryRouter>
        <ConfiguracionCajasPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    expect(labelsOfFirstDataRow(container)).toEqual([
      "Caja",
      "Estado",
      "Acciones",
    ]);
  });
});

// ---------------------------------------------------------------------------
// T080 — feature 010: tablas nuevas con celdas apilables (data-label)
// ---------------------------------------------------------------------------

const cheque: Movimiento = {
  ...movimiento,
  id: 30,
  subtotal: null,
  editable: false,
  instrumento: "cheque",
  estado: "pendiente",
  fecha_liquidacion: "2026-10-15",
  liquidable: true,
  endosable: false,
  endosado_a: null,
  endose_origen: null,
};

const paginated = (items: Movimiento[]) => ({
  items,
  page: 1,
  page_size: 20,
  total_items: items.length,
  total_pages: items.length ? 1 : 0,
});

describe("listadoStackedFields — cheques (T080)", () => {
  beforeEach(() => {
    fetchCheques.mockReset();
    fetchChequesPendientes.mockReset();
    fetchSaldoFuturo.mockReset();
  });

  it("exposes data-label cells in the pending cheques block (Registro: with Acciones)", async () => {
    fetchChequesPendientes.mockResolvedValue(paginated([cheque]));
    const { container } = render(
      <ChequesPendientesBlock
        cajaId={1}
        onLiquidar={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    await waitFor(() => expect(container.querySelector("td[data-label]")).not.toBeNull());
    expect(labelsOfFirstDataRow(container)).toEqual([
      "Descripción",
      "Monto",
      "Instrumento",
      "Fecha de carga",
      "Fecha de liquidación",
      "Acciones",
    ]);
  });

  it("omits Acciones in the read-only pending cheques block (Consulta)", async () => {
    fetchChequesPendientes.mockResolvedValue(paginated([cheque]));
    const { container } = render(<ChequesPendientesBlock cajaId={1} readOnly />);

    await waitFor(() => expect(container.querySelector("td[data-label]")).not.toBeNull());
    expect(labelsOfFirstDataRow(container)).toEqual([
      "Descripción",
      "Monto",
      "Instrumento",
      "Fecha de carga",
      "Fecha de liquidación",
    ]);
  });

  it("exposes data-label cells in both Cheques page listings", async () => {
    fetchCheques.mockImplementation(() => Promise.resolve(paginated([cheque])));
    const { container } = render(
      <MemoryRouter>
        <ChequesPage />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(container.querySelectorAll("td[data-label]").length).toBeGreaterThan(0),
    );
    const tables = Array.from(container.querySelectorAll("table"));
    expect(tables).toHaveLength(2);
    for (const table of tables) {
      expect(labelsOfFirstDataRow(table.parentElement as HTMLElement)).toEqual([
        "Caja",
        "Instrumento",
        "Descripción",
        "Tipo",
        "Moneda",
        "Monto",
        "Fecha de carga",
        "Fecha de liquidación",
        "Acciones",
      ]);
    }
  });

  it("exposes data-label cells in the saldo a futuro table", async () => {
    fetchSaldoFuturo.mockResolvedValue({
      caja,
      fecha_calculo: "2026-10-21",
      monedas: [
        {
          moneda: "ARS",
          saldo_actual: "1000.00",
          filas: [
            {
              fecha_liquidacion: "2026-11-05",
              vencido: false,
              cheques: 2,
              efecto_neto: "400.00",
              saldo_proyectado: "1400.00",
              detalle: [
                { descripcion: "Cheque A", instrumento: "cheque", tipo: "entrada", monto: "400.00" },
              ],
            },
          ],
        },
        { moneda: "USD", saldo_actual: "0.00", filas: [] },
      ],
    });
    const { container } = render(<SaldoFuturoDesplegable cajaId={1} />);
    fireEvent.click(screen.getByText("Saldo a futuro"));

    await waitFor(() => expect(container.querySelector("td[data-label]")).not.toBeNull());
    const rows = Array.from(container.querySelectorAll("tbody tr")).filter((row) =>
      row.querySelector("td[data-label]"),
    );
    expect(rows.length).toBeGreaterThanOrEqual(2); // fila "Hoy" + fecha proyectada
    for (const row of rows) {
      expect(
        Array.from(row.querySelectorAll("td")).map((c) => c.getAttribute("data-label")),
      ).toEqual(["Fecha", "Detalle", "Efecto", "Saldo proyectado"]);
    }
  });
});

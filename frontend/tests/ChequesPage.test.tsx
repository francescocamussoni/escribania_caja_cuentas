/**
 * T044 — TDD: sección "Cheques" (feature 010, US3).
 *
 * Dos listados (Aptos para liquidar / Próximos a liquidar este mes) con los cheques
 * pendientes de todas las cajas. Liquidar solo para la Secretaria.
 */

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ChequesPage from "../src/pages/ChequesPage";
import type { Movimiento, PaginatedMovimientos } from "../src/services/api";

const fetchCheques = vi.fn();
const liquidarCheque = vi.fn();
const authState = { rol: "secretaria" as "secretaria" | "escribano" };

vi.mock("../src/services/api", () => ({
  fetchCheques: (...args: unknown[]) => fetchCheques(...args),
  liquidarCheque: (...args: unknown[]) => liquidarCheque(...args),
}));

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({
    token: "test-token",
    rol: authState.rol,
    username: "user",
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

function cheque(overrides: Partial<Movimiento> = {}): Movimiento {
  return {
    id: 1,
    descripcion: "Cheque de prueba",
    monto: "500.00",
    tipo: "entrada",
    moneda: "ARS",
    subtotal: null,
    fecha: "2026-10-20T12:00:00-03:00",
    editable: false,
    caja: { id: 7, nombre: "Bambina", slug: "bambina" },
    instrumento: "cheque",
    estado: "pendiente",
    fecha_carga: "2026-10-20T12:00:00-03:00",
    fecha_liquidacion: "2026-10-15",
    fecha_liquidado: null,
    liquidable: true,
    ...overrides,
  };
}

function page(items: Movimiento[], overrides: Partial<PaginatedMovimientos> = {}) {
  return {
    items,
    page: 1,
    page_size: 20,
    total_items: items.length,
    total_pages: items.length ? 1 : 0,
    ...overrides,
  };
}

function setup(aptos: PaginatedMovimientos, proximos: PaginatedMovimientos) {
  fetchCheques.mockImplementation((categoria: string, p: number) => {
    const source = categoria === "aptos" ? aptos : proximos;
    return Promise.resolve({ ...source, page: p });
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ChequesPage />
    </MemoryRouter>,
  );
}

function section(name: RegExp): HTMLElement {
  return screen.getByRole("region", { name });
}

describe("ChequesPage (T044)", () => {
  beforeEach(() => {
    fetchCheques.mockReset();
    liquidarCheque.mockReset();
    authState.rol = "secretaria";
  });

  it("muestra el título y los dos listados con sus cheques", async () => {
    setup(
      page([cheque({ id: 1, descripcion: "Apto uno" })]),
      page([cheque({ id: 2, descripcion: "Proximo uno", fecha_liquidacion: "2999-01-01" })]),
    );

    renderPage();

    expect(screen.getByRole("heading", { level: 1, name: /^cheques$/i })).toBeInTheDocument();
    expect(await screen.findByText("Apto uno")).toBeInTheDocument();
    expect(await screen.findByText("Proximo uno")).toBeInTheDocument();
    expect(fetchCheques).toHaveBeenCalledWith("aptos", 1);
    expect(fetchCheques).toHaveBeenCalledWith("proximos", 1);

    expect(within(section(/aptos para liquidar/i)).getByText("Apto uno")).toBeInTheDocument();
    expect(
      within(section(/próximos a liquidar este mes/i)).getByText("Proximo uno"),
    ).toBeInTheDocument();
  });

  it("cada listado muestra caja, instrumento, descripción, tipo, moneda, monto y fechas", async () => {
    setup(
      page([
        cheque({
          id: 1,
          descripcion: "Echeque proveedor",
          instrumento: "echeque",
          tipo: "salida",
          moneda: "USD",
          monto: "200.00",
          fecha_liquidacion: "2026-10-15",
          caja: { id: 9, nombre: "Ebel", slug: "ebel" },
        }),
      ]),
      page([]),
    );

    renderPage();

    const aptos = section(/aptos para liquidar/i);
    await within(aptos).findByText("Echeque proveedor");
    for (const name of [
      /^caja$/i,
      /^instrumento$/i,
      /^descripción$/i,
      /^tipo$/i,
      /^moneda$/i,
      /^monto$/i,
      /fecha de carga/i,
      /fecha de liquidación/i,
    ]) {
      expect(within(aptos).getByRole("columnheader", { name })).toBeInTheDocument();
    }
    const row = within(aptos).getAllByRole("row")[1];
    const cells = within(row);
    expect(cells.getByText("Ebel")).toBeInTheDocument();
    expect(cells.getByText("Echeque")).toBeInTheDocument();
    expect(cells.getByText(/salida/i)).toBeInTheDocument();
    expect(cells.getByText("USD")).toBeInTheDocument();
    expect(cells.getByText("200.00")).toBeInTheDocument();
    expect(cells.getByText("15/10/2026")).toBeInTheDocument();
    expect(cells.getByText(/20\/10\/2026/)).toBeInTheDocument();
  });

  it("muestra estados vacíos independientes", async () => {
    setup(page([cheque({ descripcion: "Solo apto" })]), page([]));

    renderPage();

    await screen.findByText("Solo apto");
    expect(
      within(section(/próximos a liquidar este mes/i)).getByText(/no hay cheques próximos/i),
    ).toBeInTheDocument();
    expect(
      within(section(/aptos para liquidar/i)).queryByText(/no hay cheques aptos/i),
    ).not.toBeInTheDocument();
  });

  it("muestra un error si falla la carga de un listado sin romper el otro", async () => {
    fetchCheques.mockImplementation((categoria: string) =>
      categoria === "aptos"
        ? Promise.reject(new Error("boom"))
        : Promise.resolve(page([cheque({ id: 2, descripcion: "Proximo ok" })])),
    );

    renderPage();

    expect(
      await within(section(/aptos para liquidar/i)).findByText(
        /no se pudieron cargar los cheques/i,
      ),
    ).toBeInTheDocument();
    expect(await screen.findByText("Proximo ok")).toBeInTheDocument();
    expect(screen.queryByText(/boom/)).not.toBeInTheDocument();
  });

  it("pagina cada listado de forma independiente", async () => {
    fetchCheques.mockImplementation((categoria: string, p: number) => {
      if (categoria === "aptos") {
        return Promise.resolve(
          page([cheque({ id: p, descripcion: `Apto página ${p}` })], {
            page: p,
            total_items: 21,
            total_pages: 2,
          }),
        );
      }
      return Promise.resolve(page([cheque({ id: 100, descripcion: "Proximo fijo" })]));
    });

    renderPage();

    const aptos = section(/aptos para liquidar/i);
    await within(aptos).findByText("Apto página 1");
    fireEvent.click(within(aptos).getByRole("button", { name: /siguiente/i }));

    expect(await within(aptos).findByText("Apto página 2")).toBeInTheDocument();
    expect(fetchCheques).toHaveBeenCalledWith("aptos", 2);
    const proximosCalls = fetchCheques.mock.calls.filter((c) => c[0] === "proximos");
    expect(proximosCalls.every((c) => c[1] === 1)).toBe(true);
    expect(proximosCalls).toHaveLength(1);
  });

  it("la Secretaria puede liquidar y ambos listados se recargan", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    setup(page([cheque({ id: 31, caja: { id: 9, nombre: "Ebel", slug: "ebel" } })]), page([]));
    liquidarCheque.mockResolvedValue(cheque({ estado: "liquidado", liquidable: false }));

    renderPage();
    await screen.findByText("Cheque de prueba");
    const callsBefore = fetchCheques.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: /liquidar/i }));

    await waitFor(() => expect(liquidarCheque).toHaveBeenCalledWith(9, 31));
    await waitFor(() => expect(fetchCheques.mock.calls.length).toBeGreaterThan(callsBefore));
    const after = fetchCheques.mock.calls.slice(callsBefore).map((c) => c[0]);
    expect(after).toEqual(expect.arrayContaining(["aptos", "proximos"]));
    confirmSpy.mockRestore();
  });

  it("si liquidar falla se muestra un mensaje genérico y el cheque permanece", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    setup(page([cheque({ id: 31 })]), page([]));
    liquidarCheque.mockRejectedValue(new Error('{"detail":"interno"}'));

    renderPage();
    await screen.findByText("Cheque de prueba");
    fireEvent.click(screen.getByRole("button", { name: /liquidar/i }));

    expect(await screen.findByText(/no se pudo liquidar el cheque/i)).toBeInTheDocument();
    expect(screen.queryByText(/interno/)).not.toBeInTheDocument();
    expect(screen.getByText("Cheque de prueba")).toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it("solo ofrece Liquidar en cheques liquidables", async () => {
    setup(
      page([
        cheque({ id: 1, descripcion: "Con acción", liquidable: true }),
        cheque({ id: 2, descripcion: "Sin acción", liquidable: false }),
      ]),
      page([]),
    );

    renderPage();
    await screen.findByText("Con acción");

    expect(screen.getAllByRole("button", { name: /liquidar/i })).toHaveLength(1);
  });

  it("el Escribano ve los listados sin acciones", async () => {
    authState.rol = "escribano";
    setup(
      page([cheque({ id: 1, liquidable: false })]),
      page([cheque({ id: 2, descripcion: "Proximo esc", liquidable: false })]),
    );

    renderPage();
    await screen.findByText("Proximo esc");

    expect(screen.queryByRole("button", { name: /liquidar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: /acciones/i })).not.toBeInTheDocument();
  });

  it("usa celdas con data-label para apilar en pantallas chicas", async () => {
    setup(page([cheque()]), page([]));

    renderPage();
    await screen.findByText("Cheque de prueba");

    const labels = Array.from(
      document.querySelectorAll("[data-block='cheques-aptos'] td[data-label]"),
    ).map((td) => td.getAttribute("data-label"));
    expect(labels).toEqual(
      expect.arrayContaining([
        "Caja",
        "Instrumento",
        "Descripción",
        "Tipo",
        "Moneda",
        "Monto",
        "Fecha de carga",
        "Fecha de liquidación",
        "Acciones",
      ]),
    );
  });

  it("en 'Próximos' Liquidar sale en gris hasta que llegue la fecha; en 'Aptos' está habilitado", async () => {
    setup(
      page([cheque({ id: 1, descripcion: "Apto uno", fecha_liquidacion: "2020-01-01" })]),
      page([cheque({ id: 2, descripcion: "Proximo uno", fecha_liquidacion: "2999-01-01" })]),
    );

    renderPage();

    await screen.findByText("Apto uno");
    await screen.findByText("Proximo uno");
    expect(
      within(section(/aptos para liquidar/i)).getByRole("button", { name: /^liquidar$/i }),
    ).toBeEnabled();
    expect(
      within(section(/próximos a liquidar este mes/i)).getByRole("button", { name: /^liquidar$/i }),
    ).toBeDisabled();
  });
});

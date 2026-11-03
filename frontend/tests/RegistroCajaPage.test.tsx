import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { mananaAr } from "../src/utils/fechas";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RegistroCajaPage from "../src/pages/RegistroCajaPage";

const apiGet = vi.fn();
const apiPost = vi.fn();
const fetchChequesPendientes = vi.fn();
const liquidarCheque = vi.fn();
const fetchSaldoFuturo = vi.fn();
const fetchSaldoProyectado = vi.fn();
const updateMovimiento = vi.fn();
const deleteMovimiento = vi.fn();

const EMPTY_PAGE = { items: [], page: 1, page_size: 20, total_items: 0, total_pages: 0 };

vi.mock("../src/services/api", () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
  apiPost: (...args: unknown[]) => apiPost(...args),
  fetchChequesPendientes: (...args: unknown[]) => fetchChequesPendientes(...args),
  liquidarCheque: (...args: unknown[]) => liquidarCheque(...args),
  fetchSaldoFuturo: (...args: unknown[]) => fetchSaldoFuturo(...args),
  fetchSaldoProyectado: (...args: unknown[]) => fetchSaldoProyectado(...args),
  updateMovimiento: (...args: unknown[]) => updateMovimiento(...args),
  deleteMovimiento: (...args: unknown[]) => deleteMovimiento(...args),
  getAuthToken: () => "test-token",
  setAuthToken: vi.fn(),
}));

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({
    token: "test-token",
    rol: "secretaria",
    username: "admin",
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

describe("RegistroCajaPage", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    fetchChequesPendientes.mockReset();
    fetchChequesPendientes.mockResolvedValue(EMPTY_PAGE);
    liquidarCheque.mockReset();
    updateMovimiento.mockReset();
    deleteMovimiento.mockReset();
    fetchSaldoFuturo.mockReset();
    fetchSaldoProyectado.mockReset();
    fetchSaldoProyectado.mockResolvedValue({
      caja: { id: 1, nombre: "Bambina", slug: "bambina" },
      fecha: null,
      monedas: [],
    });
    fetchSaldoFuturo.mockResolvedValue({
      caja: { id: 1, nombre: "Bambina", slug: "bambina" },
      fecha_calculo: "2026-10-21",
      monedas: [
        { moneda: "ARS", saldo_actual: "0.00", filas: [] },
        { moneda: "USD", saldo_actual: "0.00", filas: [] },
      ],
    });
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") {
        return Promise.resolve([
          { id: 1, nombre: "Bambina", slug: "bambina" },
          { id: 2, nombre: "Ebel", slug: "ebel" },
          { id: 3, nombre: "Martin", slug: "martin" },
        ]);
      }
      if (path === "/api/v1/cajas/1/saldo") {
        return Promise.resolve({
          caja: { id: 1, nombre: "Bambina", slug: "bambina" },
          saldo_ars: "0.00",
          saldo_usd: "0.00",
          ultimo_movimiento_at: null,
        });
      }
      if (path.startsWith("/api/v1/cajas/1/movimientos")) {
        return Promise.resolve({
          items: [],
          page: 1,
          page_size: 20,
          total_items: 0,
          total_pages: 0,
        });
      }
      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });
  });

  it("muestra Valor de caja total a la derecha del valor de caja (secretaria)", async () => {
    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: /valor de caja total/i })).toBeInTheDocument();
  });

  it("loads cajas and submits a new entrada movimiento", async () => {
    apiPost.mockResolvedValue({
      movimiento: {
        id: 1,
        descripcion: "Pago cliente",
        monto: "5000.00",
        tipo: "entrada",
        moneda: "ARS",
        subtotal: "5000.00",
        fecha: "2026-08-03T14:30:00-03:00",
        editable: true,
        caja: { id: 1, nombre: "Bambina", slug: "bambina" },
      },
      complementario: null,
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Pago cliente" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "5000.00" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith("/api/v1/cajas/1/movimientos", {
        descripcion: "Pago cliente",
        monto: "5000.00",
        tipo: "entrada",
        moneda: "ARS",
        registrar_complementario: false,
      });
    });
  });

  it("registers the movimiento in additional selected cajas", async () => {
    apiPost.mockResolvedValue({
      movimiento: {
        id: 1,
        descripcion: "Pago cliente",
        monto: "5000.00",
        tipo: "entrada",
        moneda: "ARS",
        subtotal: "5000.00",
        fecha: "2026-08-03T14:30:00-03:00",
        editable: true,
        caja: { id: 1, nombre: "Bambina", slug: "bambina" },
      },
      complementario: null,
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Registrar también en otras cajas")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Registrar también en otras cajas"));
    fireEvent.click(screen.getByRole("checkbox", { name: /ebel/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /martin/i }));

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Pago cliente" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "5000.00" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledTimes(3);
      expect(apiPost).toHaveBeenCalledWith("/api/v1/cajas/1/movimientos", {
        descripcion: "Pago cliente",
        monto: "5000.00",
        tipo: "entrada",
        moneda: "ARS",
        registrar_complementario: false,
      });
      expect(apiPost).toHaveBeenCalledWith("/api/v1/cajas/2/movimientos", {
        descripcion: "Pago cliente",
        monto: "5000.00",
        tipo: "entrada",
        moneda: "ARS",
        registrar_complementario: false,
      });
      expect(apiPost).toHaveBeenCalledWith("/api/v1/cajas/3/movimientos", {
        descripcion: "Pago cliente",
        monto: "5000.00",
        tipo: "entrada",
        moneda: "ARS",
        registrar_complementario: false,
      });
    });

    expect(screen.queryByRole("checkbox", { name: /bambina/i })).not.toBeInTheDocument();
  });

  it("does not list archived cajas in the selector or additional boxes", async () => {
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") {
        return Promise.resolve([
          { id: 1, nombre: "Bambina", slug: "bambina", estado: "activa" },
          { id: 2, nombre: "Ebel", slug: "ebel", estado: "activa" },
        ]);
      }
      if (path === "/api/v1/cajas/1/saldo") {
        return Promise.resolve({
          caja: { id: 1, nombre: "Bambina", slug: "bambina" },
          saldo_ars: "0.00",
          saldo_usd: "0.00",
          ultimo_movimiento_at: null,
        });
      }
      if (path.startsWith("/api/v1/cajas/1/movimientos")) {
        return Promise.resolve({
          items: [],
          page: 1,
          page_size: 20,
          total_items: 0,
          total_pages: 0,
        });
      }
      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Registrar también en otras cajas"));

    expect(screen.queryByText("Caja Archivada")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: /caja archivada/i })).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /ebel/i })).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // T010 — Selector de moneda (TDD: deben fallar hasta T016)
  // -----------------------------------------------------------------------

  it("T010: moneda selector defaults to ARS", async () => {
    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    // Debe existir un selector de moneda con valor por defecto ARS
    const monedaSelect = screen.getByLabelText(/moneda/i);
    expect(monedaSelect).toBeInTheDocument();
    expect((monedaSelect as HTMLSelectElement).value).toBe("ARS");
  });

  it("T010: moneda selector only offers ARS and USD options", async () => {
    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    const monedaSelect = screen.getByLabelText(/moneda/i) as HTMLSelectElement;
    const optionValues = Array.from(monedaSelect.options).map((o) => o.value);

    expect(optionValues).toContain("ARS");
    expect(optionValues).toContain("USD");
    // No debe ofrecer ninguna otra moneda
    expect(optionValues.filter((v) => v !== "ARS" && v !== "USD")).toHaveLength(0);
  });

  it("T010: moneda selector resets to ARS when the selected caja changes", async () => {
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") {
        return Promise.resolve([
          { id: 1, nombre: "Bambina", slug: "bambina" },
          { id: 2, nombre: "Ebel", slug: "ebel" },
        ]);
      }
      if (path === "/api/v1/cajas/1/saldo") {
        return Promise.resolve({
          caja: { id: 1, nombre: "Bambina", slug: "bambina" },
          saldo_ars: "0.00",
          saldo_usd: "0.00",
          ultimo_movimiento_at: null,
        });
      }
      if (path === "/api/v1/cajas/2/saldo") {
        return Promise.resolve({
          caja: { id: 2, nombre: "Ebel", slug: "ebel" },
          saldo_ars: "0.00",
          saldo_usd: "0.00",
          ultimo_movimiento_at: null,
        });
      }
      if (path.startsWith("/api/v1/cajas/")) {
        return Promise.resolve({
          items: [],
          page: 1,
          page_size: 20,
          total_items: 0,
          total_pages: 0,
        });
      }
      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    // Cambiar moneda a USD
    const monedaSelect = screen.getByLabelText(/moneda/i);
    fireEvent.change(monedaSelect, { target: { value: "USD" } });
    expect((monedaSelect as HTMLSelectElement).value).toBe("USD");

    // Cambiar la caja seleccionada → moneda debe resetear a ARS
    fireEvent.change(screen.getByLabelText(/^caja$/i), { target: { value: "2" } });

    await waitFor(() => {
      expect((screen.getByLabelText(/moneda/i) as HTMLSelectElement).value).toBe("ARS");
    });
  });

  it("T010: submit includes moneda in the POST payload", async () => {
    apiPost.mockResolvedValue({
      movimiento: {
        id: 1,
        descripcion: "Pago USD",
        monto: "50.00",
        tipo: "entrada",
        moneda: "USD",
        subtotal: "50.00",
        fecha: "2026-09-07T14:30:00-03:00",
        editable: true,
        caja: { id: 1, nombre: "Bambina", slug: "bambina" },
      },
      complementario: null,
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Pago USD" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "50.00" },
    });
    fireEvent.change(screen.getByLabelText(/moneda/i), {
      target: { value: "USD" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    // USD ya no muestra diálogo — apiPost se llama directamente (feature 009)
    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(
        "/api/v1/cajas/1/movimientos",
        expect.objectContaining({ moneda: "USD" }),
      );
    });
  });

  it("T010: submit without changing moneda sends ARS by default", async () => {
    apiPost.mockResolvedValue({
      movimiento: {
        id: 2,
        descripcion: "Pago ARS",
        monto: "100.00",
        tipo: "entrada",
        moneda: "ARS",
        subtotal: "100.00",
        fecha: "2026-09-07T14:30:00-03:00",
        editable: true,
        caja: { id: 1, nombre: "Bambina", slug: "bambina" },
      },
      complementario: null,
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Pago ARS" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), {
      target: { value: "100.00" },
    });
    // No cambiamos moneda → debe enviarse ARS
    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(
        "/api/v1/cajas/1/movimientos",
        expect.objectContaining({ moneda: "ARS" }),
      );
    });
  });
  // -----------------------------------------------------------------------
  // T024 — feature 010 (US1): bloque de cheques pendientes y alta de cheque
  // -----------------------------------------------------------------------

  const chequePendiente = {
    id: 501,
    descripcion: "Cheque pendiente de prueba",
    monto: "500.00",
    tipo: "entrada" as const,
    moneda: "ARS" as const,
    subtotal: null,
    fecha: "2026-10-20T12:00:00-03:00",
    editable: true,
    caja: { id: 1, nombre: "Bambina", slug: "bambina" },
    instrumento: "cheque" as const,
    estado: "pendiente" as const,
    fecha_carga: "2026-10-20T12:00:00-03:00",
    fecha_liquidacion: "2020-01-01",
    fecha_liquidado: null,
    liquidable: true,
  };

  // El listado de cheques pendientes se ve con el botón "Cheques pendientes" junto a los filtros.
  async function abrirPendientes() {
    fireEvent.click(await screen.findByRole("button", { name: /^cheques pendientes$/i }));
  }

  it("T024: el botón Cheques pendientes junto a los filtros alterna entre historial y pendientes", async () => {
    fetchChequesPendientes.mockResolvedValue({
      ...EMPTY_PAGE,
      items: [chequePendiente],
      total_items: 1,
      total_pages: 1,
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    const boton = await screen.findByRole("button", { name: /^cheques pendientes$/i });
    // Vive dentro del bloque de filtros y por defecto está apagado: se ve el historial.
    expect(document.querySelector('[data-block="filtros"]')).toContainElement(boton);
    expect(boton).toHaveAttribute("aria-pressed", "false");
    expect(document.querySelector('[data-block="historial"]')).not.toBeNull();
    expect(document.querySelector('[data-block="cheques-pendientes"]')).toBeNull();
    expect(fetchChequesPendientes).not.toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: /cheques pendientes/i })).not.toBeInTheDocument();

    fireEvent.click(boton);

    expect(await screen.findByText("Cheque pendiente de prueba")).toBeInTheDocument();
    expect(boton).toHaveAttribute("aria-pressed", "true");
    expect(fetchChequesPendientes).toHaveBeenCalledWith(1, 1, {});
    expect(document.querySelector('[data-block="historial"]')).toBeNull();
    expect(document.querySelector('[data-block="paginacion"]')).toBeNull();

    fireEvent.click(boton);

    expect(boton).toHaveAttribute("aria-pressed", "false");
    expect(document.querySelector('[data-block="historial"]')).not.toBeNull();
    expect(document.querySelector('[data-block="cheques-pendientes"]')).toBeNull();
  });

  it("Registro pide el listado con los cheques pendientes incluidos y permite liquidar desde la lista", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    liquidarCheque.mockResolvedValue({ ...chequePendiente, estado: "liquidado" });
    const base = apiGet.getMockImplementation();
    apiGet.mockImplementation((path: string) => {
      if (path.startsWith("/api/v1/cajas/1/movimientos")) {
        return Promise.resolve({
          ...EMPTY_PAGE,
          items: [chequePendiente],
          total_items: 1,
          total_pages: 1,
        });
      }
      return base ? base(path) : Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    const fila = (await screen.findByText("Cheque pendiente de prueba")).closest("tr") as HTMLElement;
    expect(
      apiGet.mock.calls.some(
        (c) =>
          String(c[0]).startsWith("/api/v1/cajas/1/movimientos") &&
          String(c[0]).includes("incluir_pendientes=true"),
      ),
    ).toBe(true);
    expect(within(fila).getByText("Pendiente")).toBeInTheDocument();

    fireEvent.click(within(fila).getByRole("button", { name: /^liquidar$/i }));

    await waitFor(() => expect(liquidarCheque).toHaveBeenCalledWith(1, 501));
    confirmSpy.mockRestore();
  });

  it("T024: los filtros de moneda y fechas también filtran los cheques pendientes", async () => {
    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );
    await abrirPendientes();
    await waitFor(() => expect(fetchChequesPendientes).toHaveBeenCalledWith(1, 1, {}));

    fireEvent.change(screen.getByLabelText("Filtrar por divisa"), { target: { value: "USD" } });
    await waitFor(() =>
      expect(fetchChequesPendientes).toHaveBeenLastCalledWith(1, 1, { moneda: "USD" }),
    );

    fireEvent.change(screen.getByLabelText("Desde"), { target: { value: "2026-10-01" } });
    await waitFor(() =>
      expect(fetchChequesPendientes).toHaveBeenLastCalledWith(1, 1, {
        moneda: "USD",
        fecha_desde: "2026-10-01",
      }),
    );
  });

  it("T024: el cheque pendiente NO suma al Valor de caja mostrado", async () => {
    fetchChequesPendientes.mockResolvedValue({
      ...EMPTY_PAGE,
      items: [chequePendiente],
      total_items: 1,
      total_pages: 1,
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await abrirPendientes();
    await screen.findByText("Cheque pendiente de prueba");
    // El saldo viene del servidor (0.00): el frontend no calcula nada con los pendientes.
    expect(screen.getAllByText(/\$ 0\.00/).length).toBeGreaterThanOrEqual(2);
  });

  it("T024: crear un cheque envía instrumento y fecha de liquidación y refresca el bloque", async () => {
    apiPost.mockResolvedValue({ movimiento: chequePendiente, complementario: null });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });
    await abrirPendientes();
    await waitFor(() => expect(fetchChequesPendientes).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByLabelText(/descripción/i), {
      target: { value: "Cheque cliente" },
    });
    fireEvent.change(screen.getByLabelText(/monto/i), { target: { value: "500.00" } });
    fireEvent.change(screen.getByLabelText(/instrumento/i), { target: { value: "cheque" } });
    fireEvent.change(screen.getByLabelText(/fecha de liquidación/i), {
      target: { value: "2999-01-01" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^entrada$/i }));

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith("/api/v1/cajas/1/movimientos", {
        descripcion: "Cheque cliente",
        monto: "500.00",
        tipo: "entrada",
        moneda: "ARS",
        registrar_complementario: false,
        instrumento: "cheque",
        fecha_liquidacion: "2999-01-01",
      });
    });
    await waitFor(() => expect(fetchChequesPendientes.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it("T024: un cheque con cajas adicionales se registra como cheque pendiente en cada caja", async () => {
    apiPost.mockResolvedValue({ movimiento: chequePendiente, complementario: null });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Registrar también en otras cajas")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Registrar también en otras cajas"));
    fireEvent.click(screen.getByRole("checkbox", { name: /ebel/i }));

    fireEvent.change(screen.getByLabelText(/descripción/i), { target: { value: "Cheque" } });
    fireEvent.change(screen.getByLabelText(/monto/i), { target: { value: "10.00" } });
    fireEvent.change(screen.getByLabelText(/instrumento/i), { target: { value: "echeque" } });
    fireEvent.change(screen.getByLabelText(/fecha de liquidación/i), {
      target: { value: "2999-01-01" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^salida$/i }));

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledTimes(2);
    });
    const payloads = apiPost.mock.calls.map((c) => c[1]);
    for (const payload of payloads) {
      expect(payload).toMatchObject({
        tipo: "salida",
        instrumento: "echeque",
        fecha_liquidacion: "2999-01-01",
      });
    }
    expect(apiPost.mock.calls.map((c) => c[0]).sort()).toEqual([
      "/api/v1/cajas/1/movimientos",
      "/api/v1/cajas/2/movimientos",
    ]);
  });
  // -----------------------------------------------------------------------
  // T038 — feature 010 (US2): liquidar un cheque desde Registro
  // -----------------------------------------------------------------------

  it("T038: liquidar refresca Valor de caja, historial y bloque de pendientes", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    fetchChequesPendientes.mockResolvedValue({
      ...EMPTY_PAGE,
      items: [chequePendiente],
      total_items: 1,
      total_pages: 1,
    });
    liquidarCheque.mockResolvedValue({
      ...chequePendiente,
      subtotal: "500.00",
      estado: "liquidado",
      liquidable: false,
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );
    await abrirPendientes();
    await screen.findByText("Cheque pendiente de prueba");
    const saldoCalls = () =>
      apiGet.mock.calls.filter((c) => c[0] === "/api/v1/cajas/1/saldo").length;
    const historialCalls = () =>
      apiGet.mock.calls.filter((c) => String(c[0]).startsWith("/api/v1/cajas/1/movimientos")).length;
    const saldoBefore = saldoCalls();
    const historialBefore = historialCalls();
    const pendientesBefore = fetchChequesPendientes.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: /liquidar/i }));

    await waitFor(() => expect(liquidarCheque).toHaveBeenCalledWith(1, 501));
    await waitFor(() => expect(saldoCalls()).toBeGreaterThan(saldoBefore));
    expect(historialCalls()).toBeGreaterThan(historialBefore);
    await waitFor(() =>
      expect(fetchChequesPendientes.mock.calls.length).toBeGreaterThan(pendientesBefore),
    );
    confirmSpy.mockRestore();
  });

  it("T038: si liquidar falla muestra un error genérico y el cheque sigue pendiente", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    fetchChequesPendientes.mockResolvedValue({
      ...EMPTY_PAGE,
      items: [chequePendiente],
      total_items: 1,
      total_pages: 1,
    });
    liquidarCheque.mockRejectedValue(new Error('{"detail":"stack interno"}'));

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );
    await abrirPendientes();
    await screen.findByText("Cheque pendiente de prueba");

    fireEvent.click(screen.getByRole("button", { name: /liquidar/i }));

    expect(await screen.findByText(/no se pudo liquidar el cheque/i)).toBeInTheDocument();
    expect(screen.queryByText(/stack interno/)).not.toBeInTheDocument();
    expect(screen.getByText("Cheque pendiente de prueba")).toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it("T038: sin confirmación no se liquida", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    fetchChequesPendientes.mockResolvedValue({
      ...EMPTY_PAGE,
      items: [chequePendiente],
      total_items: 1,
      total_pages: 1,
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );
    await abrirPendientes();
    await screen.findByText("Cheque pendiente de prueba");

    fireEvent.click(screen.getByRole("button", { name: /liquidar/i }));

    expect(liquidarCheque).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });
  // -----------------------------------------------------------------------
  // T056 — feature 010 (US4): Saldo a futuro dentro de "Valor de caja"
  // -----------------------------------------------------------------------

  it("T056: el desplegable Saldo a futuro está dentro de Valor de caja y colapsado", async () => {
    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await screen.findByText("Saldo a futuro");
    const panel = document.querySelector('[data-block="saldo"]');
    expect(panel).not.toBeNull();
    expect(within(panel as HTMLElement).getByText("Saldo a futuro")).toBeInTheDocument();
    expect(within(panel as HTMLElement).getByText("Valor de caja")).toBeInTheDocument();
    expect(screen.getByText("Saldo a futuro").closest("details")).not.toHaveAttribute("open");
    expect(fetchSaldoFuturo).not.toHaveBeenCalled();
  });

  it("T056: el banner ARS/USD de Valor de caja no cambia", async () => {
    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );

    await screen.findByText("Saldo a futuro");
    const valores = document.querySelectorAll('[data-block="saldo"] .saldo-dual .saldo-valor');
    expect(valores).toHaveLength(2);
    expect(valores[0].textContent).toContain("ARS");
    expect(valores[1].textContent).toContain("USD");
  });

  it("T056: al expandir pide el saldo a futuro de la caja y se refresca tras liquidar", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    fetchChequesPendientes.mockResolvedValue({
      ...EMPTY_PAGE,
      items: [chequePendiente],
      total_items: 1,
      total_pages: 1,
    });
    liquidarCheque.mockResolvedValue({ ...chequePendiente, estado: "liquidado", liquidable: false });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );
    await abrirPendientes();
    await screen.findByText("Cheque pendiente de prueba");
    fireEvent.click(screen.getByText("Saldo a futuro"));
    await waitFor(() => expect(fetchSaldoFuturo).toHaveBeenCalledWith(1));
    const before = fetchSaldoFuturo.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: /liquidar/i }));

    await waitFor(() => expect(fetchSaldoFuturo.mock.calls.length).toBeGreaterThan(before));
    confirmSpy.mockRestore();
  });
  // -----------------------------------------------------------------------
  // T067 — feature 010 (US5): editar y eliminar cheques
  // -----------------------------------------------------------------------

  const chequeEditable = { ...chequePendiente, fecha_liquidacion: "2999-06-01" };

  async function renderWithPendingCheque(cheque = chequeEditable) {
    fetchChequesPendientes.mockResolvedValue({
      ...EMPTY_PAGE,
      items: [cheque],
      total_items: 1,
      total_pages: 1,
    });
    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );
    await abrirPendientes();
    await screen.findByText(cheque.descripcion);
  }

  it("T067: Editar un cheque pendiente abre el panel con Cheque/Echeque (nunca '-') y fecha de liquidación", async () => {
    await renderWithPendingCheque();

    fireEvent.click(screen.getByRole("button", { name: /^editar$/i }));

    const panel = document.querySelector('[data-block="edicion"]') as HTMLElement;
    expect(panel).not.toBeNull();
    const instrumento = within(panel).getByLabelText(/instrumento/i) as HTMLSelectElement;
    expect(Array.from(instrumento.options).map((o) => o.value)).toEqual(["cheque", "echeque"]);
    expect(Array.from(instrumento.options).map((o) => o.text)).not.toContain("-");
    expect(instrumento.value).toBe("cheque");
    const fecha = within(panel).getByLabelText(/fecha de liquidación/i) as HTMLInputElement;
    expect(fecha.value).toBe("2999-06-01");
    expect(fecha.min).toBe(mananaAr());
    expect(within(panel).getByLabelText(/descripción/i)).toHaveValue(chequeEditable.descripcion);
    expect(within(panel).getByLabelText(/monto/i)).toHaveValue("500.00");
    expect(within(panel).getByLabelText(/tipo/i)).toHaveValue("entrada");
  });

  it("T067: guardar un cheque pendiente envía los campos editados y refresca bloque, saldo y desplegable sin cambiar el Valor de caja", async () => {
    updateMovimiento.mockResolvedValue({ ...chequeEditable, monto: "700.00", instrumento: "echeque" });
    await renderWithPendingCheque();
    fireEvent.click(screen.getByText("Saldo a futuro"));
    await waitFor(() => expect(fetchSaldoFuturo).toHaveBeenCalled());
    const pendientesBefore = fetchChequesPendientes.mock.calls.length;
    const futuroBefore = fetchSaldoFuturo.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: /^editar$/i }));
    const panel = document.querySelector('[data-block="edicion"]') as HTMLElement;
    fireEvent.change(within(panel).getByLabelText(/monto/i), { target: { value: "700.00" } });
    fireEvent.change(within(panel).getByLabelText(/instrumento/i), { target: { value: "echeque" } });
    fireEvent.change(within(panel).getByLabelText(/fecha de liquidación/i), {
      target: { value: "2999-07-01" },
    });
    fireEvent.click(within(panel).getByRole("button", { name: /guardar/i }));

    await waitFor(() =>
      expect(updateMovimiento).toHaveBeenCalledWith(1, 501, {
        descripcion: chequeEditable.descripcion,
        monto: "700.00",
        tipo: "entrada",
        instrumento: "echeque",
        fecha_liquidacion: "2999-07-01",
      }),
    );
    await waitFor(() =>
      expect(fetchChequesPendientes.mock.calls.length).toBeGreaterThan(pendientesBefore),
    );
    await waitFor(() => expect(fetchSaldoFuturo.mock.calls.length).toBeGreaterThan(futuroBefore));
    expect(document.querySelector('[data-block="edicion"]')).toBeNull();
    const valores = document.querySelectorAll('[data-block="saldo"] .saldo-dual .saldo-valor');
    expect(valores[0].textContent).toContain("0.00");
    expect(valores[1].textContent).toContain("0.00");
  });

  it("T067: no reenvía fecha_liquidacion si no cambió (cheque con fecha ya vencida)", async () => {
    updateMovimiento.mockResolvedValue(chequePendiente);
    await renderWithPendingCheque({ ...chequePendiente, fecha_liquidacion: "2020-01-01" });

    fireEvent.click(screen.getByRole("button", { name: /^editar$/i }));
    const panel = document.querySelector('[data-block="edicion"]') as HTMLElement;
    fireEvent.change(within(panel).getByLabelText(/monto/i), { target: { value: "42.00" } });
    fireEvent.click(within(panel).getByRole("button", { name: /guardar/i }));

    await waitFor(() => expect(updateMovimiento).toHaveBeenCalledTimes(1));
    const payload = updateMovimiento.mock.calls[0][2];
    expect(payload).not.toHaveProperty("fecha_liquidacion");
    expect(payload).toMatchObject({ monto: "42.00", instrumento: "cheque" });
  });

  it("T067: no envía una fecha de liquidación cambiada a hoy o anterior", async () => {
    await renderWithPendingCheque();

    fireEvent.click(screen.getByRole("button", { name: /^editar$/i }));
    const panel = document.querySelector('[data-block="edicion"]') as HTMLElement;
    const fecha = within(panel).getByLabelText(/fecha de liquidación/i) as HTMLInputElement;
    fireEvent.change(fecha, { target: { value: "2020-01-01" } });
    fireEvent.click(within(panel).getByRole("button", { name: /guardar/i }));

    // The `min` attribute (tomorrow) makes the browser block the submit; the server is the
    // authority anyway (422 for a date that is not after today).
    expect(fecha.validity.rangeUnderflow).toBe(true);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(updateMovimiento).not.toHaveBeenCalled();
  });

  it("T067: si guardar falla muestra un error genérico", async () => {
    updateMovimiento.mockRejectedValue(new Error('{"detail":"interno"}'));
    await renderWithPendingCheque();

    fireEvent.click(screen.getByRole("button", { name: /^editar$/i }));
    const panel = document.querySelector('[data-block="edicion"]') as HTMLElement;
    fireEvent.click(within(panel).getByRole("button", { name: /guardar/i }));

    expect(await screen.findByText(/no se pudo actualizar el movimiento/i)).toBeInTheDocument();
    expect(screen.queryByText(/interno/)).not.toBeInTheDocument();
  });

  it("T067: el panel de un cheque liquidado permite Cheque/Echeque pero no la fecha de liquidación", async () => {
    const liquidado = {
      ...chequePendiente,
      id: 777,
      descripcion: "Cheque ya liquidado",
      subtotal: "500.00",
      estado: "liquidado" as const,
      liquidable: false,
      fecha_liquidado: "2026-10-21T10:00:00-03:00",
    };
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") {
        return Promise.resolve([{ id: 1, nombre: "Bambina", slug: "bambina" }]);
      }
      if (path === "/api/v1/cajas/1/saldo") {
        return Promise.resolve({
          caja: { id: 1, nombre: "Bambina", slug: "bambina" },
          saldo_ars: "500.00",
          saldo_usd: "0.00",
          ultimo_movimiento_at: null,
        });
      }
      if (path.startsWith("/api/v1/cajas/1/movimientos")) {
        return Promise.resolve({
          items: [liquidado],
          page: 1,
          page_size: 20,
          total_items: 1,
          total_pages: 1,
        });
      }
      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );
    const row = (await screen.findByText("Cheque ya liquidado")).closest("tr") as HTMLElement;
    fireEvent.click(within(row).getByRole("button", { name: /^editar$/i }));

    const panel = document.querySelector('[data-block="edicion"]') as HTMLElement;
    expect(within(panel).getByLabelText(/instrumento/i)).toBeInTheDocument();
    expect(within(panel).queryByLabelText(/fecha de liquidación/i)).not.toBeInTheDocument();
  });

  it("T067: el panel de un movimiento común no muestra campos de instrumento", async () => {
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") {
        return Promise.resolve([{ id: 1, nombre: "Bambina", slug: "bambina" }]);
      }
      if (path === "/api/v1/cajas/1/saldo") {
        return Promise.resolve({
          caja: { id: 1, nombre: "Bambina", slug: "bambina" },
          saldo_ars: "10.00",
          saldo_usd: "0.00",
          ultimo_movimiento_at: null,
        });
      }
      if (path.startsWith("/api/v1/cajas/1/movimientos")) {
        return Promise.resolve({
          items: [
            {
              id: 900,
              descripcion: "Movimiento común",
              monto: "10.00",
              tipo: "entrada",
              moneda: "ARS",
              subtotal: "10.00",
              fecha: "2026-10-20T12:00:00-03:00",
              editable: true,
              caja: { id: 1, nombre: "Bambina", slug: "bambina" },
              instrumento: "ninguno",
              estado: null,
              fecha_carga: "2026-10-20T12:00:00-03:00",
              fecha_liquidacion: null,
              fecha_liquidado: null,
              liquidable: false,
            },
          ],
          page: 1,
          page_size: 20,
          total_items: 1,
          total_pages: 1,
        });
      }
      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });
    updateMovimiento.mockResolvedValue({});

    render(
      <MemoryRouter>
        <RegistroCajaPage />
      </MemoryRouter>,
    );
    const row = (await screen.findByText("Movimiento común")).closest("tr") as HTMLElement;
    fireEvent.click(within(row).getByRole("button", { name: /^editar$/i }));

    const panel = document.querySelector('[data-block="edicion"]') as HTMLElement;
    expect(within(panel).queryByLabelText(/instrumento/i)).not.toBeInTheDocument();
    expect(within(panel).queryByLabelText(/fecha de liquidación/i)).not.toBeInTheDocument();

    fireEvent.click(within(panel).getByRole("button", { name: /guardar/i }));
    await waitFor(() => expect(updateMovimiento).toHaveBeenCalledTimes(1));
    expect(updateMovimiento.mock.calls[0][2]).toEqual({
      descripcion: "Movimiento común",
      monto: "10.00",
      tipo: "entrada",
    });
  });

  it("T067: eliminar un cheque pendiente pide confirmación, lo elimina y refresca todo", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    deleteMovimiento.mockResolvedValue(undefined);
    await renderWithPendingCheque();
    fireEvent.click(screen.getByText("Saldo a futuro"));
    await waitFor(() => expect(fetchSaldoFuturo).toHaveBeenCalled());
    const pendientesBefore = fetchChequesPendientes.mock.calls.length;
    const futuroBefore = fetchSaldoFuturo.mock.calls.length;

    const bloque = document.querySelector('[data-block="cheques-pendientes"]') as HTMLElement;
    fireEvent.click(within(bloque).getByRole("button", { name: /^eliminar$/i }));

    await waitFor(() => expect(deleteMovimiento).toHaveBeenCalledWith(1, 501));
    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() =>
      expect(fetchChequesPendientes.mock.calls.length).toBeGreaterThan(pendientesBefore),
    );
    await waitFor(() => expect(fetchSaldoFuturo.mock.calls.length).toBeGreaterThan(futuroBefore));
    confirmSpy.mockRestore();
  });
});


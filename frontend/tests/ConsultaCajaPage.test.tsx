import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ConsultaCajaPage from "../src/pages/ConsultaCajaPage";

const CAJAS = [
  { id: 1, nombre: "Bambina", slug: "bambina" },
  { id: 2, nombre: "Martin", slug: "martin" },
  { id: 3, nombre: "Gabriel", slug: "gabriel" },
] as const;

function saldoFor(
  caja: (typeof CAJAS)[number],
  saldoActual: string,
) {
  return {
    caja,
    saldo_actual: saldoActual,
    ultimo_movimiento_at: "2026-08-03T14:30:00-03:00",
  };
}

function movimientosFor(
  caja: (typeof CAJAS)[number],
  descripcion: string,
  page: number,
  totalPages: number,
) {
  return {
    items: [
      {
        id: caja.id * 10 + page,
        descripcion,
        monto: "10.00",
        tipo: "entrada" as const,
        subtotal: "10.00",
        fecha: "2026-08-03T14:30:00-03:00",
        editable: false,
        caja,
      },
    ],
    page,
    page_size: 20,
    total_items: totalPages,
    total_pages: totalPages,
  };
}

const apiGet = vi.fn();

vi.mock("../src/services/api", () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
  apiPost: vi.fn(),
  getAuthToken: () => "test-token",
  setAuthToken: vi.fn(),
}));

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({
    token: "test-token",
    rol: "escribano",
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

describe("ConsultaCajaPage", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") {
        return Promise.resolve([...CAJAS]);
      }
      if (path === "/api/v1/cajas/1/saldo") {
        return Promise.resolve(saldoFor(CAJAS[0], "250.00"));
      }
      if (path === "/api/v1/cajas/2/saldo") {
        return Promise.resolve(saldoFor(CAJAS[1], "80.00"));
      }
      if (path === "/api/v1/cajas/3/saldo") {
        return Promise.resolve(saldoFor(CAJAS[2], "15.00"));
      }
      if (path === "/api/v1/cajas/1/movimientos?page=1") {
        return Promise.resolve(
          movimientosFor(CAJAS[0], "Movimiento de prueba consulta", 1, 1),
        );
      }
      if (path === "/api/v1/cajas/2/movimientos?page=1") {
        return Promise.resolve(movimientosFor(CAJAS[1], "Movimiento Martin p1", 1, 2));
      }
      if (path === "/api/v1/cajas/2/movimientos?page=2") {
        return Promise.resolve(movimientosFor(CAJAS[1], "Movimiento Martin p2", 2, 2));
      }
      if (path === "/api/v1/cajas/3/movimientos?page=1") {
        return Promise.resolve(movimientosFor(CAJAS[2], "Movimiento Gabriel", 1, 1));
      }
      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });
  });

  it("renders read-only consulta and loads data on Consulta click", async () => {
    render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: /entrada/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /salida/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /consulta/i })).toBeInTheDocument();
    expect(
      screen.getByText("Ver en conjunto con otras cajas"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /consulta/i }));

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/1/saldo");
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/1/movimientos?page=1");
    });

    const dataPaths = apiGet.mock.calls
      .map((call) => call[0] as string)
      .filter((path) => path !== "/api/v1/cajas");
    expect(dataPaths).toEqual([
      "/api/v1/cajas/1/saldo",
      "/api/v1/cajas/1/movimientos?page=1",
    ]);

    expect(screen.getByText(/valor de caja/i)).toBeInTheDocument();
    expect(screen.getByText("$ 250.00")).toBeInTheDocument();
    expect(
      screen.getByText("Movimiento de prueba consulta"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /martin/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /valor en conjunto/i })).not.toBeInTheDocument();
  });

  it("keeps single-caja layout when additional checkboxes stay unchecked", async () => {
    render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Ver en conjunto con otras cajas")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Ver en conjunto con otras cajas"));
    expect(screen.getByRole("checkbox", { name: /martin/i })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: /gabriel/i })).not.toBeChecked();
    expect(
      screen.queryByRole("checkbox", { name: /bambina/i }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /consulta/i }));

    await waitFor(() => {
      expect(screen.getByText("$ 250.00")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: /valor de caja/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /valor en conjunto/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /^martin$/i })).not.toBeInTheDocument();
    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/cajas/2/saldo");
    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/cajas/3/saldo");
  });

  async function renderConsulta() {
    render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Ver en conjunto con otras cajas")).toBeInTheDocument();
    });
  }

  async function markAdicionalesAndConsult() {
    fireEvent.click(screen.getByText("Ver en conjunto con otras cajas"));
    fireEvent.click(screen.getByRole("checkbox", { name: /gabriel/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /martin/i }));
    fireEvent.click(screen.getByRole("button", { name: /consulta/i }));
  }

  it("loads all saldos in parallel, shows closed solapas in principal then catalog order, and fetches historial only on expand", async () => {
    await renderConsulta();
    await markAdicionalesAndConsult();

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/1/saldo");
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/2/saldo");
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/3/saldo");
    });

    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/cajas/1/movimientos?page=1");
    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/cajas/2/movimientos?page=1");
    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/cajas/3/movimientos?page=1");
    expect(screen.queryByRole("heading", { name: /valor de caja/i })).not.toBeInTheDocument();

    expect(screen.getByRole("heading", { name: /valor en conjunto/i })).toBeInTheDocument();
    expect(screen.getByText("$ 345.00")).toBeInTheDocument();

    const solapas = document.querySelectorAll(".caja-consulta-solapa");
    expect(solapas).toHaveLength(3);
    expect(solapas[0]).toHaveTextContent("Bambina");
    expect(solapas[0]).toHaveTextContent("$ 250.00");
    expect(solapas[1]).toHaveTextContent("Martin");
    expect(solapas[1]).toHaveTextContent("$ 80.00");
    expect(solapas[2]).toHaveTextContent("Gabriel");
    expect(solapas[2]).toHaveTextContent("$ 15.00");
    solapas.forEach((solapa) => {
      expect(solapa).not.toHaveAttribute("open");
    });

    fireEvent.click(solapas[1].querySelector("summary") as HTMLElement);

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/2/movimientos?page=1");
    });
    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/cajas/1/movimientos?page=1");
    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/cajas/3/movimientos?page=1");
    expect(screen.getByText("Movimiento Martin p1")).toBeInTheDocument();
    expect(screen.queryByText("Movimiento de prueba consulta")).not.toBeInTheDocument();
    expect(screen.queryByText("Movimiento Gabriel")).not.toBeInTheDocument();
  });

  it("keeps pagination isolated per solapa", async () => {
    await renderConsulta();
    await markAdicionalesAndConsult();

    await waitFor(() => {
      expect(document.querySelectorAll(".caja-consulta-solapa")).toHaveLength(3);
    });

    const solapas = document.querySelectorAll(".caja-consulta-solapa");
    fireEvent.click(solapas[1].querySelector("summary") as HTMLElement);

    await waitFor(() => {
      expect(screen.getByText("Movimiento Martin p1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/2/movimientos?page=2");
      expect(screen.getByText("Movimiento Martin p2")).toBeInTheDocument();
    });
    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/cajas/1/movimientos?page=1");
    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/cajas/3/movimientos?page=1");
    expect(solapas[0]).not.toHaveAttribute("open");
    expect(solapas[2]).not.toHaveAttribute("open");
  });

  it("discards the whole joint consulta when any saldo fails", async () => {
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") {
        return Promise.resolve([...CAJAS]);
      }
      if (path === "/api/v1/cajas/1/saldo") {
        return Promise.resolve(saldoFor(CAJAS[0], "250.00"));
      }
      if (path === "/api/v1/cajas/2/saldo") {
        return Promise.reject(new Error("404"));
      }
      if (path === "/api/v1/cajas/3/saldo") {
        return Promise.resolve(saldoFor(CAJAS[2], "15.00"));
      }
      if (path === "/api/v1/cajas/1/movimientos?page=1") {
        return Promise.resolve(
          movimientosFor(CAJAS[0], "Movimiento de prueba consulta", 1, 1),
        );
      }
      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    await renderConsulta();
    fireEvent.click(screen.getByRole("button", { name: /consulta/i }));
    await waitFor(() => {
      expect(screen.getByText("$ 250.00")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Ver en conjunto con otras cajas"));
    fireEvent.click(screen.getByRole("checkbox", { name: /martin/i }));
    fireEvent.click(screen.getByRole("button", { name: /consulta/i }));

    await waitFor(() => {
      expect(screen.getByText(/no se pudieron cargar/i)).toBeInTheDocument();
    });
    expect(screen.queryByText("$ 250.00")).not.toBeInTheDocument();
    expect(document.querySelectorAll(".caja-consulta-solapa")).toHaveLength(0);
    expect(screen.queryByRole("heading", { name: /valor de caja/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /valor en conjunto/i })).not.toBeInTheDocument();
  });

  it("moves a marked adicional to principal when the dropdown changes", async () => {
    await renderConsulta();
    fireEvent.click(screen.getByText("Ver en conjunto con otras cajas"));
    fireEvent.click(screen.getByRole("checkbox", { name: /martin/i }));
    expect(screen.getByRole("checkbox", { name: /martin/i })).toBeChecked();

    fireEvent.change(screen.getByLabelText(/^caja$/i), { target: { value: "2" } });

    expect(screen.queryByRole("checkbox", { name: /martin/i })).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /bambina/i })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /bambina/i })).not.toBeChecked();
  });
});

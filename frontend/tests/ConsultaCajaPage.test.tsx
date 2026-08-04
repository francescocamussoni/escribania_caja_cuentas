import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ConsultaCajaPage from "../src/pages/ConsultaCajaPage";

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
        return Promise.resolve([
          { id: 1, nombre: "Bambina", slug: "bambina" },
        ]);
      }
      if (path === "/api/v1/cajas/1/saldo") {
        return Promise.resolve({
          caja: { id: 1, nombre: "Bambina", slug: "bambina" },
          saldo_actual: "250.00",
          ultimo_movimiento_at: "2026-08-03T14:30:00-03:00",
        });
      }
      if (path.startsWith("/api/v1/cajas/1/movimientos")) {
        return Promise.resolve({
          items: [
            {
              id: 1,
              descripcion: "Movimiento de prueba consulta",
              monto: "250.00",
              tipo: "entrada",
              subtotal: "250.00",
              fecha: "2026-08-03T14:30:00-03:00",
              editable: false,
              caja: { id: 1, nombre: "Bambina", slug: "bambina" },
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

    fireEvent.click(screen.getByRole("button", { name: /consulta/i }));

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/1/saldo");
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/1/movimientos?page=1");
    });

    expect(screen.getByText(/valor de caja/i)).toBeInTheDocument();
    expect(screen.getByText("$ 250.00")).toBeInTheDocument();
    expect(
      screen.getByText("Movimiento de prueba consulta"),
    ).toBeInTheDocument();
  });
});

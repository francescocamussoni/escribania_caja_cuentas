import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ConsultaPlazosFijosPage from "../src/pages/ConsultaPlazosFijosPage";

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

const samplePlazoFijo = {
  id: 1,
  monto_ingresado: "25000.00",
  monto_a_vencimiento: "27500.00",
  fecha_vencimiento: "2026-12-31",
  vencido: false,
  created_at: "2026-08-06T12:00:00-03:00",
  caja: { id: 1, nombre: "Bambina", slug: "bambina" },
};

describe("ConsultaPlazosFijosPage", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") {
        return Promise.resolve([{ id: 1, nombre: "Bambina", slug: "bambina" }]);
      }
      if (path === "/api/v1/cajas/1/plazos-fijos/resumen") {
        return Promise.resolve({
          caja: { id: 1, nombre: "Bambina", slug: "bambina" },
          total_monto_ingresado_activos: "25000.00",
          total_monto_a_vencimiento_activos: "27500.00",
        });
      }
      if (path === "/api/v1/cajas/1/plazos-fijos?page=1") {
        return Promise.resolve({
          items: [samplePlazoFijo],
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
        <ConsultaPlazosFijosPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: /registrar/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^editar$/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^eliminar$/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /consulta/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /consulta/i }));

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/1/plazos-fijos/resumen");
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/1/plazos-fijos?page=1");
    });

    expect(screen.getByText(/dinero ingresado/i)).toBeInTheDocument();
    expect(screen.getByText(/cobrar al vencer/i)).toBeInTheDocument();
    expect(screen.getByText("$ 25000.00")).toBeInTheDocument();
    expect(screen.getByText("$ 27500.00")).toBeInTheDocument();
    expect(screen.getByText("25000.00")).toBeInTheDocument();
    expect(screen.getByText("27500.00")).toBeInTheDocument();
  });
});

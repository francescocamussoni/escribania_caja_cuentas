import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RegistroCajaPage from "../src/pages/RegistroCajaPage";

const apiGet = vi.fn();
const apiPost = vi.fn();

vi.mock("../src/services/api", () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
  apiPost: (...args: unknown[]) => apiPost(...args),
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
          saldo_actual: "0.00",
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

  it("loads cajas and submits a new entrada movimiento", async () => {
    apiPost.mockResolvedValue({
      id: 1,
      descripcion: "Pago cliente",
      monto: "5000.00",
      tipo: "entrada",
      subtotal: "5000.00",
      fecha: "2026-08-03T14:30:00-03:00",
      editable: true,
      caja: { id: 1, nombre: "Bambina", slug: "bambina" },
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
      });
    });
  });

  it("registers the movimiento in additional selected cajas", async () => {
    apiPost.mockResolvedValue({
      id: 1,
      descripcion: "Pago cliente",
      monto: "5000.00",
      tipo: "entrada",
      subtotal: "5000.00",
      fecha: "2026-08-03T14:30:00-03:00",
      editable: true,
      caja: { id: 1, nombre: "Bambina", slug: "bambina" },
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
      });
      expect(apiPost).toHaveBeenCalledWith("/api/v1/cajas/2/movimientos", {
        descripcion: "Pago cliente",
        monto: "5000.00",
        tipo: "entrada",
      });
      expect(apiPost).toHaveBeenCalledWith("/api/v1/cajas/3/movimientos", {
        descripcion: "Pago cliente",
        monto: "5000.00",
        tipo: "entrada",
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
          saldo_actual: "0.00",
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
});

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlazosFijosPage from "../src/pages/PlazosFijosPage";

const apiGet = vi.fn();
const apiPost = vi.fn();
const updatePlazoFijo = vi.fn();
const deletePlazoFijo = vi.fn();

vi.mock("../src/services/api", () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
  apiPost: (...args: unknown[]) => apiPost(...args),
  updatePlazoFijo: (...args: unknown[]) => updatePlazoFijo(...args),
  deletePlazoFijo: (...args: unknown[]) => deletePlazoFijo(...args),
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

const cajas = [
  { id: 1, nombre: "Bambina", slug: "bambina" },
  { id: 2, nombre: "Ebel", slug: "ebel" },
];

const samplePlazoFijo = {
  id: 1,
  monto_ingresado: "10000.00",
  monto_a_vencimiento: "11000.00",
  fecha_vencimiento: "2026-12-31",
  vencido: false,
  created_at: "2026-08-06T12:00:00-03:00",
  caja: { id: 1, nombre: "Bambina", slug: "bambina" },
};

const resumenActivo = {
  caja: { id: 1, nombre: "Bambina", slug: "bambina" },
  total_monto_ingresado_activos: "10000.00",
  total_monto_a_vencimiento_activos: "11000.00",
};

function mockDefaultApiGet(
  listOverrides: Partial<{
    items: typeof samplePlazoFijo[];
    page: number;
    total_pages: number;
    total_items: number;
  }> = {},
) {
  apiGet.mockImplementation((path: string) => {
    if (path === "/api/v1/cajas") {
      return Promise.resolve(cajas);
    }
    if (path === "/api/v1/cajas/1/plazos-fijos/resumen") {
      return Promise.resolve(resumenActivo);
    }
    if (path === "/api/v1/cajas/1/plazos-fijos?page=1") {
      return Promise.resolve({
        items: listOverrides.items ?? [samplePlazoFijo],
        page: listOverrides.page ?? 1,
        page_size: 20,
        total_items: listOverrides.total_items ?? 1,
        total_pages: listOverrides.total_pages ?? 1,
      });
    }
    if (path === "/api/v1/cajas/1/plazos-fijos?page=2") {
      return Promise.resolve({
        items: [
          {
            ...samplePlazoFijo,
            id: 2,
            monto_ingresado: "5000.00",
            monto_a_vencimiento: "5500.00",
            fecha_vencimiento: "2027-01-15",
          },
        ],
        page: 2,
        page_size: 20,
        total_items: 21,
        total_pages: 2,
      });
    }
    if (path === "/api/v1/cajas/2/plazos-fijos/resumen") {
      return Promise.resolve({
        caja: cajas[1],
        total_monto_ingresado_activos: "0.00",
        total_monto_a_vencimiento_activos: "0.00",
      });
    }
    if (path === "/api/v1/cajas/2/plazos-fijos?page=1") {
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
}

describe("PlazosFijosPage", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    updatePlazoFijo.mockReset();
    deletePlazoFijo.mockReset();
    mockDefaultApiGet();
  });

  it("loads cajas and submits a new plazo fijo", async () => {
    apiPost.mockResolvedValue({
      ...samplePlazoFijo,
      monto_ingresado: "50000.00",
      monto_a_vencimiento: "52500.00",
      fecha_vencimiento: "2026-09-30",
    });

    render(
      <MemoryRouter>
        <PlazosFijosPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/monto ingresado/i), {
      target: { value: "50000.00" },
    });
    fireEvent.change(screen.getByLabelText(/fecha de vencimiento/i), {
      target: { value: "2026-09-30" },
    });
    fireEvent.change(screen.getByLabelText(/monto a vencimiento/i), {
      target: { value: "52500.00" },
    });
    fireEvent.click(screen.getByRole("button", { name: /registrar/i }));

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith("/api/v1/cajas/1/plazos-fijos", {
        monto_ingresado: "50000.00",
        monto_a_vencimiento: "52500.00",
        fecha_vencimiento: "2026-09-30",
      });
    });
  });

  it("displays resumen panel with active totals", async () => {
    render(
      <MemoryRouter>
        <PlazosFijosPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/1/plazos-fijos/resumen");
    });

    expect(screen.getByText(/dinero ingresado/i)).toBeInTheDocument();
    expect(screen.getByText(/cobrar al vencer/i)).toBeInTheDocument();
    expect(screen.getByText("$ 10000.00")).toBeInTheDocument();
    expect(screen.getByText("$ 11000.00")).toBeInTheDocument();
  });

  it("edits an existing plazo fijo", async () => {
    updatePlazoFijo.mockResolvedValue({
      ...samplePlazoFijo,
      monto_ingresado: "20000.00",
      monto_a_vencimiento: "22000.00",
    });

    render(
      <MemoryRouter>
        <PlazosFijosPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("10000.00")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^editar$/i }));

    const editPanel = screen
      .getByRole("heading", { name: /editar plazo fijo/i })
      .closest("section");
    expect(editPanel).not.toBeNull();

    await waitFor(() => {
      expect(
        within(editPanel as HTMLElement).getByLabelText(/monto ingresado/i),
      ).toHaveValue("10000.00");
    });

    fireEvent.change(
      within(editPanel as HTMLElement).getByLabelText(/monto ingresado/i),
      {
        target: { value: "20000.00" },
      },
    );
    fireEvent.change(
      within(editPanel as HTMLElement).getByLabelText(/monto a vencimiento/i),
      {
        target: { value: "22000.00" },
      },
    );
    fireEvent.click(
      within(editPanel as HTMLElement).getByRole("button", { name: /^guardar$/i }),
    );

    await waitFor(() => {
      expect(updatePlazoFijo).toHaveBeenCalledWith(1, 1, {
        monto_ingresado: "20000.00",
        monto_a_vencimiento: "22000.00",
      });
    });
  });

  it("deletes a plazo fijo after confirmation", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    deletePlazoFijo.mockResolvedValue(undefined);

    render(
      <MemoryRouter>
        <PlazosFijosPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("10000.00")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^eliminar$/i }));

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalled();
      expect(deletePlazoFijo).toHaveBeenCalledWith(1, 1);
    });

    confirmSpy.mockRestore();
  });

  it("reloads data when caja changes", async () => {
    render(
      <MemoryRouter>
        <PlazosFijosPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/caja/i), {
      target: { value: "2" },
    });

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/2/plazos-fijos/resumen");
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/2/plazos-fijos?page=1");
    });
  });

  it("navigates to the next page", async () => {
    mockDefaultApiGet({ total_pages: 2, total_items: 21 });

    render(
      <MemoryRouter>
        <PlazosFijosPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Página 1 de 2")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/1/plazos-fijos?page=2");
      expect(screen.getByText("5000.00")).toBeInTheDocument();
    });
  });
});

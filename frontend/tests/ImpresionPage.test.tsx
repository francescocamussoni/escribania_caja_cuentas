import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ImpresionPage from "../src/pages/ImpresionPage";

const apiGet = vi.fn();
const postInformePdf = vi.fn();

vi.mock("../src/services/api", () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
  postInformePdf: (...args: unknown[]) => postInformePdf(...args),
  getAuthToken: () => "test-token",
  setAuthToken: vi.fn(),
}));

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({
    token: "test-token",
    rol: "secretaria",
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

describe("ImpresionPage", () => {
  beforeEach(() => {
    apiGet.mockReset();
    postInformePdf.mockReset();
    apiGet.mockResolvedValue([{ id: 2, nombre: "Ebel", slug: "ebel" }]);
    postInformePdf.mockResolvedValue({
      blob: new Blob(["%PDF-test"], { type: "application/pdf" }),
      filename: "CAJA-Ebel-2026-03.pdf",
    });
    URL.createObjectURL = vi.fn(() => "blob:test");
    URL.revokeObjectURL = vi.fn();
  });

  it("renders caja form with mes/anio and hasta hoy", async () => {
    render(
      <MemoryRouter>
        <ImpresionPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Ebel")).toBeInTheDocument();
    });

    expect(document.getElementById("impresion-mes")).toBeInTheDocument();
    expect(document.getElementById("impresion-anio")).toBeInTheDocument();
    expect(screen.getByLabelText(/hasta hoy/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /generar informe/i }),
    ).toBeInTheDocument();
  });

  it("shows validation error when periodo sin fecha inicio", async () => {
    render(
      <MemoryRouter>
        <ImpresionPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Ebel")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText(/período específico/i));
    fireEvent.click(screen.getByRole("button", { name: /generar informe de caja/i }));

    expect(
      await screen.findByText(/ingrese la fecha de inicio/i),
    ).toBeInTheDocument();
    expect(postInformePdf).not.toHaveBeenCalled();
  });

  it("submits mes/anio request and downloads blob", async () => {
    render(
      <MemoryRouter>
        <ImpresionPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Ebel")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /generar informe de caja/i }));

    await waitFor(() => {
      expect(postInformePdf).toHaveBeenCalledWith(
        expect.objectContaining({
          tipo: "CAJA",
          caja_id: 2,
          modo: "MES_ANIO",
          mes: expect.any(Number),
          anio: expect.any(Number),
        }),
      );
    });
  });

  it("sends hasta_hoy and omits fecha_fin in periodo mode", async () => {
    render(
      <MemoryRouter>
        <ImpresionPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Ebel")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText(/período específico/i));
    fireEvent.change(screen.getByLabelText(/fecha inicio/i), {
      target: { value: "2026-04-01" },
    });
    fireEvent.click(screen.getByLabelText(/hasta hoy/i));
    fireEvent.click(screen.getByRole("button", { name: /generar informe de caja/i }));

    await waitFor(() => {
      expect(postInformePdf).toHaveBeenCalledWith({
        tipo: "CAJA",
        caja_id: 2,
        modo: "PERIODO",
        hasta_hoy: true,
        fecha_inicio: "2026-04-01",
      });
    });
  });

  it("submits plazo fijo periodo request with expected payload", async () => {
    apiGet.mockResolvedValue([{ id: 5, nombre: "Gabriel", slug: "gabriel" }]);
    postInformePdf.mockResolvedValue({
      blob: new Blob(["%PDF-test"], { type: "application/pdf" }),
      filename: "PLAZO_FIJO-Gabriel-2026-01-01_2026-12-31.pdf",
    });

    render(
      <MemoryRouter>
        <ImpresionPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Gabriel")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText(/^plazo fijo$/i));
    fireEvent.click(screen.getByLabelText(/período específico/i));
    fireEvent.change(screen.getByLabelText(/fecha inicio/i), {
      target: { value: "2026-01-01" },
    });
    fireEvent.change(screen.getByLabelText(/fecha fin/i), {
      target: { value: "2026-12-31" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /generar informe de plazos fijos/i }),
    );

    await waitFor(() => {
      expect(postInformePdf).toHaveBeenCalledWith({
        tipo: "PLAZO_FIJO",
        caja_id: 5,
        modo: "PERIODO",
        hasta_hoy: false,
        fecha_inicio: "2026-01-01",
        fecha_fin: "2026-12-31",
      });
    });
  });

  it("submits plazo fijo mes anio with hasta_hoy", async () => {
    apiGet.mockResolvedValue([{ id: 5, nombre: "Gabriel", slug: "gabriel" }]);

    render(
      <MemoryRouter>
        <ImpresionPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Gabriel")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText(/^plazo fijo$/i));
    fireEvent.click(screen.getByLabelText(/hasta hoy/i));
    fireEvent.click(
      screen.getByRole("button", { name: /generar informe de plazos fijos/i }),
    );

    await waitFor(() => {
      expect(postInformePdf).toHaveBeenCalledWith(
        expect.objectContaining({
          tipo: "PLAZO_FIJO",
          caja_id: 5,
          modo: "MES_ANIO",
          hasta_hoy: true,
          mes: expect.any(Number),
          anio: expect.any(Number),
        }),
      );
    });
  });

  it("does not list archived cajas in the selector", async () => {
    render(
      <MemoryRouter>
        <ImpresionPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Ebel")).toBeInTheDocument();
    });
    expect(screen.queryByText("Caja Archivada")).not.toBeInTheDocument();
  });
});

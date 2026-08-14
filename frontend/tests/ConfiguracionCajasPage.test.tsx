import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ConfiguracionCajasPage from "../src/pages/ConfiguracionCajasPage";

const listCajasConfig = vi.fn();
const createCaja = vi.fn();
const archiveCaja = vi.fn();
const unarchiveCaja = vi.fn();

vi.mock("../src/services/api", () => ({
  listCajasConfig: (...args: unknown[]) => listCajasConfig(...args),
  createCaja: (...args: unknown[]) => createCaja(...args),
  archiveCaja: (...args: unknown[]) => archiveCaja(...args),
  unarchiveCaja: (...args: unknown[]) => unarchiveCaja(...args),
}));

const activa = {
  id: 1,
  nombre: "Bambina",
  slug: "bambina",
  estado: "activa" as const,
};
const archivada = {
  id: 2,
  nombre: "Ebel",
  slug: "ebel",
  estado: "archivada" as const,
};

describe("ConfiguracionCajasPage", () => {
  beforeEach(() => {
    listCajasConfig.mockReset();
    createCaja.mockReset();
    archiveCaja.mockReset();
    unarchiveCaja.mockReset();
    listCajasConfig.mockResolvedValue([activa, archivada]);
  });

  it("lists active and archived cajas", async () => {
    render(
      <MemoryRouter>
        <ConfiguracionCajasPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });
    expect(screen.getByText("Ebel")).toBeInTheDocument();
    expect(screen.getAllByText("activa").length).toBeGreaterThan(0);
    expect(screen.getAllByText("archivada").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /^archivar$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^desarchivar$/i })).toBeInTheDocument();
  });

  it("creates a caja and shows a success message", async () => {
    const created = {
      id: 99,
      nombre: "Nueva Caja",
      slug: "nueva-caja",
      estado: "activa" as const,
    };
    listCajasConfig
      .mockResolvedValueOnce([activa, archivada])
      .mockResolvedValueOnce([activa, archivada, created]);
    createCaja.mockResolvedValue(created);

    render(
      <MemoryRouter>
        <ConfiguracionCajasPage />
      </MemoryRouter>,
    );

    await screen.findByText("Bambina");
    fireEvent.change(screen.getByLabelText(/nombre/i), {
      target: { value: "Nueva Caja" },
    });
    fireEvent.click(screen.getByRole("button", { name: /agregar/i }));

    await waitFor(() => {
      expect(createCaja).toHaveBeenCalledWith("Nueva Caja");
    });
    expect(await screen.findByText(/caja creada/i)).toBeInTheDocument();
    expect(await screen.findByText("Nueva Caja")).toBeInTheDocument();
  });

  it("archives a caja and shows a success message", async () => {
    listCajasConfig
      .mockResolvedValueOnce([activa, archivada])
      .mockResolvedValueOnce([{ ...activa, estado: "archivada" }, archivada]);
    archiveCaja.mockResolvedValue({ ...activa, estado: "archivada" });

    render(
      <MemoryRouter>
        <ConfiguracionCajasPage />
      </MemoryRouter>,
    );

    await screen.findByText("Bambina");
    fireEvent.click(screen.getByRole("button", { name: /^archivar$/i }));

    await waitFor(() => {
      expect(archiveCaja).toHaveBeenCalledWith(1);
    });
    expect(await screen.findByText(/caja archivada/i)).toBeInTheDocument();
  });

  it("unarchives a caja and shows a success message", async () => {
    listCajasConfig
      .mockResolvedValueOnce([activa, archivada])
      .mockResolvedValueOnce([activa, { ...archivada, estado: "activa" }]);
    unarchiveCaja.mockResolvedValue({ ...archivada, estado: "activa" });

    render(
      <MemoryRouter>
        <ConfiguracionCajasPage />
      </MemoryRouter>,
    );

    await screen.findByText("Ebel");
    fireEvent.click(screen.getByRole("button", { name: /^desarchivar$/i }));

    await waitFor(() => {
      expect(unarchiveCaja).toHaveBeenCalledWith(2);
    });
    expect(await screen.findByText(/caja desarchivada/i)).toBeInTheDocument();
  });

  it("shows an error when create fails", async () => {
    createCaja.mockRejectedValue(new Error("duplicado"));

    render(
      <MemoryRouter>
        <ConfiguracionCajasPage />
      </MemoryRouter>,
    );

    await screen.findByText("Bambina");
    fireEvent.change(screen.getByLabelText(/nombre/i), {
      target: { value: "Bambina" },
    });
    fireEvent.click(screen.getByRole("button", { name: /agregar/i }));

    expect(
      await screen.findByText(/no se pudo crear la caja/i),
    ).toBeInTheDocument();
  });
});

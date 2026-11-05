/**
 * T013 — TDD: ventana de selección de caja para endosar (feature 011).
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import EndoseDialog from "../src/components/EndoseDialog";

const fetchCajas = vi.fn();

vi.mock("../src/services/api", () => ({
  fetchCajas: (...args: unknown[]) => fetchCajas(...args),
}));

const CAJAS = [
  { id: 1, nombre: "Bambina", slug: "bambina" },
  { id: 2, nombre: "Ebel", slug: "ebel" },
  { id: 3, nombre: "Oriente", slug: "oriente" },
];

describe("EndoseDialog (T013)", () => {
  beforeEach(() => {
    fetchCajas.mockReset();
    fetchCajas.mockResolvedValue(CAJAS);
  });

  it("es un diálogo modal y lista las cajas como radios sin la caja origen", async () => {
    render(<EndoseDialog cajaOrigenId={1} onConfirm={vi.fn()} onCancel={vi.fn()} />);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(await screen.findByRole("radio", { name: "Ebel" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Oriente" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Bambina" })).not.toBeInTheDocument();
    expect(screen.getByRole("radiogroup")).toBeInTheDocument();
  });

  it("Confirmar está deshabilitado hasta elegir una caja y confirma con su id", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(<EndoseDialog cajaOrigenId={1} onConfirm={onConfirm} onCancel={vi.fn()} />);

    const confirmar = screen.getByRole("button", { name: "Confirmar" });
    expect(confirmar).toBeDisabled();

    fireEvent.click(await screen.findByRole("radio", { name: "Oriente" }));
    expect(confirmar).toBeEnabled();
    fireEvent.click(confirmar);

    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith(3));
  });

  it("Cancelar y Esc cierran sin confirmar", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(<EndoseDialog cajaOrigenId={1} onConfirm={onConfirm} onCancel={onCancel} />);
    await screen.findByRole("radio", { name: "Ebel" });

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onCancel).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(2);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("bloquea una segunda confirmación mientras envía", async () => {
    let resolve: () => void = () => {};
    const onConfirm = vi.fn(
      () =>
        new Promise<void>((r) => {
          resolve = r;
        }),
    );
    render(<EndoseDialog cajaOrigenId={1} onConfirm={onConfirm} onCancel={vi.fn()} />);

    fireEvent.click(await screen.findByRole("radio", { name: "Ebel" }));
    const confirmar = screen.getByRole("button", { name: "Confirmar" });
    fireEvent.click(confirmar);
    fireEvent.click(confirmar);

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(confirmar).toBeDisabled();
    resolve();
  });

  it("ante un error muestra un mensaje genérico y el diálogo sigue usable", async () => {
    const onConfirm = vi.fn().mockRejectedValue(new Error('{"detail":"interno"}'));
    render(<EndoseDialog cajaOrigenId={1} onConfirm={onConfirm} onCancel={vi.fn()} />);

    fireEvent.click(await screen.findByRole("radio", { name: "Ebel" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudo endosar el cheque.",
    );
    expect(screen.queryByText(/interno/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeEnabled();
  });

  it("muestra un error genérico si no se pueden cargar las cajas", async () => {
    fetchCajas.mockRejectedValue(new Error("boom"));
    render(<EndoseDialog cajaOrigenId={1} onConfirm={vi.fn()} onCancel={vi.fn()} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudieron cargar las cajas.",
    );
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeDisabled();
  });
});

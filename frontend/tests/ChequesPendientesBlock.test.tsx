/**
 * T023 — TDD: bloque "Cheques pendientes" (feature 010, US1).
 *
 * Regla (spec FR-015): los cheques pendientes se muestran en un bloque separado arriba
 * del historial, con instrumento, fecha de carga, fecha de liquidación y monto, SIN
 * subtotal. En solo lectura (Consulta) no ofrece acciones.
 */

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ChequesPendientesBlock from "../src/components/ChequesPendientesBlock";
import type { Movimiento, PaginatedMovimientos } from "../src/services/api";

const fetchChequesPendientes = vi.fn();
const fetchCajas = vi.fn();

vi.mock("../src/services/api", () => ({
  fetchChequesPendientes: (...args: unknown[]) => fetchChequesPendientes(...args),
  fetchCajas: (...args: unknown[]) => fetchCajas(...args),
}));

const caja = { id: 1, nombre: "Bambina", slug: "bambina" };

function cheque(overrides: Partial<Movimiento> = {}): Movimiento {
  return {
    id: 1,
    descripcion: "Cheque Banco Nación 0001234",
    monto: "500.00",
    tipo: "entrada",
    moneda: "ARS",
    subtotal: null,
    fecha: "2026-10-20T12:00:00-03:00",
    editable: true,
    caja,
    instrumento: "cheque",
    estado: "pendiente",
    fecha_carga: "2026-10-20T12:00:00-03:00",
    fecha_liquidacion: "2020-01-01",
    fecha_liquidado: null,
    liquidable: true,
    endosable: false,
    endosado_a: null,
    endose_origen: null,
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

describe("ChequesPendientesBlock (T023)", () => {
  beforeEach(() => {
    fetchChequesPendientes.mockReset();
    fetchChequesPendientes.mockResolvedValue(page([]));
  });

  it("carga y lista los cheques pendientes de la caja", async () => {
    fetchChequesPendientes.mockResolvedValue(
      page([
        cheque({ id: 1 }),
        cheque({
          id: 2,
          descripcion: "Echeque proveedor",
          instrumento: "echeque",
          tipo: "salida",
          monto: "200.00",
          moneda: "USD",
          fecha_liquidacion: "2026-12-01",
        }),
      ]),
    );

    render(<ChequesPendientesBlock cajaId={1} />);

    expect(await screen.findByText("Cheque Banco Nación 0001234")).toBeInTheDocument();
    expect(fetchChequesPendientes).toHaveBeenCalledWith(1, 1, {});
    const rows = screen.getAllByRole("row").slice(1); // sin encabezado
    expect(rows).toHaveLength(2);

    const first = within(rows[0]);
    expect(first.getByText("Cheque")).toBeInTheDocument();
    expect(first.getByText("500.00")).toBeInTheDocument();
    expect(first.getByText("ARS")).toBeInTheDocument();
    expect(first.getByText("01/01/2020")).toBeInTheDocument();
    expect(first.getByText(/20\/10\/2026/)).toBeInTheDocument();

    const second = within(rows[1]);
    expect(second.getByText("Echeque")).toBeInTheDocument();
    expect(second.getByText("USD")).toBeInTheDocument();
    expect(second.getByText("01/12/2026")).toBeInTheDocument();
  });

  it("tiene título y columnas esperadas, sin columna Subtotal", async () => {
    fetchChequesPendientes.mockResolvedValue(page([cheque()]));

    render(<ChequesPendientesBlock cajaId={1} />);

    await screen.findByText("Cheque Banco Nación 0001234");
    expect(screen.getByRole("heading", { name: /cheques pendientes/i })).toBeInTheDocument();
    for (const name of [
      /^descripción$/i,
      /^monto$/i,
      /^instrumento$/i,
      /fecha de carga/i,
      /fecha de liquidación/i,
    ]) {
      expect(screen.getByRole("columnheader", { name })).toBeInTheDocument();
    }
    expect(screen.queryByRole("columnheader", { name: /subtotal/i })).not.toBeInTheDocument();
  });

  it("distingue entradas y salidas por signo y color", async () => {
    fetchChequesPendientes.mockResolvedValue(
      page([cheque({ id: 1, tipo: "entrada" }), cheque({ id: 2, tipo: "salida", monto: "70.00" })]),
    );

    render(<ChequesPendientesBlock cajaId={1} />);

    await screen.findAllByText("Cheque");
    const cells = document.querySelectorAll('td[data-label="Monto"]');
    expect(cells[0]).toHaveClass("movimiento-entrada");
    expect(cells[1]).toHaveClass("movimiento-salida");
    expect(cells[1].textContent).toContain("-70.00");
  });

  it("muestra estado vacío cuando no hay cheques pendientes", async () => {
    render(<ChequesPendientesBlock cajaId={1} />);

    expect(await screen.findByText(/no hay cheques pendientes/i)).toBeInTheDocument();
  });

  it("muestra un error si la carga falla", async () => {
    fetchChequesPendientes.mockRejectedValue(new Error("boom"));

    render(<ChequesPendientesBlock cajaId={1} />);

    expect(
      await screen.findByText(/no se pudieron cargar los cheques pendientes/i),
    ).toBeInTheDocument();
  });

  it("en modo solo lectura no ofrece acciones", async () => {
    fetchChequesPendientes.mockResolvedValue(page([cheque()]));

    render(<ChequesPendientesBlock cajaId={1} readOnly />);

    await screen.findByText("Cheque Banco Nación 0001234");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: /acciones/i })).not.toBeInTheDocument();
  });

  it("pagina con su propia paginación", async () => {
    fetchChequesPendientes.mockImplementation((_cajaId: number, p: number) =>
      Promise.resolve(
        page([cheque({ id: p, descripcion: `Cheque página ${p}` })], {
          page: p,
          total_items: 21,
          total_pages: 2,
        }),
      ),
    );

    render(<ChequesPendientesBlock cajaId={1} />);

    await screen.findByText("Cheque página 1");
    expect(screen.getByText(/página 1 de 2/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    expect(await screen.findByText("Cheque página 2")).toBeInTheDocument();
    expect(fetchChequesPendientes).toHaveBeenLastCalledWith(1, 2, {});
  });

  it("recarga al cambiar de caja o cuando cambia refreshKey", async () => {
    const { rerender } = render(<ChequesPendientesBlock cajaId={1} refreshKey={0} />);
    await waitFor(() => expect(fetchChequesPendientes).toHaveBeenCalledTimes(1));

    rerender(<ChequesPendientesBlock cajaId={2} refreshKey={0} />);
    await waitFor(() => expect(fetchChequesPendientes).toHaveBeenCalledTimes(2));
    expect(fetchChequesPendientes).toHaveBeenLastCalledWith(2, 1, {});

    rerender(<ChequesPendientesBlock cajaId={2} refreshKey={1} />);
    await waitFor(() => expect(fetchChequesPendientes).toHaveBeenCalledTimes(3));
  });

  it("no consulta si no hay caja seleccionada", async () => {
    render(<ChequesPendientesBlock cajaId={null} />);

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetchChequesPendientes).not.toHaveBeenCalled();
  });
});

describe("ChequesPendientesBlock — Liquidar (T037)", () => {
  beforeEach(() => {
    fetchChequesPendientes.mockReset();
    fetchChequesPendientes.mockResolvedValue(page([cheque()]));
  });

  it("muestra Liquidar solo en cheques liquidables y solo con onLiquidar", async () => {
    fetchChequesPendientes.mockResolvedValue(
      page([
        cheque({ id: 1, descripcion: "Liquidable", liquidable: true }),
        cheque({ id: 2, descripcion: "No liquidable", liquidable: false }),
      ]),
    );

    const { rerender } = render(
      <ChequesPendientesBlock cajaId={1} onLiquidar={vi.fn().mockResolvedValue(undefined)} />,
    );

    await screen.findByText("Liquidable");
    expect(screen.getAllByRole("button", { name: /liquidar/i })).toHaveLength(1);
    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]).getByRole("button", { name: /liquidar/i })).toBeInTheDocument();
    expect(within(rows[1]).queryByRole("button", { name: /liquidar/i })).not.toBeInTheDocument();

    rerender(<ChequesPendientesBlock cajaId={1} />);
    expect(screen.queryByRole("button", { name: /liquidar/i })).not.toBeInTheDocument();
  });

  it("no ofrece Liquidar en solo lectura aunque reciba onLiquidar", async () => {
    render(
      <ChequesPendientesBlock
        cajaId={1}
        readOnly
        onLiquidar={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    await screen.findByText("Cheque Banco Nación 0001234");
    expect(screen.queryByRole("button", { name: /liquidar/i })).not.toBeInTheDocument();
  });

  it("pide confirmación y, si se cancela, no liquida", async () => {
    const onLiquidar = vi.fn().mockResolvedValue(undefined);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<ChequesPendientesBlock cajaId={1} onLiquidar={onLiquidar} />);
    await screen.findByText("Cheque Banco Nación 0001234");
    fireEvent.click(screen.getByRole("button", { name: /liquidar/i }));

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(onLiquidar).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("al confirmar llama onLiquidar con el cheque y recarga el bloque", async () => {
    const onLiquidar = vi.fn().mockResolvedValue(undefined);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ChequesPendientesBlock cajaId={1} onLiquidar={onLiquidar} />);
    await screen.findByText("Cheque Banco Nación 0001234");
    expect(fetchChequesPendientes).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: /liquidar/i }));

    await waitFor(() => expect(onLiquidar).toHaveBeenCalledTimes(1));
    expect(onLiquidar.mock.calls[0][0]).toMatchObject({ id: 1 });
    await waitFor(() => expect(fetchChequesPendientes).toHaveBeenCalledTimes(2));
    confirmSpy.mockRestore();
  });

  it("si liquidar falla, el cheque sigue en la lista y se muestra un mensaje", async () => {
    const onLiquidar = vi.fn().mockRejectedValue(new Error("boom"));
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ChequesPendientesBlock cajaId={1} onLiquidar={onLiquidar} />);
    await screen.findByText("Cheque Banco Nación 0001234");
    fireEvent.click(screen.getByRole("button", { name: /liquidar/i }));

    expect(await screen.findByText(/no se pudo liquidar el cheque/i)).toBeInTheDocument();
    expect(screen.getByText("Cheque Banco Nación 0001234")).toBeInTheDocument();
    expect(screen.queryByText(/boom/)).not.toBeInTheDocument();
    expect(fetchChequesPendientes).toHaveBeenCalledTimes(1);
    confirmSpy.mockRestore();
  });

  it("evita doble envío mientras se liquida", async () => {
    let resolve!: () => void;
    const onLiquidar = vi.fn().mockImplementation(
      () => new Promise<void>((r) => { resolve = r; }),
    );
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ChequesPendientesBlock cajaId={1} onLiquidar={onLiquidar} />);
    await screen.findByText("Cheque Banco Nación 0001234");
    const button = screen.getByRole("button", { name: /liquidar/i });
    fireEvent.click(button);
    fireEvent.click(button);

    expect(onLiquidar).toHaveBeenCalledTimes(1);
    expect(button).toBeDisabled();
    resolve();
    await waitFor(() => expect(fetchChequesPendientes).toHaveBeenCalledTimes(2));
    confirmSpy.mockRestore();
  });
});

describe("ChequesPendientesBlock — Editar / Eliminar (T067)", () => {
  beforeEach(() => {
    fetchChequesPendientes.mockReset();
    fetchChequesPendientes.mockResolvedValue(page([cheque()]));
  });

  it("muestra Editar y Eliminar solo cuando hay callbacks y no es solo lectura", async () => {
    const { rerender } = render(
      <ChequesPendientesBlock
        cajaId={1}
        onEdit={vi.fn()}
        onDelete={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    await screen.findByText("Cheque Banco Nación 0001234");
    expect(screen.getByRole("button", { name: /^editar$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^eliminar$/i })).toBeInTheDocument();

    rerender(
      <ChequesPendientesBlock
        cajaId={1}
        readOnly
        onEdit={vi.fn()}
        onDelete={vi.fn().mockResolvedValue(undefined)}
      />,
    );
    expect(screen.queryByRole("button", { name: /^editar$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^eliminar$/i })).not.toBeInTheDocument();

    rerender(<ChequesPendientesBlock cajaId={1} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("no ofrece acciones sobre cheques no editables", async () => {
    fetchChequesPendientes.mockResolvedValue(page([cheque({ editable: false, liquidable: false })]));

    render(
      <ChequesPendientesBlock
        cajaId={1}
        onEdit={vi.fn()}
        onDelete={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    await screen.findByText("Cheque Banco Nación 0001234");
    expect(screen.queryByRole("button", { name: /^editar$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^eliminar$/i })).not.toBeInTheDocument();
  });

  it("Editar llama onEdit con el cheque", async () => {
    const onEdit = vi.fn();

    render(<ChequesPendientesBlock cajaId={1} onEdit={onEdit} />);
    await screen.findByText("Cheque Banco Nación 0001234");
    fireEvent.click(screen.getByRole("button", { name: /^editar$/i }));

    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onEdit.mock.calls[0][0]).toMatchObject({ id: 1 });
  });

  it("Eliminar pide confirmación y, si se cancela, no elimina", async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<ChequesPendientesBlock cajaId={1} onDelete={onDelete} />);
    await screen.findByText("Cheque Banco Nación 0001234");
    fireEvent.click(screen.getByRole("button", { name: /^eliminar$/i }));

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(onDelete).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("al confirmar elimina y recarga el bloque", async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ChequesPendientesBlock cajaId={1} onDelete={onDelete} />);
    await screen.findByText("Cheque Banco Nación 0001234");
    fireEvent.click(screen.getByRole("button", { name: /^eliminar$/i }));

    await waitFor(() => expect(onDelete).toHaveBeenCalledTimes(1));
    expect(onDelete.mock.calls[0][0]).toMatchObject({ id: 1 });
    await waitFor(() => expect(fetchChequesPendientes).toHaveBeenCalledTimes(2));
    confirmSpy.mockRestore();
  });

  it("si eliminar falla muestra un mensaje genérico y el cheque permanece", async () => {
    const onDelete = vi.fn().mockRejectedValue(new Error("boom interno"));
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ChequesPendientesBlock cajaId={1} onDelete={onDelete} />);
    await screen.findByText("Cheque Banco Nación 0001234");
    fireEvent.click(screen.getByRole("button", { name: /^eliminar$/i }));

    expect(await screen.findByText(/no se pudo eliminar el cheque/i)).toBeInTheDocument();
    expect(screen.queryByText(/boom interno/)).not.toBeInTheDocument();
    expect(screen.getByText("Cheque Banco Nación 0001234")).toBeInTheDocument();
    expect(fetchChequesPendientes).toHaveBeenCalledTimes(1);
    confirmSpy.mockRestore();
  });
});

describe("ChequesPendientesBlock — filtros y título (Registro)", () => {
  beforeEach(() => {
    fetchChequesPendientes.mockReset();
    fetchChequesPendientes.mockResolvedValue(page([cheque({ id: 1 })]));
  });

  it("aplica los filtros de moneda y fechas al pedir los pendientes", async () => {
    render(
      <ChequesPendientesBlock
        cajaId={1}
        filtros={{ moneda: "USD", fecha_desde: "2026-10-01", fecha_hasta: "2026-10-31" }}
      />,
    );

    await screen.findByText("Cheque Banco Nación 0001234");
    expect(fetchChequesPendientes).toHaveBeenCalledWith(1, 1, {
      moneda: "USD",
      fecha_desde: "2026-10-01",
      fecha_hasta: "2026-10-31",
    });
  });

  it("vuelve a consultar desde la página 1 cuando cambian los filtros", async () => {
    fetchChequesPendientes.mockResolvedValue(page([cheque({ id: 1 })], { total_pages: 3 }));
    const { rerender } = render(<ChequesPendientesBlock cajaId={1} />);
    await screen.findByText("Cheque Banco Nación 0001234");

    rerender(<ChequesPendientesBlock cajaId={1} filtros={{ moneda: "ARS" }} />);

    await waitFor(() =>
      expect(fetchChequesPendientes).toHaveBeenLastCalledWith(1, 1, {
        moneda: "ARS",
        fecha_desde: undefined,
        fecha_hasta: undefined,
      }),
    );
  });

  it("showTitle=false oculta el encabezado y por defecto se muestra", async () => {
    const { rerender } = render(<ChequesPendientesBlock cajaId={1} showTitle={false} />);
    await screen.findByText("Cheque Banco Nación 0001234");
    expect(screen.queryByRole("heading", { name: /cheques pendientes/i })).not.toBeInTheDocument();

    rerender(<ChequesPendientesBlock cajaId={1} />);
    expect(screen.getByRole("heading", { name: /cheques pendientes/i })).toBeInTheDocument();
  });
});


describe("ChequesPendientesBlock — Liquidar según la fecha de liquidación", () => {
  beforeEach(() => {
    fetchChequesPendientes.mockReset();
  });

  it("habilita Liquidar si la fecha ya llegó y lo deja deshabilitado si es futura", async () => {
    fetchChequesPendientes.mockResolvedValue(
      page([
        cheque({ id: 1, descripcion: "Vencido", fecha_liquidacion: "2020-01-01" }),
        cheque({ id: 2, descripcion: "Futuro", fecha_liquidacion: "2999-01-01" }),
      ]),
    );
    const onLiquidar = vi.fn().mockResolvedValue(undefined);

    render(<ChequesPendientesBlock cajaId={1} onLiquidar={onLiquidar} />);

    const filaVencido = (await screen.findByText("Vencido")).closest("tr") as HTMLElement;
    const filaFuturo = screen.getByText("Futuro").closest("tr") as HTMLElement;
    expect(within(filaVencido).getByRole("button", { name: /^liquidar$/i })).toBeEnabled();
    const boton = within(filaFuturo).getByRole("button", { name: /^liquidar$/i });
    expect(boton).toBeDisabled();
    expect(boton).toHaveAttribute("title", "Disponible desde el 01/01/2999");
  });
});

describe("ChequesPendientesBlock — Endose (T014, feature 011)", () => {
  beforeEach(() => {
    fetchChequesPendientes.mockReset();
    fetchCajas.mockReset();
    fetchCajas.mockResolvedValue([
      { id: 1, nombre: "Bambina", slug: "bambina" },
      { id: 2, nombre: "Ebel", slug: "ebel" },
    ]);
  });

  it("muestra Endose junto a Liquidar solo si el cheque es endosable y hay onEndosar", async () => {
    fetchChequesPendientes.mockResolvedValue(
      page([
        cheque({ id: 1, descripcion: "Endosable", endosable: true }),
        cheque({ id: 2, descripcion: "No endosable", endosable: false }),
      ]),
    );
    const { rerender } = render(
      <ChequesPendientesBlock
        cajaId={1}
        onLiquidar={vi.fn()}
        onEndosar={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    const filas = await screen.findByText("Endosable").then(() => screen.getAllByRole("row").slice(1));
    expect(within(filas[0]).getByRole("button", { name: /^endose$/i })).toBeInTheDocument();
    expect(within(filas[0]).getByRole("button", { name: /^liquidar$/i })).toBeInTheDocument();
    expect(within(filas[1]).queryByRole("button", { name: /^endose$/i })).not.toBeInTheDocument();

    rerender(<ChequesPendientesBlock cajaId={1} onLiquidar={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /^endose$/i })).not.toBeInTheDocument();
  });

  it("con fecha futura Liquidar está deshabilitado y Endose habilitado; con fecha alcanzada ambos", async () => {
    fetchChequesPendientes.mockResolvedValue(
      page([
        cheque({ id: 1, descripcion: "Futuro", fecha_liquidacion: "2999-01-01", endosable: true }),
        cheque({ id: 2, descripcion: "Vencido", fecha_liquidacion: "2020-01-01", endosable: true }),
      ]),
    );
    render(
      <ChequesPendientesBlock
        cajaId={1}
        onLiquidar={vi.fn()}
        onEndosar={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    const futuro = (await screen.findByText("Futuro")).closest("tr") as HTMLElement;
    const vencido = screen.getByText("Vencido").closest("tr") as HTMLElement;
    expect(within(futuro).getByRole("button", { name: /^liquidar$/i })).toBeDisabled();
    expect(within(futuro).getByRole("button", { name: /^endose$/i })).toBeEnabled();
    expect(within(vencido).getByRole("button", { name: /^liquidar$/i })).toBeEnabled();
    expect(within(vencido).getByRole("button", { name: /^endose$/i })).toBeEnabled();
  });

  it("no ofrece Endose en solo lectura", async () => {
    fetchChequesPendientes.mockResolvedValue(page([cheque({ endosable: true })]));
    render(
      <ChequesPendientesBlock
        cajaId={1}
        readOnly
        onEndosar={vi.fn().mockResolvedValue(undefined)}
      />,
    );
    await screen.findByText("Cheque Banco Nación 0001234");
    expect(screen.queryByRole("button", { name: /^endose$/i })).not.toBeInTheDocument();
  });

  it("abre el diálogo, confirma con onEndosar y recarga el bloque", async () => {
    fetchChequesPendientes.mockResolvedValue(page([cheque({ id: 7, endosable: true })]));
    const onEndosar = vi.fn().mockResolvedValue(undefined);
    render(<ChequesPendientesBlock cajaId={1} onEndosar={onEndosar} />);
    await screen.findByText("Cheque Banco Nación 0001234");
    const callsBefore = fetchChequesPendientes.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: /^endose$/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("radio", { name: "Ebel" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));

    await waitFor(() =>
      expect(onEndosar).toHaveBeenCalledWith(expect.objectContaining({ id: 7 }), 2),
    );
    await waitFor(() =>
      expect(fetchChequesPendientes.mock.calls.length).toBeGreaterThan(callsBefore),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("si el endose falla muestra un error genérico y el cheque permanece", async () => {
    fetchChequesPendientes.mockResolvedValue(page([cheque({ endosable: true })]));
    const onEndosar = vi.fn().mockRejectedValue(new Error('{"detail":"interno"}'));
    render(<ChequesPendientesBlock cajaId={1} onEndosar={onEndosar} />);
    await screen.findByText("Cheque Banco Nación 0001234");

    fireEvent.click(screen.getByRole("button", { name: /^endose$/i }));
    fireEvent.click(await screen.findByRole("radio", { name: "Ebel" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar" }));

    expect(await screen.findByText("No se pudo endosar el cheque.")).toBeInTheDocument();
    expect(screen.queryByText(/interno/)).not.toBeInTheDocument();
    expect(screen.getByText("Cheque Banco Nación 0001234")).toBeInTheDocument();
  });

  it("cancelar el diálogo no llama a onEndosar", async () => {
    fetchChequesPendientes.mockResolvedValue(page([cheque({ endosable: true })]));
    const onEndosar = vi.fn();
    render(<ChequesPendientesBlock cajaId={1} onEndosar={onEndosar} />);
    await screen.findByText("Cheque Banco Nación 0001234");

    fireEvent.click(screen.getByRole("button", { name: /^endose$/i }));
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(onEndosar).not.toHaveBeenCalled();
  });
});

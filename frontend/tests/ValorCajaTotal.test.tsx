/**
 * "Valor de caja total": solo Secretaria; elige una fecha futura y muestra, por moneda,
 * el valor de caja ± cheques pendientes de liquidar hasta esa fecha. El cálculo es del servidor.
 */

import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ValorCajaTotal from "../src/components/ValorCajaTotal";

const fetchSaldoProyectado = vi.fn();
let authState: { rol: string | null } = { rol: "secretaria" };

vi.mock("../src/services/api", () => ({
  fetchSaldoProyectado: (...args: unknown[]) => fetchSaldoProyectado(...args),
}));
vi.mock("../src/hooks/useAuth", () => ({ useAuth: () => authState }));

const caja = { id: 1, nombre: "Ebel", slug: "ebel" };

function respuesta(fecha: string) {
  return {
    caja,
    fecha,
    monedas: [
      { moneda: "ARS", saldo_actual: "1000.00", efecto_cheques: "500.00", saldo_proyectado: "1500.00", cheques: 2 },
      { moneda: "USD", saldo_actual: "10.00", efecto_cheques: "0.00", saldo_proyectado: "10.00", cheques: 0 },
    ],
  };
}

beforeEach(() => {
  authState = { rol: "secretaria" };
  fetchSaldoProyectado.mockReset();
  fetchSaldoProyectado.mockImplementation((_id: number, fecha: string) =>
    Promise.resolve(respuesta(fecha)),
  );
});

describe("ValorCajaTotal", () => {
  it("no se muestra para el escribano", () => {
    authState = { rol: "escribano" };
    render(<ValorCajaTotal cajaId={1} fecha="2999-01-01" />);

    expect(screen.queryByText("Valor de caja total")).not.toBeInTheDocument();
    expect(fetchSaldoProyectado).not.toHaveBeenCalled();
  });

  it("sin fecha en Hasta calcula con todos los cheques pendientes", async () => {
    render(<ValorCajaTotal cajaId={1} fecha="" />);

    await waitFor(() => expect(fetchSaldoProyectado).toHaveBeenCalledWith(1, undefined));
    expect(await screen.findByTestId("valor-caja-total-ARS")).toBeInTheDocument();
    expect(screen.getByText(/Con todos los cheques pendientes/)).toBeInTheDocument();
  });

  it("con una fecha futura calcula solo y muestra el total por moneda", async () => {
    render(<ValorCajaTotal cajaId={1} fecha="2999-01-01" />);

    await waitFor(() => expect(fetchSaldoProyectado).toHaveBeenCalledWith(1, "2999-01-01"));
    expect(await screen.findByTestId("valor-caja-total-ARS")).toHaveTextContent("$ 1500.00");
    expect(screen.getByTestId("valor-caja-total-USD")).toHaveTextContent("$ 10.00");
  });

  it("recalcula cuando cambia la fecha", async () => {
    const { rerender } = render(<ValorCajaTotal cajaId={1} fecha="2999-01-01" />);
    await waitFor(() => expect(fetchSaldoProyectado).toHaveBeenCalledTimes(1));

    rerender(<ValorCajaTotal cajaId={1} fecha="2999-02-01" />);

    await waitFor(() => expect(fetchSaldoProyectado).toHaveBeenLastCalledWith(1, "2999-02-01"));
  });

  it("con una fecha pasada no consulta", () => {
    render(<ValorCajaTotal cajaId={1} fecha="2020-01-01" />);

    expect(fetchSaldoProyectado).not.toHaveBeenCalled();
    expect(screen.getByText(/solo se calcula con una fecha futura/)).toBeInTheDocument();
  });

  it("recalcula cuando cambia refreshKey", async () => {
    const { rerender } = render(<ValorCajaTotal cajaId={1} fecha="2999-01-01" refreshKey={0} />);
    await waitFor(() => expect(fetchSaldoProyectado).toHaveBeenCalledTimes(1));

    rerender(<ValorCajaTotal cajaId={1} fecha="2999-01-01" refreshKey={1} />);

    await waitFor(() => expect(fetchSaldoProyectado).toHaveBeenCalledTimes(2));
  });

  it("muestra un error si falla el servidor", async () => {
    fetchSaldoProyectado.mockRejectedValue(new Error("boom"));
    render(<ValorCajaTotal cajaId={1} fecha="2999-01-01" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo calcular");
  });
});

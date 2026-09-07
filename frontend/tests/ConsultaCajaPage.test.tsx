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
  saldoArs: string,
  saldoUsd: string = "0.00",
) {
  return {
    caja,
    saldo_ars: saldoArs,
    saldo_usd: saldoUsd,
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
        moneda: "ARS" as const,
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

const authState = {
  token: "test-token",
  rol: "escribano",
  isAuthenticated: true,
  login: vi.fn(),
  logout: vi.fn(),
};

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => authState,
}));

describe("ConsultaCajaPage", () => {
  beforeEach(() => {
    authState.rol = "escribano";
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
    expect(screen.getByRole("button", { name: /^consulta$/i })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /subtotal general/i }),
    ).not.toBeInTheDocument();
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
    expect(document.querySelector(".cajas-adicionales")).not.toHaveAttribute("open");

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

  it("does not list archived cajas in the dropdown or additional boxes", async () => {
    await renderConsulta();
    fireEvent.click(screen.getByText("Ver en conjunto con otras cajas"));

    expect(screen.queryByText("Caja Archivada")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("checkbox", { name: /caja archivada/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /martin/i })).toBeInTheDocument();
  });

  it("hides Subtotal general from escribano and shows it for secretaria", async () => {
    const { rerender } = render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: /subtotal general/i }),
    ).not.toBeInTheDocument();

    authState.rol = "secretaria";
    rerender(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /subtotal general/i }),
      ).toBeInTheDocument();
    });
  });

  it("loads subtotal general for secretaria without requiring a caja consulta", async () => {
    authState.rol = "secretaria";
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") {
        return Promise.resolve([...CAJAS]);
      }
      if (path === "/api/v1/cajas/saldo-general") {
        return Promise.resolve({
          subtotal_general_ars: "1234.50",
          subtotal_general_usd: "0.00",
          cajas_incluidas: 3,
          cajas: [
            { caja: CAJAS[0], saldo_ars: "250.00", saldo_usd: "0.00" },
            { caja: CAJAS[1], saldo_ars: "80.00", saldo_usd: "0.00" },
            { caja: CAJAS[2], saldo_ars: "904.50", saldo_usd: "0.00" },
          ],
        });
      }
      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /subtotal general/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /subtotal general/i }));

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith("/api/v1/cajas/saldo-general");
    });
    expect(screen.getByRole("heading", { name: /subtotal general/i })).toBeInTheDocument();
    expect(screen.getByText("$ 1234.50")).toBeInTheDocument();
    const resumen = screen.getByRole("table");
    expect(resumen).toHaveTextContent("Bambina");
    expect(resumen).toHaveTextContent("$ 250.00");
    expect(resumen).toHaveTextContent("Martin");
    expect(resumen).toHaveTextContent("$ 80.00");
    expect(resumen).toHaveTextContent("Gabriel");
    expect(resumen).toHaveTextContent("$ 904.50");
    expect(screen.queryByRole("heading", { name: /valor de caja/i })).not.toBeInTheDocument();
  });

  it("replaces consulta results with subtotal general and vice versa", async () => {
    authState.rol = "secretaria";
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") {
        return Promise.resolve([...CAJAS]);
      }
      if (path === "/api/v1/cajas/saldo-general") {
        return Promise.resolve({
          subtotal_general_ars: "1234.50",
          subtotal_general_usd: "0.00",
          cajas_incluidas: 3,
          cajas: [
            { caja: CAJAS[0], saldo_ars: "250.00", saldo_usd: "0.00" },
            { caja: CAJAS[1], saldo_ars: "80.00", saldo_usd: "0.00" },
            { caja: CAJAS[2], saldo_ars: "904.50", saldo_usd: "0.00" },
          ],
        });
      }
      if (path === "/api/v1/cajas/1/saldo") {
        return Promise.resolve(saldoFor(CAJAS[0], "250.00"));
      }
      if (path === "/api/v1/cajas/1/movimientos?page=1") {
        return Promise.resolve(
          movimientosFor(CAJAS[0], "Movimiento de prueba consulta", 1, 1),
        );
      }
      return Promise.reject(new Error(`Unexpected path: ${path}`));
    });

    render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^consulta$/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^consulta$/i }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /valor de caja/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /subtotal general/i }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /subtotal general/i })).toBeInTheDocument();
    });
    expect(screen.queryByRole("heading", { name: /valor de caja/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /valor en conjunto/i })).not.toBeInTheDocument();
    expect(screen.queryByText("Movimiento de prueba consulta")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^consulta$/i }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /valor de caja/i })).toBeInTheDocument();
    });
    expect(screen.queryByRole("heading", { name: /subtotal general/i })).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// T028 — Filtros de moneda y fecha en Registro y Consulta (TDD — TDD red)
// Deben FALLAR hasta que T032 / T033 implementen los controles.
// ---------------------------------------------------------------------------

describe("ConsultaCajaPage — filtros de listado (T028)", () => {
  beforeEach(() => {
    authState.rol = "escribano";
    apiGet.mockImplementation((path: string) => {
      if (path === "/api/v1/cajas") return Promise.resolve([...CAJAS]);
      if (path === "/api/v1/cajas/1/saldo")
        return Promise.resolve(saldoFor(CAJAS[0], "250.00"));
      if (/\/api\/v1\/cajas\/1\/movimientos/.test(path))
        return Promise.resolve(movimientosFor(CAJAS[0], "Movimiento consulta filtro", 1, 1));
      return Promise.reject(new Error(`Unexpected: ${path}`));
    });
  });

  it("T028: escribano sees a moneda filter dropdown with options Todas/ARS/USD", async () => {
    render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^consulta$/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /valor de caja/i })).toBeInTheDocument();
    });

    const monedaFilter = screen.getByLabelText(/filtrar.*moneda|moneda.*filtro|moneda/i);
    expect(monedaFilter).toBeInTheDocument();
    const options = Array.from((monedaFilter as HTMLSelectElement).options).map(
      (o) => o.value,
    );
    expect(options).toContain("");
    expect(options).toContain("ARS");
    expect(options).toContain("USD");
  });

  it("T028: escribano sees date-from and date-to filter inputs", async () => {
    render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^consulta$/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /valor de caja/i })).toBeInTheDocument();
    });

    expect(screen.getByLabelText(/desde/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/hasta/i)).toBeInTheDocument();
  });

  it("T028: selecting a moneda filter calls the API with the moneda query param", async () => {
    render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^consulta$/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /valor de caja/i })).toBeInTheDocument();
    });

    const monedaFilter = screen.getByLabelText(/filtrar.*moneda|moneda.*filtro|moneda/i);
    fireEvent.change(monedaFilter, { target: { value: "USD" } });

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith(
        expect.stringContaining("moneda=USD"),
      );
    });
  });

  it("T028: clearing the moneda filter reloads the full list (no moneda param)", async () => {
    render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^consulta$/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /valor de caja/i })).toBeInTheDocument();
    });

    const monedaFilter = screen.getByLabelText(/filtrar.*moneda|moneda.*filtro|moneda/i);
    fireEvent.change(monedaFilter, { target: { value: "USD" } });

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith(expect.stringContaining("moneda=USD"));
    });

    // limpiar filtro
    fireEvent.change(monedaFilter, { target: { value: "" } });

    await waitFor(() => {
      const lastCall = apiGet.mock.calls[apiGet.mock.calls.length - 1][0] as string;
      expect(lastCall).not.toContain("moneda=");
    });
  });

  it("T028: saldo header is unchanged when a filter is applied", async () => {
    render(
      <MemoryRouter>
        <ConsultaCajaPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Bambina")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^consulta$/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /valor de caja/i })).toBeInTheDocument();
      expect(screen.getByText("$ 250.00")).toBeInTheDocument();
    });

    // aplicar filtro — el saldo debe mantenerse
    const monedaFilter = screen.getByLabelText(/filtrar.*moneda|moneda.*filtro|moneda/i);
    fireEvent.change(monedaFilter, { target: { value: "USD" } });

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith(expect.stringContaining("moneda=USD"));
    });

    // El saldo ARS sigue mostrando $ 250.00 (no fue refiltrado)
    expect(screen.getByText("$ 250.00")).toBeInTheDocument();
  });
});


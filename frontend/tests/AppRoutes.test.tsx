import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";

const authState = {
  token: "test-token" as string | null,
  rol: "escribano",
  username: "escribano",
  isAuthenticated: true,
  login: vi.fn(),
  logout: vi.fn(),
  changePassword: vi.fn(),
};

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => authState,
}));

vi.mock("../src/services/api", () => ({
  apiGet: (path: string) => {
    if (path === "/api/v1/cajas") {
      return Promise.resolve([]);
    }
    return Promise.reject(new Error(`Unexpected path: ${path}`));
  },
  fetchCheques: () =>
    Promise.resolve({ items: [], page: 1, page_size: 20, total_items: 0, total_pages: 0 }),
  liquidarCheque: vi.fn(),
  listCajasConfig: () => Promise.resolve([]),
  createCaja: vi.fn(),
  archiveCaja: vi.fn(),
  unarchiveCaja: vi.fn(),
  getAuthToken: () => "test-token",
  setAuthToken: vi.fn(),
}));

describe("App routes — configuración RBAC", () => {
  beforeEach(() => {
    authState.rol = "escribano";
    authState.username = "escribano";
    authState.isAuthenticated = true;
  });

  it("redirects escribano away from /configuracion", async () => {
    render(
      <MemoryRouter initialEntries={["/configuracion"]}>
        <App />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", { name: /consulta de caja/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /^configuración$/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /configuración/i }),
    ).not.toBeInTheDocument();
  });

  it("lets secretaria open /configuracion", async () => {
    authState.rol = "secretaria";
    authState.username = "admin";

    render(
      <MemoryRouter initialEntries={["/configuracion"]}>
        <App />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", { name: /^configuración$/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /configuración/i })).toBeInTheDocument();
  });
});

describe("App routes — /cheques (T046)", () => {
  beforeEach(() => {
    authState.rol = "escribano";
    authState.username = "escribano";
    authState.isAuthenticated = true;
  });

  it("redirects to login when there is no session", async () => {
    authState.isAuthenticated = false;

    render(
      <MemoryRouter initialEntries={["/cheques"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: /escribanía barat/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /^cheques$/i })).not.toBeInTheDocument();
  });

  it.each([
    ["escribano", "escribano"],
    ["secretaria", "admin"],
  ])("lets %s open /cheques", async (rol, username) => {
    authState.rol = rol;
    authState.username = username;

    render(
      <MemoryRouter initialEntries={["/cheques"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { level: 1, name: /^cheques$/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cheques" })).toBeInTheDocument();
  });
});

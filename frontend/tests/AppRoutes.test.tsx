import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";

const authState = {
  token: "test-token",
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

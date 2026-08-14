import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "../src/pages/LoginPage";

const login = vi.fn();
const postChangePasswordPublic = vi.fn();

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({
    login,
    logout: vi.fn(),
    token: null,
    rol: null,
    isAuthenticated: false,
  }),
}));

vi.mock("../src/services/api", () => ({
  postChangePasswordPublic: (...args: unknown[]) =>
    postChangePasswordPublic(...args),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    login.mockReset();
    postChangePasswordPublic.mockReset();
  });

  it("submits username and password to the login API", async () => {
    login.mockResolvedValue({
      access_token: "test-token",
      token_type: "bearer",
      expires_in: 28800,
      rol: "secretaria",
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/usuario/i), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText(/^contraseña$/i), {
      target: { value: "admin" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ingresar/i }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith("admin", "admin");
    });
  });

  it("replaces the login form when Cambiar contraseña is clicked", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: /cambiar contraseña/i }));

    expect(
      screen.getByRole("button", { name: /guardar contraseña/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /ingresar/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña actual/i)).toBeInTheDocument();
  });

  it("returns to login when Cancelar is clicked", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: /cambiar contraseña/i }));
    fireEvent.click(screen.getByRole("button", { name: /cancelar/i }));

    expect(screen.getByRole("button", { name: /ingresar/i })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /guardar contraseña/i }),
    ).not.toBeInTheDocument();
  });

  it("shows success and login form after a successful password change", async () => {
    postChangePasswordPublic.mockResolvedValue(undefined);

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: /cambiar contraseña/i }));
    fireEvent.change(screen.getByLabelText(/usuario/i), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText(/contraseña actual/i), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText(/nueva contraseña/i), {
      target: { value: "NuevaClave1" },
    });
    fireEvent.change(screen.getByLabelText(/confirmar contraseña/i), {
      target: { value: "NuevaClave1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /guardar contraseña/i }));

    await waitFor(() => {
      expect(postChangePasswordPublic).toHaveBeenCalledWith({
        username: "admin",
        current_password: "admin",
        new_password: "NuevaClave1",
        new_password_confirm: "NuevaClave1",
      });
    });

    expect(screen.getByText(/contraseña actualizada/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ingresar/i })).toBeInTheDocument();
  });
});

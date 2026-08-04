import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "../src/pages/LoginPage";

const login = vi.fn();

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({
    login,
    logout: vi.fn(),
    token: null,
    rol: null,
    isAuthenticated: false,
  }),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    login.mockReset();
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
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: "admin" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ingresar/i }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith("admin", "admin");
    });
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Navbar } from "../src/components/layout/Navbar";

const changePassword = vi.fn();
const logout = vi.fn();
const authState = {
  token: "test-token",
  rol: "secretaria",
  username: "admin",
  isAuthenticated: true,
  login: vi.fn(),
  changePassword,
  logout,
};

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => authState,
}));

describe("Navbar", () => {
  beforeEach(() => {
    changePassword.mockReset();
    logout.mockReset();
    authState.rol = "secretaria";
    authState.username = "admin";
  });

  it("opens the user section when the username is clicked", () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "admin" }));

    expect(screen.getByText(/cambiar contraseña/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña actual/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /configuración/i })).toBeInTheDocument();
  });

  it("places Configuración between username and Salir", () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    const userCluster = screen.getByRole("button", { name: "admin" }).closest(
      ".navbar__user",
    );
    expect(userCluster).not.toBeNull();
    const labels = Array.from(
      userCluster!.querySelectorAll("button, a"),
    ).map((el) => el.textContent?.trim());
    expect(labels).toEqual(["admin", "Configuración", "Salir"]);
  });

  it("hides Configuración from escribano and shows it for secretaria", () => {
    const { rerender } = render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: /configuración/i })).toBeInTheDocument();

    authState.rol = "escribano";
    authState.username = "escribano";
    rerender(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    expect(
      screen.queryByRole("link", { name: /configuración/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^consulta$/i })).toBeInTheDocument();
  });

  it("submits the password change and logs out on success", async () => {
    changePassword.mockResolvedValue(undefined);

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "admin" }));
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
      expect(changePassword).toHaveBeenCalledWith(
        "admin",
        "NuevaClave1",
        "NuevaClave1",
      );
    });
    expect(screen.queryByText(/cambiar contraseña/i)).not.toBeInTheDocument();
  });
});

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

  it("closes the password panel from the mobile backdrop control", () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "admin" }));
    expect(screen.getByText(/cambiar contraseña/i)).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /cerrar cambio de contraseña/i }),
    );
    expect(screen.queryByText(/cambiar contraseña/i)).not.toBeInTheDocument();
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

  it("exposes the app name on the header landmark", () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("banner", { name: "Escribanía Barat" }),
    ).toBeInTheDocument();
  });

  it("toggles the compact menu and lists the same destinations as desktop for secretaria", () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    const toggle = screen.getByRole("button", { name: "Menú" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    const labels = Array.from(
      document.querySelectorAll(
        ".navbar__links a, .navbar__user a, .navbar__logout",
      ),
    ).map((el) => el.textContent?.trim());
    expect(labels).toEqual([
      "Registro",
      "Plazos fijos",
      "Consulta",
      "Consulta plazos fijos",
      "Cheques",
      "Impresión",
      "Configuración",
      "Salir",
    ]);
  });

  it("lists the same compact-menu destinations as desktop for escribano", () => {
    authState.rol = "escribano";
    authState.username = "escribano";

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Menú" }));

    const labels = Array.from(
      document.querySelectorAll(
        ".navbar__links a, .navbar__user a, .navbar__logout",
      ),
    ).map((el) => el.textContent?.trim());
    expect(labels).toEqual([
      "Consulta",
      "Consulta plazos fijos",
      "Cheques",
      "Impresión",
      "Salir",
    ]);
  });

  it("T045: places Cheques between Consulta plazos fijos and Impresión for both roles", () => {
    const { rerender } = render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    const linkLabels = () =>
      Array.from(document.querySelectorAll(".navbar__links a")).map((el) =>
        el.textContent?.trim(),
      );

    expect(linkLabels()).toEqual([
      "Registro",
      "Plazos fijos",
      "Consulta",
      "Consulta plazos fijos",
      "Cheques",
      "Impresión",
    ]);
    expect(screen.getByRole("link", { name: "Cheques" })).toHaveAttribute("href", "/cheques");

    authState.rol = "escribano";
    authState.username = "escribano";
    rerender(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    expect(linkLabels()).toEqual([
      "Consulta",
      "Consulta plazos fijos",
      "Cheques",
      "Impresión",
    ]);
  });

  it("closes the compact menu when a destination is chosen", () => {
    render(
      <MemoryRouter initialEntries={["/registro"]}>
        <Navbar />
      </MemoryRouter>,
    );

    const toggle = screen.getByRole("button", { name: "Menú" });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(screen.getByRole("link", { name: /^consulta$/i }));
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});

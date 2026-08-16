import { FormEvent, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";

const links = [
  { to: "/registro", label: "Registro", roles: ["secretaria"] },
  { to: "/plazos-fijos", label: "Plazos fijos", roles: ["secretaria"] },
  { to: "/consulta", label: "Consulta", roles: ["secretaria", "escribano"] },
  {
    to: "/consulta-plazos-fijos",
    label: "Consulta plazos fijos",
    roles: ["secretaria", "escribano"],
  },
  { to: "/impresion", label: "Impresión", roles: ["secretaria", "escribano"] },
] as const;

export function Navbar() {
  const { rol, username, logout, changePassword } = useAuth();
  const navigate = useNavigate();
  const [navOpen, setNavOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const visibleLinks = links.filter(
    (link) => rol && (link.roles as readonly string[]).includes(rol),
  );

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  function closeNav() {
    setNavOpen(false);
  }

  function closeMenu() {
    setMenuOpen(false);
    setCurrentPassword("");
    setNewPassword("");
    setNewPasswordConfirm("");
    setError(null);
  }

  async function handleChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (newPassword !== newPasswordConfirm) {
      setError("La confirmación no coincide con la nueva contraseña.");
      return;
    }

    setSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword, newPasswordConfirm);
      closeMenu();
      navigate("/login", { replace: true });
    } catch {
      setError(
        "No se pudo cambiar la contraseña. Verifique la contraseña actual.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const navbarClass = [
    "navbar",
    navOpen ? "navbar--nav-open" : "",
    menuOpen ? "navbar--password-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <header className={navbarClass} aria-label="Escribanía Barat">
      <div className="navbar__brand">Escribanía Barat</div>
      <button
        type="button"
        className="navbar__toggle"
        aria-expanded={navOpen}
        aria-controls="navbar-links"
        onClick={() => {
          setNavOpen((open) => !open);
          setMenuOpen(false);
        }}
      >
        Menú
      </button>
      <nav
        id="navbar-links"
        className="navbar__links"
        aria-label="Navegación principal"
      >
        {visibleLinks.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              isActive ? "navbar__link navbar__link--active" : "navbar__link"
            }
            onClick={closeNav}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="navbar__user">
        {username ? (
          <div className="navbar__user-menu">
            <button
              type="button"
              className="navbar__username"
              aria-expanded={menuOpen}
              aria-haspopup="true"
              onClick={() => {
                setMenuOpen((open) => !open);
                setNavOpen(false);
              }}
            >
              {username}
            </button>
            {menuOpen ? (
              <form
                className="navbar__password-panel"
                onSubmit={handleChangePassword}
              >
                <p className="navbar__password-title">Cambiar contraseña</p>
                <label className="field">
                  <span>Contraseña actual</span>
                  <input
                    name="current_password"
                    type="password"
                    autoComplete="current-password"
                    value={currentPassword}
                    disabled={submitting}
                    onChange={(event) => setCurrentPassword(event.target.value)}
                    required
                  />
                </label>
                <label className="field">
                  <span>Nueva contraseña</span>
                  <input
                    name="new_password"
                    type="password"
                    autoComplete="new-password"
                    minLength={8}
                    value={newPassword}
                    disabled={submitting}
                    onChange={(event) => setNewPassword(event.target.value)}
                    required
                  />
                </label>
                <label className="field">
                  <span>Confirmar contraseña</span>
                  <input
                    name="new_password_confirm"
                    type="password"
                    autoComplete="new-password"
                    minLength={8}
                    value={newPasswordConfirm}
                    disabled={submitting}
                    onChange={(event) =>
                      setNewPasswordConfirm(event.target.value)
                    }
                    required
                  />
                </label>
                {error ? <p className="form-error">{error}</p> : null}
                <button
                  type="submit"
                  className="button button--primary button--small"
                  disabled={submitting}
                >
                  {submitting ? "Guardando…" : "Guardar contraseña"}
                </button>
              </form>
            ) : null}
          </div>
        ) : null}
        {rol === "secretaria" ? (
          <NavLink
            to="/configuracion"
            className={({ isActive }) =>
              isActive ? "navbar__link navbar__link--active" : "navbar__link"
            }
          >
            Configuración
          </NavLink>
        ) : null}
        <button type="button" className="navbar__logout" onClick={handleLogout}>
          Salir
        </button>
      </div>
      {menuOpen ? (
        <button
          type="button"
          className="navbar__password-backdrop"
          aria-label="Cerrar cambio de contraseña"
          onClick={closeMenu}
        />
      ) : null}
    </header>
  );
}

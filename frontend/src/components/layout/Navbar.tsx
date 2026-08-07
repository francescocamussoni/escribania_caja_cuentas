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
  const { rol, username, logout } = useAuth();
  const navigate = useNavigate();

  const visibleLinks = links.filter(
    (link) => rol && (link.roles as readonly string[]).includes(rol),
  );

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="navbar">
      <div className="navbar__brand">Escribanía Barat</div>
      <nav className="navbar__links" aria-label="Navegación principal">
        {visibleLinks.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              isActive ? "navbar__link navbar__link--active" : "navbar__link"
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="navbar__user">
        {username ? <span>{username}</span> : null}
        <button type="button" className="navbar__logout" onClick={handleLogout}>
          Salir
        </button>
      </div>
    </header>
  );
}

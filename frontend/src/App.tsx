import { Link, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { useAuth } from "./hooks/useAuth";
import ConsultaCajaPage from "./pages/ConsultaCajaPage";
import LoginPage from "./pages/LoginPage";
import RegistroCajaPage from "./pages/RegistroCajaPage";

function HomePage() {
  const { rol } = useAuth();

  if (rol === "secretaria") {
    return <Navigate to="/registro" replace />;
  }

  return <Navigate to="/consulta" replace />;
}

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function SecretariaOnlyRoute({ children }: { children: JSX.Element }) {
  const { rol } = useAuth();

  if (rol !== "secretaria") {
    return <Navigate to="/consulta" replace />;
  }

  return children;
}

function AppLayout() {
  const { rol } = useAuth();

  return (
    <div className="app-layout">
      <header className="app-header">
        <nav className="app-nav" aria-label="Navegación principal">
          {rol === "secretaria" ? (
            <Link to="/registro">Registro</Link>
          ) : null}
          <Link to="/consulta">Consulta</Link>
        </nav>
      </header>
      <Outlet />
    </div>
  );
}

export default function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
        }
      />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<HomePage />} />
        <Route
          path="/registro"
          element={
            <SecretariaOnlyRoute>
              <RegistroCajaPage />
            </SecretariaOnlyRoute>
          }
        />
        <Route path="/consulta" element={<ConsultaCajaPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

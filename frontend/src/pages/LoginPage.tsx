import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const response = await login(username, password);
      const destination =
        response.rol === "secretaria" ? "/registro" : "/consulta";
      navigate(destination, { replace: true });
    } catch {
      setError("No se pudo iniciar sesión. Verifique sus credenciales.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="app-shell login-page">
      <h1>Iniciar sesión</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="username">Usuario</label>
        <input
          id="username"
          name="username"
          type="text"
          autoComplete="username"
          value={username}
          disabled={submitting}
          onChange={(event) => setUsername(event.target.value)}
          required
        />

        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          disabled={submitting}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        {error ? <p className="form-error">{error}</p> : null}

        <button type="submit" disabled={submitting}>
          {submitting ? "Ingresando…" : "Ingresar"}
        </button>
      </form>
    </main>
  );
}

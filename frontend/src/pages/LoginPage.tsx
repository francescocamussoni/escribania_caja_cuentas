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
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Escribanía Barat</h1>
        <p className="login-card__subtitle">Caja y cuentas</p>

        <label className="field">
          <span>Usuario</span>
          <input
            name="username"
            type="text"
            autoComplete="username"
            value={username}
            disabled={submitting}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </label>

        <label className="field">
          <span>Contraseña</span>
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            disabled={submitting}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error ? <p className="form-error">{error}</p> : null}

        <button
          type="submit"
          className="button button--primary"
          disabled={submitting}
        >
          {submitting ? "Ingresando…" : "Ingresar"}
        </button>
      </form>
    </div>
  );
}

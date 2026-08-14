import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { postChangePasswordPublic } from "../services/api";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [mode, setMode] = useState<"login" | "change">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function resetChangeFields() {
    setCurrentPassword("");
    setNewPassword("");
    setNewPasswordConfirm("");
  }

  function showLogin() {
    setMode("login");
    setError(null);
    resetChangeFields();
  }

  function showChange() {
    setMode("change");
    setError(null);
    setSuccess(null);
    setPassword("");
    resetChangeFields();
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
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

  async function handleChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (newPassword !== newPasswordConfirm) {
      setError("La confirmación no coincide con la nueva contraseña.");
      return;
    }

    setSubmitting(true);

    try {
      await postChangePasswordPublic({
        username,
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      });
      resetChangeFields();
      setPassword("");
      setMode("login");
      setSuccess("Contraseña actualizada. Ingrese con la nueva clave.");
    } catch {
      setError(
        "No se pudo cambiar la contraseña. Verifique usuario y contraseña actual.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      {mode === "login" ? (
        <form className="login-card" onSubmit={handleLogin}>
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

          {success ? <p className="form-success">{success}</p> : null}
          {error ? <p className="form-error">{error}</p> : null}

          <button
            type="submit"
            className="button button--primary"
            disabled={submitting}
          >
            {submitting ? "Ingresando…" : "Ingresar"}
          </button>

          <button
            type="button"
            className="login-card__link"
            disabled={submitting}
            onClick={showChange}
          >
            Cambiar contraseña
          </button>
        </form>
      ) : (
        <form className="login-card" onSubmit={handleChangePassword}>
          <h1>Escribanía Barat</h1>
          <p className="login-card__subtitle">Cambiar contraseña</p>

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
              onChange={(event) => setNewPasswordConfirm(event.target.value)}
              required
            />
          </label>

          {error ? <p className="form-error">{error}</p> : null}

          <div className="login-card__actions">
            <button
              type="submit"
              className="button button--primary"
              disabled={submitting}
            >
              {submitting ? "Guardando…" : "Guardar contraseña"}
            </button>
            <button
              type="button"
              className="button button--secondary"
              disabled={submitting}
              onClick={showLogin}
            >
              Cancelar
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

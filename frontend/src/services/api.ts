// Empty string = same-origin (Vite dev proxy). Set VITE_API_BASE_URL for direct API access.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export type ApiRequestOptions = Omit<RequestInit, "headers"> & {
  headers?: Record<string, string>;
};

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      message || `API request failed with status ${response.status}`,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: "GET" });
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function apiDelete(path: string): Promise<void> {
  return apiRequest<void>(path, { method: "DELETE" });
}

export type ChangePasswordPublicPayload = {
  username: string;
  current_password: string;
  new_password: string;
  new_password_confirm: string;
};

export async function postChangePasswordPublic(
  payload: ChangePasswordPublicPayload,
): Promise<void> {
  await apiPost<void>("/api/v1/auth/change-password", payload);
}

export type ChangePasswordAuthenticatedPayload = {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
};

export async function postChangePasswordMe(
  payload: ChangePasswordAuthenticatedPayload,
): Promise<void> {
  await apiPost<void>("/api/v1/auth/me/password", payload);
}

export type Caja = {
  id: number;
  nombre: string;
  slug: string;
  estado?: "activa" | "archivada";
};

export type CajaSaldo = {
  caja: Caja;
  saldo_ars: string;
  saldo_usd: string;
  ultimo_movimiento_at: string | null;
};

export type CajaSaldoGeneralItem = {
  caja: Caja;
  saldo_ars: string;
  saldo_usd: string;
};

export type CajaSaldoGeneral = {
  subtotal_general_ars: string;
  subtotal_general_usd: string;
  cajas_incluidas: number;
  cajas: CajaSaldoGeneralItem[];
};

export type Movimiento = {
  id: number;
  descripcion: string;
  monto: string;
  tipo: "entrada" | "salida";
  moneda: "ARS" | "USD";
  subtotal: string;
  fecha: string;
  editable: boolean;
  caja: Caja;
};

export type MovimientoCreateResponse = {
  movimiento: Movimiento;
  complementario: Movimiento | null;
};

export type PaginatedMovimientos = {
  items: Movimiento[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
};

export type CreateMovimientoPayload = {
  descripcion: string;
  monto: string;
  tipo: "entrada" | "salida";
  moneda?: "ARS" | "USD";
  registrar_complementario?: boolean;
};

export type UpdateMovimientoPayload = {
  descripcion?: string;
  monto?: string;
  tipo?: "entrada" | "salida";
  moneda?: "ARS" | "USD";
};

export type PlazoFijo = {
  id: number;
  monto_ingresado: string;
  monto_a_vencimiento: string;
  fecha_vencimiento: string;
  vencido: boolean;
  created_at: string;
  caja: Caja;
};

export type PlazosFijosResumen = {
  caja: Caja;
  total_monto_ingresado_activos: string;
  total_monto_a_vencimiento_activos: string;
};

export type PaginatedPlazosFijos = {
  items: PlazoFijo[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
};

export type CreatePlazoFijoPayload = {
  monto_ingresado: string;
  monto_a_vencimiento: string;
  fecha_vencimiento: string;
};

export type UpdatePlazoFijoPayload = {
  monto_ingresado?: string;
  monto_a_vencimiento?: string;
  fecha_vencimiento?: string;
};

export type InformeTipo = "CAJA" | "PLAZO_FIJO";
export type InformeModo = "MES_ANIO" | "PERIODO";

export type InformePdfRequest = {
  tipo: InformeTipo;
  caja_id: number;
  modo: InformeModo;
  hasta_hoy?: boolean;
  mes?: number;
  anio?: number;
  fecha_inicio?: string;
  fecha_fin?: string;
};

export type InformePdfResult = {
  blob: Blob;
  filename: string;
};

export async function postInformePdf(
  body: InformePdfRequest,
): Promise<InformePdfResult> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/informes/pdf`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      message || `API request failed with status ${response.status}`,
    );
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filenameMatch = disposition.match(/filename="([^"]+)"/);
  const filename = filenameMatch?.[1] ?? "informe.pdf";

  return { blob, filename };
}

export async function fetchCajas(): Promise<Caja[]> {
  return apiGet<Caja[]>("/api/v1/cajas");
}

export async function getCajas(): Promise<Caja[]> {
  return fetchCajas();
}

export async function listCajasConfig(): Promise<Caja[]> {
  return apiGet<Caja[]>("/api/v1/cajas/config");
}

export async function createCaja(nombre: string): Promise<Caja> {
  return apiPost<Caja>("/api/v1/cajas/config", { nombre });
}

export async function archiveCaja(cajaId: number): Promise<Caja> {
  return apiPost<Caja>(`/api/v1/cajas/${cajaId}/archive`, {});
}

export async function unarchiveCaja(cajaId: number): Promise<Caja> {
  return apiPost<Caja>(`/api/v1/cajas/${cajaId}/unarchive`, {});
}

export async function fetchCajaSaldo(cajaId: number): Promise<CajaSaldo> {
  return apiGet<CajaSaldo>(`/api/v1/cajas/${cajaId}/saldo`);
}

export async function fetchSaldoGeneral(): Promise<CajaSaldoGeneral> {
  return apiGet<CajaSaldoGeneral>("/api/v1/cajas/saldo-general");
}

export type MovimientoFiltros = {
  moneda?: "ARS" | "USD" | "";
  fecha_desde?: string;
  fecha_hasta?: string;
};

export async function fetchMovimientos(
  cajaId: number,
  page: number,
  filtros?: MovimientoFiltros,
): Promise<PaginatedMovimientos> {
  const params = new URLSearchParams({ page: String(page) });
  if (filtros?.moneda) params.set("moneda", filtros.moneda);
  if (filtros?.fecha_desde) params.set("fecha_desde", filtros.fecha_desde);
  if (filtros?.fecha_hasta) params.set("fecha_hasta", filtros.fecha_hasta);
  return apiGet<PaginatedMovimientos>(
    `/api/v1/cajas/${cajaId}/movimientos?${params.toString()}`,
  );
}

export async function createMovimiento(
  cajaId: number,
  payload: CreateMovimientoPayload,
): Promise<MovimientoCreateResponse> {
  return apiPost<MovimientoCreateResponse>(
    `/api/v1/cajas/${cajaId}/movimientos`,
    payload,
  );
}

export async function updateMovimiento(
  cajaId: number,
  movimientoId: number,
  payload: UpdateMovimientoPayload,
): Promise<Movimiento> {
  return apiPatch<Movimiento>(
    `/api/v1/cajas/${cajaId}/movimientos/${movimientoId}`,
    payload,
  );
}

export async function deleteMovimiento(
  cajaId: number,
  movimientoId: number,
): Promise<void> {
  return apiDelete(`/api/v1/cajas/${cajaId}/movimientos/${movimientoId}`);
}

export async function fetchPlazosFijosResumen(
  cajaId: number,
): Promise<PlazosFijosResumen> {
  return apiGet<PlazosFijosResumen>(
    `/api/v1/cajas/${cajaId}/plazos-fijos/resumen`,
  );
}

export async function fetchPlazosFijos(
  cajaId: number,
  page: number,
): Promise<PaginatedPlazosFijos> {
  return apiGet<PaginatedPlazosFijos>(
    `/api/v1/cajas/${cajaId}/plazos-fijos?page=${page}`,
  );
}

export async function createPlazoFijo(
  cajaId: number,
  payload: CreatePlazoFijoPayload,
): Promise<PlazoFijo> {
  return apiPost<PlazoFijo>(`/api/v1/cajas/${cajaId}/plazos-fijos`, payload);
}

export async function updatePlazoFijo(
  cajaId: number,
  plazoFijoId: number,
  payload: UpdatePlazoFijoPayload,
): Promise<PlazoFijo> {
  return apiPatch<PlazoFijo>(
    `/api/v1/cajas/${cajaId}/plazos-fijos/${plazoFijoId}`,
    payload,
  );
}

export async function deletePlazoFijo(
  cajaId: number,
  plazoFijoId: number,
): Promise<void> {
  return apiDelete(`/api/v1/cajas/${cajaId}/plazos-fijos/${plazoFijoId}`);
}

// Calendar helpers. "Hoy" is always the calendar date in Argentina (the business rule),
// regardless of the browser time zone. The server stays authoritative for validations.

export const AR_TIME_ZONE = "America/Argentina/Buenos_Aires";

const arDateParts = new Intl.DateTimeFormat("en-CA", {
  timeZone: AR_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** Today in Argentina as YYYY-MM-DD. */
export function hoyAr(now: Date = new Date()): string {
  return arDateParts.format(now);
}

/** Adds `days` calendar days to a YYYY-MM-DD string. */
export function addDays(isoDate: string, days: number): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  const result = new Date(Date.UTC(year, month - 1, day + days));
  return result.toISOString().slice(0, 10);
}

/** Tomorrow in Argentina as YYYY-MM-DD (minimum allowed fecha de liquidación). */
export function mananaAr(now: Date = new Date()): string {
  return addDays(hoyAr(now), 1);
}

/**
 * A cheque can only be settled once its fecha de liquidación has arrived (today in
 * Argentina or earlier). The server enforces the same rule; this only drives the UI.
 */
export function llegoFechaLiquidacion(
  fechaLiquidacion: string | null,
  now: Date = new Date(),
): boolean {
  return fechaLiquidacion !== null && fechaLiquidacion <= hoyAr(now);
}

/** YYYY-MM-DD → dd/mm/yyyy without any time-zone shift. */
export function formatFechaIso(isoDate: string | null): string {
  if (!isoDate) {
    return "—";
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate);
  if (!match) {
    return isoDate;
  }
  return `${match[3]}/${match[2]}/${match[1]}`;
}

/** ISO date-time → dd/mm/yyyy in Argentina time. */
export function formatFechaCarga(isoDateTime: string): string {
  const date = new Date(isoDateTime);
  if (Number.isNaN(date.getTime())) {
    return isoDateTime;
  }
  return date.toLocaleDateString("es-AR", {
    timeZone: AR_TIME_ZONE,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

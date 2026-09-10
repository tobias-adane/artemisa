import type {
  ActivityLogEntry,
  EmergencyContact,
  EmergencyContactCreatePayload,
  SpaceCreatePayload,
  SpacePublic,
  SpaceTestConnectionResult,
  User,
} from '@/lib/types/artemisa-types';

/**
 * Cliente HTTP del backend Python (ver backend/api/routes.py, backend/main.py).
 * Sin Clerk todavía no hay sesión real — GET /me resuelve el usuario de
 * demo sembrado en InMemoryStore (ver backend/main.py DEMO_USER_ID).
 *
 * Cada función devuelve un ApiResult en vez de tirar: así el caller
 * decide si cae a frontend/lib/mock-data.ts cuando el backend Python
 * no está corriendo (por ejemplo, en un deploy solo-frontend).
 */
const API_URL = process.env.NEXT_PUBLIC_ARTEMISA_API_URL || 'http://localhost:8000';

/** Espejo de DEMO_USER_ID en backend/main.py — placeholder hasta que haya Clerk real. */
export const DEMO_USER_ID = '00000000-0000-0000-0000-000000000001';

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    });
    if (!res.ok) {
      return { ok: false, error: `${res.status} ${res.statusText}` };
    }
    return { ok: true, data: (await res.json()) as T };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : 'network error' };
  }
}

export function getMe() {
  return request<User>('/me');
}

export function listSpaces(userId: string) {
  return request<SpacePublic[]>(`/spaces?user_id=${encodeURIComponent(userId)}`);
}

export function createSpace(payload: SpaceCreatePayload) {
  return request<SpacePublic>('/spaces', { method: 'POST', body: JSON.stringify(payload) });
}

export function testCameraConnection(payload: SpaceCreatePayload) {
  return request<SpaceTestConnectionResult>('/spaces/test-connection', { method: 'POST', body: JSON.stringify(payload) });
}

export function listActivity(userId: string, limit = 50) {
  return request<ActivityLogEntry[]>(`/activity?user_id=${encodeURIComponent(userId)}&limit=${limit}`);
}

export function listContacts(userId: string) {
  return request<EmergencyContact[]>(`/contacts?user_id=${encodeURIComponent(userId)}`);
}

export function createContact(payload: EmergencyContactCreatePayload) {
  return request<EmergencyContact>('/contacts', { method: 'POST', body: JSON.stringify(payload) });
}

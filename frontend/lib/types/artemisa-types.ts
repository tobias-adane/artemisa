/**
 * Artemisa — Tipos TypeScript (sincronizados con Pydantic backend)
 *
 * Espejan 1:1 backend/artemisa_models.py y docs/ARTEMISA_03_DATOS.md.
 * Si cambia el schema, se tocan los tres a la vez + la migración de
 * Supabase correspondiente.
 */

// ============================================================
// ENUMS
// ============================================================

export type Classification = 'normal' | 'attention' | 'emergency';

export type AlertLevel = 1 | 2 | 3 | 4;

export type ActionLevel = 'informar' | 'alertar' | 'contactar' | 'emergencia';

export type SpaceStatus = 'active' | 'offline' | 'pending';

export type CameraType = 'rtsp';

export type ContactRelationship =
  | 'spouse_partner'
  | 'parent'
  | 'sibling'
  | 'friend'
  | 'neighbor'
  | 'other';

export type HomeType = 'apartment' | 'house' | 'small_business';

export type EventType =
  | 'thread_logged'
  | 'dispatch_triggered'
  | 'dispatch_cancelled'
  | 'space_connected'
  | 'space_went_offline'
  | 'space_reconnected';

export type AlertSensitivity = 'low' | 'balanced' | 'high';

// ============================================================
// USERS
// ============================================================

export interface User {
  id: string;
  email: string;
  name: string;
  timezone: string; // default: 'America/Argentina/Buenos_Aires'
  account_type: string; // default: 'beta'
  home_type: HomeType | null;
  area_type: string | null;
  has_children: boolean;
  /** Texto libre acumulativo — la rutina del hogar. Input más
   * importante de la Contextual Intelligence. */
  custom_instructions: string | null;
  created_at: string;
  updated_at: string;
}

// ============================================================
// SPACES (cámara + espacio, 1:1 en el MVP)
// ============================================================

/**
 * Shape completo tal como lo persiste el backend. NUNCA se envía
 * completo al cliente — camera_url (RTSP) es exclusivo del backend.
 * Cualquier query/response hacia el frontend debe usar SpacePublic.
 */
export interface Space {
  id: string;
  user_id: string;
  name: string;
  camera_url: string; // RTSP — solo backend, NUNCA exponer al cliente
  camera_type: CameraType;
  status: SpaceStatus;
  last_frame: string | null;
  last_update: string;
}

/** Lo que efectivamente puede llegar al cliente — sin camera_url.
 * Proyectar explícitamente estas columnas en cualquier select de
 * Supabase hecho desde el frontend. */
export type SpacePublic = Omit<Space, 'camera_url'>;

// ============================================================
// LAYERS (Paso 2a — Descripción, puramente factual)
// ============================================================

/**
 * SIN classification: Paso 2a solo describe, nunca clasifica.
 * Ver docs/ARTEMISA_03_DATOS.md sección 3.
 */
export interface Layer {
  id: string;
  space_id: string;
  /** Descripción factual generada por GPT-4o mini — NUNCA imagen. */
  description: string;
  confidence: number | null;
  timestamp: string;
  metadata: Record<string, unknown>;
}

// ============================================================
// THREADS (Paso 2b análisis / Paso 3 razonamiento)
// ============================================================

export interface Thread {
  id: string;
  space_id: string;
  layers: string[];
  /** La narrativa humana del evento — lo que se muestra en Activity. */
  narrative: string;
  classification: Classification;
  /** Certeza de la clasificación. attention con confidence < 0.6
   * escala a Paso 3. */
  confidence: number;
  /** Gravedad SI la clasificación es correcta — decide Nivel 2 vs
   * Nivel 3 dentro de attention. Distinto de confidence. */
  severity_score: number;
  /** Por qué se llegó a esta clasificación, en voz humana — feed de
   * "Why this mattered". Nunca el reasoning técnico de Paso 3. */
  reasoning: string;
  alert_level: AlertLevel;
  action: ActionLevel | null;
  start_time: string;
  /** null mientras el thread sigue abierto (ventana de continuidad). */
  end_time: string | null;
  escalated_to_reasoning: boolean;
}

/**
 * Mapeo determinístico classification -> (alert_level, action).
 * Espejo de resolve_action_level() en artemisa_models.py — ver
 * docs/ARTEMISA_03_DATOS.md sección 4 para la explicación completa.
 *
 * El exhaustiveness check con `never` hace que TypeScript falle en
 * compilación si se agrega una clasificación nueva sin actualizar
 * esta función.
 */
export const ATTENTION_CONTACT_THRESHOLD = 0.7;

export function resolveActionLevel(
  classification: Classification,
  severityScore: number,
  severityHigh?: boolean
): { alertLevel: AlertLevel; action: ActionLevel } {
  switch (classification) {
    case 'normal':
      return { alertLevel: 1, action: 'informar' };
    case 'attention':
      return severityScore >= ATTENTION_CONTACT_THRESHOLD
        ? { alertLevel: 3, action: 'contactar' }
        : { alertLevel: 2, action: 'alertar' };
    case 'emergency':
      return severityHigh
        ? { alertLevel: 4, action: 'emergencia' }
        : { alertLevel: 3, action: 'contactar' };
    default: {
      const _exhaustive: never = classification;
      throw new Error(`Clasificación desconocida: ${_exhaustive}`);
    }
  }
}

// ============================================================
// EMERGENCY CONTACTS
// ============================================================

export interface EmergencyContact {
  id: string;
  user_id: string;
  name: string;
  /** Formato E.164, ej. +5491122334455. Default de país: +54. */
  phone: string;
  relationship: ContactRelationship;
  /** Orden de llamado. 1 = primero. El 911 siempre antecede a esta
   * lista, no es una fila acá. */
  priority: number;
  /** True solo después de confirmación vía Twilio. Un contacto no
   * confirmado no se llama. */
  confirmed: boolean;
}

// ============================================================
// USER PREFERENCES
// ============================================================

export interface UserPreferences {
  id: string;
  user_id: string;
  alert_sensitivity: AlertSensitivity;
  /** Ventana de cancelación antes del dispatch de Nivel 4. Default 30. */
  cancel_timer_seconds: number;
  /** Ventana de cancelación antes del dispatch de Nivel 3. Default 90. */
  contact_cancel_timer_seconds: number;
  auto_call_enabled: boolean;
  do_not_disturb_start: string | null; // "HH:MM:SS"
  do_not_disturb_end: string | null;
}

// ============================================================
// CONVERSATIONS (Chat / Natural Interaction)
// ============================================================

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  messages: ChatMessage[];
  /** Contexto de estado del hogar (threads recientes) — NO es
   * historial de chat, eso va en `messages`. */
  context: Record<string, unknown>;
}

// ============================================================
// ACTIVITY LOG
// ============================================================

export interface ActivityLogEntry {
  id: string;
  user_id: string;
  thread_id: string | null;
  event_type: EventType;
  title: string;
  description: string;
  /** Nombre del space, ej. 'living room'. */
  location: string | null;
  /** SOLO imágenes subidas explícitamente por el usuario. NUNCA un
   * frame de cámara. */
  image_url: string | null;
  timestamp: string;
}

// ============================================================
// DISPATCH LOGS (Paso 4 — auditoría de Twilio)
// ============================================================

export interface DispatchLog {
  id: string;
  thread_id: string;
  user_id: string;
  action: 'call_user' | 'call_contacts' | 'call_911';
  twilio_sid: string;
  status: string;
  created_at: string;
}

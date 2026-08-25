import type {
  ActivityLogEntry,
  EmergencyContact,
  SpacePublic,
  Thread,
  User,
} from '@/lib/types/artemisa-types';

/**
 * Datos de ejemplo — familia clásica argentina (doc 01, sección 9).
 * Reemplazar por datos reales de Supabase/Clerk cuando estén conectados.
 */

export const mockUser: User = {
  id: 'user-tomas',
  email: 'tomas@artemisa.app',
  name: 'Tomás Vidal',
  timezone: 'America/Argentina/Buenos_Aires',
  account_type: 'beta',
  home_type: 'house',
  area_type: null,
  has_children: true,
  custom_instructions:
    'La mucama viene los martes a las 10am. Nadie debería estar en casa después de las 23hs entre semana.',
  created_at: '2026-03-01T00:00:00Z',
  updated_at: '2026-06-27T00:00:00Z',
};

export const mockSpaces: SpacePublic[] = [
  { id: 'living', user_id: mockUser.id, name: 'Living', camera_type: 'rtsp', status: 'active', last_frame: '2026-06-27T21:50:00Z', last_update: '2026-06-27T21:50:00Z' },
  { id: 'kitchen', user_id: mockUser.id, name: 'Cocina', camera_type: 'rtsp', status: 'active', last_frame: '2026-06-27T21:45:00Z', last_update: '2026-06-27T21:45:00Z' },
  { id: 'entrance', user_id: mockUser.id, name: 'Entrada', camera_type: 'rtsp', status: 'offline', last_frame: '2026-06-27T21:38:00Z', last_update: '2026-06-27T21:38:00Z' },
  { id: 'bedroom', user_id: mockUser.id, name: 'Dormitorio', camera_type: 'rtsp', status: 'active', last_frame: '2026-06-27T21:49:00Z', last_update: '2026-06-27T21:49:00Z' },
  { id: 'backyard', user_id: mockUser.id, name: 'Patio', camera_type: 'rtsp', status: 'active', last_frame: '2026-06-27T21:44:00Z', last_update: '2026-06-27T21:44:00Z' },
  { id: 'office', user_id: mockUser.id, name: 'Oficina', camera_type: 'rtsp', status: 'active', last_frame: '2026-06-27T21:40:00Z', last_update: '2026-06-27T21:40:00Z' },
];

export const mockThreads: Thread[] = [
  {
    id: 'th-1', space_id: 'entrance',
    layers: [],
    narrative: 'Llegó un paquete a la entrada. Nadie lo retiró todavía.',
    classification: 'attention', confidence: 0.78, severity_score: 0.4,
    reasoning: 'No había ninguna entrega esperada según lo que nos contaste. No es una situación de riesgo, pero vale la pena que sepas que quedó ahí.',
    alert_level: 2, action: 'alertar',
    start_time: '2026-06-27T14:30:00Z', end_time: '2026-06-27T14:31:00Z',
    escalated_to_reasoning: false,
  },
  {
    id: 'th-2', space_id: 'living',
    layers: [],
    narrative: 'Llegó tu mujer. Entró con las compras.',
    classification: 'normal', confidence: 0.95, severity_score: 0.05,
    reasoning: 'Coincide con su horario habitual de vuelta los viernes.',
    alert_level: 1, action: 'informar',
    start_time: '2026-06-27T18:15:00Z', end_time: '2026-06-27T18:16:00Z',
    escalated_to_reasoning: false,
  },
];

export const mockActivity: ActivityLogEntry[] = [
  {
    id: 'act-1', user_id: mockUser.id, thread_id: 'th-1', event_type: 'thread_logged',
    title: 'Llegó un paquete', description: 'Un cadete dejó una caja en el felpudo y se fue. Todavía está esperando ahí, en la puerta principal.',
    location: 'Entrada', image_url: null, timestamp: '2026-06-27T14:30:00Z',
  },
  {
    id: 'act-2', user_id: mockUser.id, thread_id: 'th-2', event_type: 'thread_logged',
    title: 'Llegó tu mujer', description: 'Llegó a eso de las 18:15 con las compras. Entró en unos diez minutos. Una tarde bastante típica.',
    location: 'Living', image_url: null, timestamp: '2026-06-27T18:15:00Z',
  },
  {
    id: 'act-3', user_id: mockUser.id, thread_id: null, event_type: 'space_went_offline',
    title: 'La cámara de Entrada perdió conexión', description: 'Sin señal hace unos minutos. El resto de tus espacios sigue funcionando con normalidad.',
    location: 'Entrada', image_url: null, timestamp: '2026-06-27T21:38:00Z',
  },
];

export const mockEmergencyContacts: EmergencyContact[] = [
  { id: 'ec-1', user_id: mockUser.id, name: 'Valentina Vidal', phone: '+5491122334455', relationship: 'spouse_partner', priority: 1, confirmed: true },
  { id: 'ec-2', user_id: mockUser.id, name: 'Marcos Ferrari', phone: '+5491133445566', relationship: 'neighbor', priority: 2, confirmed: true },
];

export const STATUS_LABEL: Record<string, string> = {
  normal: 'Tranquilo',
  attention: 'Atención',
  emergency: 'Emergencia',
};

export const STATUS_COLOR_VAR: Record<string, string> = {
  normal: 'var(--status-normal)',
  attention: 'var(--status-attention)',
  emergency: 'var(--status-emergency)',
};

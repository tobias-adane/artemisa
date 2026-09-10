import type { Thread } from '@/lib/types/artemisa-types';

/** CLAUDE.md §9 — texto de "Artemisa actuó" en ReasoningThread, en voz humana. */
export function actionText(thread: Thread): string {
  const time = new Date(thread.start_time).toLocaleTimeString('es-AR', {
    hour: '2-digit',
    minute: '2-digit',
  });
  switch (thread.action) {
    case 'informar':
      return 'Te mandé una notificación.';
    case 'alertar':
      return `Te llamé a las ${time}.`;
    case 'contactar':
      return 'Te llamé. Como no atendiste, llamé a tus contactos de emergencia.';
    case 'emergencia':
      return 'Te llamé. Llamé a tus contactos. Contacté al servicio de emergencias.';
    default:
      return '';
  }
}

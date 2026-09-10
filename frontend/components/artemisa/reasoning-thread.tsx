import { StatusDot } from '@/components/artemisa/status-dot';
import { actionText } from '@/lib/action-text';
import type { Layer, Thread } from '@/lib/types/artemisa-types';

/**
 * "Cómo llegué a esta decisión" — CLAUDE.md §9. Thread de 4 nodos
 * conectados por una línea vertical. El nodo 3 ("Artemisa verificó dos
 * veces") solo aparece si el thread escaló a razonamiento (Paso 3).
 */
export function ReasoningThread({ thread, layers }: { thread: Thread; layers: Layer[] }) {
  const firstLayer = layers[0];
  const showVerification = thread.escalated_to_reasoning && !!thread.reasoning;

  const nodes: { label: string; dotColor: string; content: React.ReactNode; bold?: boolean }[] = [
    {
      label: 'Artemisa notó algo',
      dotColor: thread.classification === 'emergency' ? 'var(--status-emergency)' : '#a3a3a3',
      content: firstLayer ? (
        <>
          <p>{firstLayer.description}</p>
          <span className="text-[11px] text-muted-foreground">
            {new Date(firstLayer.timestamp).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
          </span>
        </>
      ) : null,
    },
    { label: 'Artemisa analizó el contexto', dotColor: '#a3a3a3', content: <p>{thread.narrative}</p> },
    ...(showVerification ? [{ label: 'Artemisa verificó dos veces', dotColor: '#a3a3a3', content: <p>{thread.reasoning}</p> }] : []),
    { label: 'Artemisa actuó', dotColor: '#0a0a0a', content: <p className="font-semibold">{actionText(thread)}</p>, bold: true },
  ];

  return (
    <div className="flex flex-col">
      {nodes.map((n, i) => (
        <div key={i} className="flex gap-3">
          <div className="flex flex-col items-center">
            <StatusDot color={n.dotColor} className="mt-1" />
            {i < nodes.length - 1 && <div className="mt-1 w-px flex-1 bg-border" style={{ minHeight: 22 }} />}
          </div>
          <div className="pb-4">
            <div className="text-[11px] font-medium text-muted-foreground">{n.label}</div>
            <div className="mt-1 text-[13px] leading-relaxed text-foreground">{n.content}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

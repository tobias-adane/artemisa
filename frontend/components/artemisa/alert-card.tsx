import Link from 'next/link';
import type { Thread } from '@/lib/types/artemisa-types';

/**
 * Alert card — Nivel 2 (Attention). Doc 04, "lo que falta construir" #1.
 * Ícono de estado + título + descripción. Sin dispatch, sin llamada —
 * solo informativo. Aparece en Home y Activity.
 */
export function AlertCard({ thread, spaceName }: { thread: Thread; spaceName: string }) {
  if (thread.classification !== 'attention') return null;

  return (
    <Link
      href="/activity"
      className="flex items-start gap-3.5 rounded-3xl border border-border bg-background p-4 transition-colors hover:border-[#d4d4d4]"
    >
      <span
        className="mt-1.5 h-2.5 w-2.5 flex-none rounded-full"
        style={{ background: 'var(--status-attention)', boxShadow: '0 0 0 4px rgba(208,135,0,0.18)' }}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <div className="text-sm font-semibold text-foreground">{thread.narrative}</div>
          <span className="flex-none text-[11px] text-muted-foreground">{spaceName}</span>
        </div>
        <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{thread.reasoning}</p>
      </div>
    </Link>
  );
}

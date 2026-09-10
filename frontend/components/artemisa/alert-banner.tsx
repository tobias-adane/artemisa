import { Bell, TriangleAlert } from 'lucide-react';
import type { Classification } from '@/lib/types/artemisa-types';
import { STATUS_COLOR_VAR, STATUS_LABEL } from '@/lib/mock-data';

/**
 * Alert card Nivel 2 (Attention) — CLAUDE.md §13.1: card blanca simple,
 * ícono de estado + título + descripción, sin dispatch. Reusa el mismo
 * card para 'emergency' (Nivel 4 ya despachado) mostrando el ícono rojo,
 * pero nunca dispara acciones desde acá — eso corre server-side (Paso 4).
 */
export function AlertBanner({
  title,
  description,
  classification = 'attention',
  className = '',
}: {
  title: string;
  description: string;
  classification?: Classification;
  className?: string;
}) {
  const color = STATUS_COLOR_VAR[classification];
  const Icon = classification === 'emergency' ? TriangleAlert : Bell;

  return (
    <div className={`flex items-start gap-3 rounded-3xl border border-border bg-background p-4 ${className}`}>
      <Icon className="mt-0.5 h-4 w-4 flex-none" style={{ color }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[14.5px] font-semibold leading-tight">{title}</span>
          <span
            className="flex-none rounded-full px-2 py-0.5 text-[11px] font-medium"
            style={{ boxShadow: 'inset 0 0 0 1px #d4d4d4', color }}
          >
            {STATUS_LABEL[classification]}
          </span>
        </div>
        <p className="mt-1 text-[13.5px] leading-relaxed text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

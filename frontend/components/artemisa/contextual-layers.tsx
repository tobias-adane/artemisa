import type { Layer } from '@/lib/types/artemisa-types';

/**
 * "Hilo contextual" — CLAUDE.md §9. Feed cronológico simple de los
 * layers que construyeron el thread: descripción, hora exacta, espacio.
 */
export function ContextualLayers({ layers, spaceName }: { layers: Layer[]; spaceName: string }) {
  return (
    <div className="flex flex-col gap-3.5">
      {layers.map((l) => (
        <div key={l.id} className="flex items-start gap-3">
          <span className="mt-0.5 flex-none text-[11px] font-medium tabular-nums text-muted-foreground">
            {new Date(l.timestamp).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] leading-relaxed text-foreground">{l.description}</p>
            <span className="text-[11px] text-muted-foreground">{spaceName}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

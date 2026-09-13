import { X } from 'lucide-react';
import type { SpacePublic } from '@/lib/types/artemisa-types';

/**
 * Miniatura flotante del espacio enfocado — aparece arriba del composer
 * cuando se elige un espacio en "Espacios" (mismo tratamiento visual
 * que una foto adjunta: esquinas redondeadas, × flotante). Distinto de
 * un chip de texto — no hay prefijo en el mensaje, cambia el subtítulo
 * y las quick actions de Home mientras está activo.
 */
export function SpaceFocusCard({ space, onClear }: { space: SpacePublic; onClear: () => void }) {
  return (
    <div className="flex w-full items-start justify-end">
      <div className="relative h-20 w-20 flex-none animate-pop-in rounded-[22px] border border-border bg-muted">
        <button
          onClick={onClear}
          title="Cerrar"
          className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full border border-border bg-background text-foreground shadow-[0_1px_4px_rgba(0,0,0,0.18)] hover:bg-secondary"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

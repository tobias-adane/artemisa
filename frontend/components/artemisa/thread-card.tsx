import { EllipsisVertical, MessageCircle, Phone } from 'lucide-react';
import { ReasoningThread } from '@/components/artemisa/reasoning-thread';
import { ContextualLayers } from '@/components/artemisa/contextual-layers';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { STATUS_COLOR_VAR, STATUS_LABEL } from '@/lib/mock-data';
import type { ActivityLogEntry, Classification, Layer, SpacePublic, Thread } from '@/lib/types/artemisa-types';
import type { Dictionary } from '@/lib/i18n/es';
import type { LucideIcon } from 'lucide-react';

type MoreItem = { key: 'reasoning' | 'thread' | 'share' | 'comments'; icon: LucideIcon; label: string };

/** Card de un evento del feed de Activity — extraído para reutilización (CLAUDE.md §8). */
export function ThreadCard({
  entry,
  thread,
  threadLayers,
  threadSpace,
  moreItems,
  moreOpen,
  onToggleMore,
  onCloseMore,
  panel,
  onSelectPanel,
  dict,
}: {
  entry: ActivityLogEntry;
  thread?: Thread;
  threadLayers: Layer[];
  threadSpace?: SpacePublic;
  moreItems: MoreItem[];
  moreOpen: boolean;
  onToggleMore: () => void;
  onCloseMore: () => void;
  panel: 'reasoning' | 'thread' | undefined;
  onSelectPanel: (key: 'reasoning' | 'thread') => void;
  dict: Dictionary['activity'];
}) {
  const classification: Classification = thread?.classification ?? 'normal';

  return (
    <div className="flex animate-fade-up gap-5">
      <span className="h-fit flex-none rounded-full border border-[#d4d4d4] px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
        {new Date(entry.timestamp).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false })}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <div className="text-[15.5px] font-semibold">{entry.title}</div>
            <p className="mt-1.5 text-[13.5px] leading-relaxed text-muted-foreground">{entry.description}</p>
          </div>
          <div className="relative flex-none">
            <DropdownMenu open={moreOpen} onOpenChange={(open) => (open ? onToggleMore() : onCloseMore())}>
              <DropdownMenuTrigger asChild>
                <button
                  title={dict.moreTooltip}
                  className="flex h-4 w-4 items-center justify-center text-muted-foreground hover:text-foreground"
                >
                  <EllipsisVertical className="h-4 w-4" />
                  <span className="sr-only">{dict.moreTooltip}</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-[214px]">
                <DropdownMenuLabel>{dict.moreOptions}</DropdownMenuLabel>
                {moreItems.map((mi) => (
                  <DropdownMenuItem
                    key={mi.key}
                    onClick={() => {
                      if (mi.key === 'reasoning' || mi.key === 'thread') onSelectPanel(mi.key);
                    }}
                  >
                    <mi.icon className="h-4 w-4 flex-none" />
                    <span className="flex-1">{mi.label}</span>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <div className="mt-3.5 aspect-[16/10] w-full rounded-3xl border border-border bg-secondary" />

        {panel === 'reasoning' && (
          <div className="mt-3">
            <div className="mb-2 text-xs font-medium text-muted-foreground">{dict.whyMattered}</div>
            {thread ? (
              <ReasoningThread thread={thread} layers={threadLayers} />
            ) : (
              <p className="max-w-[520px] text-[12.5px] leading-relaxed text-muted-foreground">{dict.defaultReasoning}</p>
            )}
          </div>
        )}

        {panel === 'thread' && thread && threadSpace && threadLayers.length > 0 && (
          <div className="mt-3">
            <div className="mb-2 text-xs font-medium text-muted-foreground">{dict.contextualThreadTitle}</div>
            <ContextualLayers layers={threadLayers} spaceName={threadSpace.name} />
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-2.5">
          <div className="inline-flex items-center rounded-full px-3 py-1.5" style={{ boxShadow: 'inset 0 0 0 1px #d4d4d4' }}>
            <span className="text-xs font-medium" style={{ color: STATUS_COLOR_VAR[classification] }}>
              {STATUS_LABEL[classification]}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button className="inline-flex h-8 items-center gap-1.5 rounded-full border border-border px-3 text-[13px] font-medium hover:bg-secondary">
              <Phone className="h-3.5 w-3.5" /> {dict.requestHelp}
            </button>
            <button className="inline-flex h-8 items-center gap-1.5 rounded-full bg-primary px-3 text-[13px] font-medium text-primary-foreground hover:bg-primary/90">
              <MessageCircle className="h-3.5 w-3.5" /> {dict.askAnything}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

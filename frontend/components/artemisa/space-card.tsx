'use client';

import Link from 'next/link';
import { MoreHorizontal, RefreshCw } from 'lucide-react';
import type { SpacePublic } from '@/lib/types/artemisa-types';

export function SpaceCard({
  space,
  moreTooltip,
  offline = false,
  reconnecting = false,
  onReconnect,
  disconnectedLabel,
  reconnectingLabel,
  reconnectLabel,
}: {
  space: SpacePublic;
  moreTooltip: string;
  offline?: boolean;
  reconnecting?: boolean;
  onReconnect?: () => void;
  disconnectedLabel?: string;
  reconnectingLabel?: string;
  reconnectLabel?: string;
}) {
  return (
    <Link href={`/spaces/${space.id}`} className="flex aspect-[4/3] flex-col rounded-3xl border border-border bg-secondary p-1">
      <div className="relative flex min-h-0 flex-1 flex-col justify-end rounded-[18px] border border-border bg-secondary p-2">
        {offline && onReconnect && (
          <button
            onClick={(e) => {
              e.preventDefault();
              onReconnect();
            }}
            disabled={reconnecting}
            className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 rounded-2xl border border-border bg-background px-3.5 py-2 text-xs font-medium text-foreground shadow-sm"
          >
            <RefreshCw className={`h-3 w-3 ${reconnecting ? 'animate-spin' : ''}`} />
            {reconnecting ? reconnectingLabel : reconnectLabel}
          </button>
        )}
        <div className="flex items-center gap-2 rounded-xl px-1.5 py-1">
          <span className="flex-1 truncate text-sm">{offline ? disconnectedLabel : space.name}</span>
          <button
            title={moreTooltip}
            onClick={(e) => e.preventDefault()}
            className="flex h-4 w-4 flex-none items-center justify-center text-muted-foreground hover:text-foreground"
          >
            <MoreHorizontal className="h-4 w-4" />
          </button>
        </div>
      </div>
    </Link>
  );
}

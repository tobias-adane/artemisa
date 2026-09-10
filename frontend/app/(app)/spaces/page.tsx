'use client';

import { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { PageHeader } from '@/components/artemisa/page-header';
import { SpaceCard } from '@/components/artemisa/space-card';
import { mockSpaces } from '@/lib/mock-data';
import { useI18n } from '@/lib/i18n/context';
import { useBackendUser } from '@/lib/use-backend-user';
import { listSpaces } from '@/lib/api';
import type { SpacePublic } from '@/lib/types/artemisa-types';

export default function SpacesPage() {
  const { dict } = useI18n();
  const { userId, available } = useBackendUser();
  const [spaces, setSpaces] = useState<SpacePublic[]>(mockSpaces);
  const [reconnected, setReconnected] = useState<Record<string, boolean>>({});
  const [reconnecting, setReconnecting] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!available) return;
    let cancelled = false;
    listSpaces(userId).then((res) => {
      if (!cancelled && res.ok) setSpaces(res.data);
    });
    return () => {
      cancelled = true;
    };
  }, [available, userId]);

  function reconnect(id: string) {
    setReconnecting((r) => ({ ...r, [id]: true }));
    setTimeout(() => {
      setReconnecting((r) => ({ ...r, [id]: false }));
      setReconnected((r) => ({ ...r, [id]: true }));
    }, 1300);
  }

  return (
    <div>
      <PageHeader title={dict.spaces.pageTitle} />
      <main className="mx-auto max-w-6xl px-6 py-8 sm:px-14">
        <div className="mb-6">
          <div className="mb-1.5 text-sm text-muted-foreground">{dict.spaces.subtitle}</div>
          <h1 className="heading-display text-3xl">{dict.spaces.headline}</h1>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {spaces.map((space) => (
            <SpaceCard
              key={space.id}
              space={space}
              moreTooltip={dict.spaces.moreTooltip}
              offline={space.status === 'offline' && !reconnected[space.id]}
              reconnecting={!!reconnecting[space.id]}
              onReconnect={() => reconnect(space.id)}
              disconnectedLabel={dict.spaces.disconnected}
              reconnectingLabel={dict.spaces.reconnecting}
              reconnectLabel={dict.spaces.reconnect}
            />
          ))}
        </div>

        <button className="mt-6 inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary">
          <Plus className="h-3.5 w-3.5" /> {dict.spaces.addSpace}
        </button>
      </main>
    </div>
  );
}

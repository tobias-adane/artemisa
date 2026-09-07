'use client';

import { useState } from 'react';
import Link from 'next/link';
import { MoreHorizontal, Plus, RefreshCw } from 'lucide-react';
import { PageHeader } from '@/components/artemisa/page-header';
import { mockSpaces } from '@/lib/mock-data';

export default function SpacesPage() {
  const [reconnected, setReconnected] = useState<Record<string, boolean>>({});
  const [reconnecting, setReconnecting] = useState<Record<string, boolean>>({});

  function reconnect(id: string) {
    setReconnecting((r) => ({ ...r, [id]: true }));
    setTimeout(() => {
      setReconnecting((r) => ({ ...r, [id]: false }));
      setReconnected((r) => ({ ...r, [id]: true }));
    }, 1300);
  }

  return (
    <div>
      <PageHeader title="Espacios" />
      <main className="mx-auto max-w-6xl px-6 py-8 sm:px-14">
        <div className="mb-6">
          <div className="mb-1.5 text-sm text-muted-foreground">Tu hogar, de un vistazo.</div>
          <h1 className="heading-display text-3xl">Todo está en orden en casa.</h1>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {mockSpaces.map((space) => {
            const offline = space.status === 'offline' && !reconnected[space.id];
            const busy = !!reconnecting[space.id];
            return (
              <Link
                key={space.id}
                href={`/spaces/${space.id}`}
                className="flex aspect-[4/3] flex-col rounded-3xl border border-border bg-secondary p-1"
              >
                <div className="relative flex min-h-0 flex-1 flex-col justify-end rounded-[18px] border border-border bg-secondary p-2">
                  {offline && (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        reconnect(space.id);
                      }}
                      disabled={busy}
                      className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 rounded-2xl border border-border bg-background px-3.5 py-2 text-xs font-medium text-foreground shadow-sm"
                    >
                      <RefreshCw className={`h-3 w-3 ${busy ? 'animate-spin' : ''}`} /> {busy ? 'Reconectando…' : 'Reconectar'}
                    </button>
                  )}
                  <div className="flex items-center gap-2 rounded-xl px-1.5 py-1">
                    <span className="flex-1 truncate text-sm">{offline ? 'Desconectada' : space.name}</span>
                    <button
                      title="Más"
                      onClick={(e) => e.preventDefault()}
                      className="flex h-4 w-4 flex-none items-center justify-center text-muted-foreground hover:text-foreground"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>

        <button className="mt-6 inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary">
          <Plus className="h-3.5 w-3.5" /> Agregar espacio
        </button>
      </main>
    </div>
  );
}

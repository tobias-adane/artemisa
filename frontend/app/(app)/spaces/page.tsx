'use client';

import Link from 'next/link';
import { RefreshCw } from 'lucide-react';
import { PageHeader } from '@/components/artemisa/page-header';
import { mockSpaces } from '@/lib/mock-data';

const STATUS_DOT: Record<string, string> = {
  active: 'var(--status-normal)',
  offline: 'var(--status-offline)',
  pending: 'var(--status-offline)',
};

export default function SpacesPage() {
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
            const offline = space.status === 'offline';
            return (
              <Link
                key={space.id}
                href={`/spaces/${space.id}`}
                className="relative aspect-[4/3] overflow-hidden rounded-3xl bg-secondary"
              >
                <div
                  className="absolute inset-0"
                  style={offline ? { opacity: 0.45, filter: 'grayscale(0.4)' } : undefined}
                />
                <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/55 to-transparent" />
                <span className="absolute bottom-3.5 left-4 text-xs text-white [text-shadow:0_1px_8px_rgba(0,0,0,0.3)]">
                  {space.name}
                </span>
                {offline && (
                  <span className="absolute bottom-9 left-4 text-[11px] text-white/80 [text-shadow:0_1px_8px_rgba(0,0,0,0.3)]">
                    Sin conexión hace 12 min
                  </span>
                )}
                <span
                  className="absolute right-4 top-4 h-2.5 w-2.5 rounded-full"
                  style={{ background: STATUS_DOT[space.status] }}
                />
                {offline && (
                  <span className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 rounded-2xl bg-white/95 px-3.5 py-2 text-xs font-medium text-foreground shadow-lg">
                    <RefreshCw className="h-3 w-3" /> Reconectar
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </main>
    </div>
  );
}

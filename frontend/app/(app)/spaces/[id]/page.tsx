'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ChevronLeft, MoreHorizontal, RefreshCw, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { mockActivity, mockSpaces } from '@/lib/mock-data';

export default function SpaceDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [reconnected, setReconnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);

  const space = mockSpaces.find((s) => s.id === params.id) ?? mockSpaces[0];
  const isOffline = space.status === 'offline' && !reconnected;
  const events = mockActivity.filter((a) => a.location?.toLowerCase() === space.name.toLowerCase());

  function reconnect() {
    setReconnecting(true);
    setTimeout(() => {
      setReconnecting(false);
      setReconnected(true);
    }, 1300);
  }

  return (
    <div>
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-transparent bg-background/85 px-4 backdrop-blur">
        <button onClick={() => router.push('/spaces')} className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="rounded-full border border-border bg-background px-4 py-2 text-xs font-medium">{space.name}</div>
        <button className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground">
          <MoreHorizontal className="h-4 w-4" />
        </button>
      </header>

      <main className="mx-auto max-w-2xl px-5 pb-20 pt-5">
        <div className="flex items-center gap-2.5">
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{
              background: isOffline ? 'var(--status-offline)' : 'var(--status-normal)',
              boxShadow: isOffline ? 'none' : '0 0 0 4px rgba(34,197,94,0.3)',
            }}
          />
          <span className="text-[12.5px] text-muted-foreground">
            {isOffline ? 'Desconectada · sin señal hace 12 min' : reconnecting ? 'Reconectando…' : 'Activa · última actualización hace 2 min'}
          </span>
        </div>

        <h1 className="heading-display mt-3.5 text-[28px] leading-tight">
          {isOffline ? 'Sin señal de esta cámara.' : `${space.name} está tranquilo${space.name.endsWith('a') ? 'a' : ''} ahora mismo.`}
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed text-muted-foreground">
          {isOffline
            ? 'Perdimos la conexión hace unos minutos. El resto de tus espacios sigue funcionando con normalidad — esto no es una emergencia.'
            : 'Nada fuera de lo común por acá. Todo está tal como debería estar.'}
        </p>

        {isOffline && (
          <Button onClick={reconnect} disabled={reconnecting} className="mt-4">
            <RefreshCw className={`h-3.5 w-3.5 ${reconnecting ? 'animate-spin' : ''}`} /> Reconectar
          </Button>
        )}

        <div className="mt-10">
          <div className="mb-3.5 flex items-center justify-between">
            <div className="heading-display text-xl">Actividad</div>
            <Button variant="outline" size="sm" onClick={() => router.push('/activity')}>
              Ver todo
            </Button>
          </div>
          {events.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-[#d4d4d4] px-6 py-12 text-center">
              <div className="heading-display text-lg">Todavía no pasó nada acá</div>
              <p className="mx-auto mt-2 max-w-[40ch] text-[13.5px] leading-relaxed text-muted-foreground">
                Apuntá una cámara a este espacio y Artemisa va a empezar a contar su historia.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-8">
              {events.map((e) => (
                <div key={e.id} className="flex gap-5">
                  <span className="h-fit flex-none rounded-full border border-[#d4d4d4] px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                    {new Date(e.timestamp).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false })}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-[15.5px] font-semibold">{e.title}</div>
                    <p className="mt-1.5 text-[13.5px] leading-relaxed text-muted-foreground">{e.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      <div className="fixed inset-x-0 bottom-24 z-30 flex justify-center">
        <Button onClick={() => router.push(`/home?space=${space.id}`)} className="rounded-full px-5 py-3 shadow-lg">
          <Sparkles className="h-3.5 w-3.5" /> Preguntar lo que sea
        </Button>
      </div>
    </div>
  );
}

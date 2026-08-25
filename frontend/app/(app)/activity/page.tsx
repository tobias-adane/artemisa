'use client';

import { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { PageHeader } from '@/components/artemisa/page-header';
import { mockActivity } from '@/lib/mock-data';

export default function ActivityPage() {
  const [open, setOpen] = useState<Record<string, boolean>>({});

  return (
    <div>
      <PageHeader title="Actividad" />
      <main className="mx-auto max-w-2xl px-6 pb-16 pt-8 sm:px-14">
        <div className="mb-1.5 text-sm text-muted-foreground">Todo lo que pasó en tu hogar.</div>
        <h1 className="heading-display mb-8 text-4xl">Un día tranquilo.</h1>

        {mockActivity.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-[#d4d4d4] px-6 py-14 text-center">
            <div className="heading-display text-xl">Todavía no hay actividad</div>
            <p className="mx-auto mt-2.5 max-w-[42ch] text-[13.5px] leading-relaxed text-muted-foreground">
              Apenas una cámara esté mirando un espacio, todo lo que note va a aparecer acá, en orden, lo más reciente primero.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-12">
            {mockActivity
              .slice()
              .reverse()
              .map((e) => (
                <div key={e.id} className="flex gap-5 animate-fade-up">
                  <span className="h-fit flex-none rounded-full border border-[#d4d4d4] px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                    {new Date(e.timestamp).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false })}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-[15.5px] font-semibold">{e.title}</div>
                    <p className="mt-1.5 text-[13.5px] leading-relaxed text-muted-foreground">{e.description}</p>

                    <button
                      onClick={() => setOpen((o) => ({ ...o, [e.id]: !o[e.id] }))}
                      className="mt-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-muted-foreground hover:text-foreground"
                    >
                      <ChevronRight className={`h-2.5 w-2.5 transition-transform ${open[e.id] ? 'rotate-90' : ''}`} />
                      Por qué importó
                    </button>
                    {open[e.id] && (
                      <p className="mt-2 max-w-[520px] text-[12.5px] leading-relaxed text-muted-foreground">
                        {e.location
                          ? `Registrado en ${e.location}. ${e.event_type === 'space_went_offline' ? 'Una cámara caída no es una emergencia — el resto de tu hogar sigue vigilado.' : 'No hace falta que hagas nada por ahora.'}`
                          : 'No hace falta que hagas nada por ahora.'}
                      </p>
                    )}
                  </div>
                </div>
              ))}
          </div>
        )}
      </main>
    </div>
  );
}

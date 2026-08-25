'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { mockEmergencyContacts, mockUser } from '@/lib/mock-data';

const TABS = [
  { key: 'members', label: 'Hogar' },
  { key: 'alerts', label: 'Alertas' },
  { key: 'plan', label: 'Plan' },
] as const;

type TabKey = (typeof TABS)[number]['key'];

function SettingsInner() {
  const router = useRouter();
  const search = useSearchParams();
  const initialTab = (search.get('tab') as TabKey) ?? 'members';
  const [tab, setTab] = useState<TabKey>(TABS.some((t) => t.key === initialTab) ? initialTab : 'members');
  const [channels, setChannels] = useState({ push: true, email: false, sms: true });
  const [plan, setPlan] = useState<'Founding' | 'Premium'>('Founding');

  return (
    <div>
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-transparent bg-background/85 px-4 backdrop-blur">
        <button onClick={() => router.push('/home')} className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="rounded-full bg-background px-4 py-2 text-xs font-medium">Configuración</div>
        <div className="w-8" />
      </header>

      <main className="mx-auto max-w-3xl px-6 pb-16 pt-3">
        <h1 className="heading-display mt-3 text-[31px]">{TABS.find((t) => t.key === tab)?.label}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {tab === 'members' && 'Agregá a las personas que deberían ver lo que vos ves — y decidí cuánto pueden cambiar.'}
          {tab === 'alerts' && 'Artemisa mira todo. Vos decidís qué amerita interrumpir tu día.'}
          {tab === 'plan' && 'Cambiá cuando quieras. El cambio se aplica en tu próximo ciclo de facturación.'}
        </p>

        <div className="mt-6 flex gap-2">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`h-8.5 rounded-full border px-3.5 text-[13px] font-medium ${
                tab === t.key ? 'border-[#d4d4d4] bg-secondary text-foreground' : 'border-border text-muted-foreground'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'members' && (
          <div className="mt-6 rounded-3xl border border-border bg-background p-1">
            <div className="p-4 pb-1">
              <div className="heading-display text-xl">Quién puede ver tu hogar</div>
              <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">
                Todos acá tienen la misma visibilidad sobre lo que pasa en tu hogar. Solo los dueños pueden agregar cámaras o cambiar las reglas de alerta.
              </p>
            </div>
            <div className="flex flex-col gap-2 p-2.5">
              {[
                { name: mockUser.name, email: mockUser.email, role: 'Administrador' },
                { name: 'Valentina Vidal', email: 'valentina@artemisa.app', role: 'Administrador' },
              ].map((m) => (
                <div key={m.email} className="flex items-center gap-3 rounded-2xl border border-border bg-background p-3">
                  <span className="flex h-7.5 w-7.5 flex-none items-center justify-center rounded-full bg-secondary text-xs font-semibold">
                    {m.name[0]}
                  </span>
                  <div className="min-w-[120px] flex-1">
                    <div className="text-[13.5px] font-semibold">{m.name}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">{m.email}</div>
                  </div>
                  <span className="rounded-full border border-border px-2.5 py-1 text-[11.5px] text-muted-foreground">{m.role}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'alerts' && (
          <div className="mt-6 flex flex-col gap-3.5">
            <div className="rounded-3xl border border-border bg-background p-1">
              <div className="p-4 pb-1">
                <div className="heading-display text-xl">Cómo te contactamos</div>
                <p className="mt-1.5 text-[13px] text-muted-foreground">Las emergencias siempre te llegan, incluso en horario silencioso.</p>
              </div>
              <div className="flex flex-col gap-2 p-2.5">
                {([
                  ['push', 'Push en tu teléfono', 'Llega en un par de segundos.'],
                  ['email', 'Resumen por email', 'Un resumen cada noche.'],
                  ['sms', 'Mensaje de texto', 'Solo emergencias, con costo de tu operador.'],
                ] as const).map(([key, label, hint]) => (
                  <div key={key} className="flex items-center gap-3 rounded-2xl border border-border p-3.5">
                    <div className="flex-1">
                      <div className="text-[13.5px] font-semibold">{label}</div>
                      <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div>
                    </div>
                    <Switch
                      checked={channels[key]}
                      onCheckedChange={(v) => setChannels((c) => ({ ...c, [key]: v }))}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === 'plan' && (
          <div className="mt-6 flex flex-col gap-3.5">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {([
                { name: 'Founding' as const, price: '$[PRECIO FOUNDING] ARS / mes', note: 'Precio congelado mientras dure la beta', features: ['1 cámara', 'Comprensión contextual completa', 'Contactos de emergencia', 'Memoria de actividad sin límite'] },
                { name: 'Premium' as const, price: '$[PRECIO PREMIUM] ARS / mes', note: '', features: ['Hasta [N] cámaras', 'Todo lo de Founding', 'Soporte prioritario', 'Contactos ilimitados'] },
              ]).map((p) => {
                const current = plan === p.name;
                return (
                  <div key={p.name} className={`rounded-3xl border p-4.5 ${current ? 'border-[#d4d4d4] bg-secondary/40' : 'border-border'}`}>
                    <div className="flex items-baseline justify-between gap-2">
                      <div className="heading-display text-xl">{p.name}</div>
                      {current && <span className="rounded-full bg-[#ececec] px-2.5 py-1 text-[11px] font-semibold">Actual</span>}
                    </div>
                    <div className="mt-2 text-[13px] text-muted-foreground">{p.price}</div>
                    {p.note && <div className="mt-0.5 text-[11.5px] text-muted-foreground/70">{p.note}</div>}
                    <ul className="mt-3.5 flex flex-col gap-1.5">
                      {p.features.map((f) => (
                        <li key={f} className="flex gap-2 text-[12.5px] text-foreground/80">
                          <span>·</span>
                          {f}
                        </li>
                      ))}
                    </ul>
                    <Button
                      variant={current ? 'secondary' : 'default'}
                      disabled={current}
                      onClick={() => setPlan(p.name)}
                      className="mt-4 w-full"
                    >
                      {current ? 'Plan actual' : `Cambiar a ${p.name}`}
                    </Button>
                  </div>
                );
              })}
            </div>
            <p className="text-[11.5px] text-muted-foreground">
              Contactos de emergencia configurados: {mockEmergencyContacts.length}.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={null}>
      <SettingsInner />
    </Suspense>
  );
}

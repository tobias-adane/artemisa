'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Bell,
  ChevronLeft,
  CreditCard,
  FileText,
  Folders,
  GalleryHorizontalEnd,
  Globe,
  HelpCircle,
  Lock,
  LogOut,
  PhoneCall,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  UserRound,
  Users,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { mockEmergencyContacts, mockUser } from '@/lib/mock-data';

type SectionKey =
  | 'perfil'
  | 'suscripcion'
  | 'espacios'
  | 'familia'
  | 'seguridad'
  | 'privacidad'
  | 'contactos'
  | 'instrucciones'
  | 'alertas'
  | 'idioma'
  | 'recursos'
  | 'terminos'
  | 'ayuda';

const SECTIONS: Record<
  SectionKey,
  { label: string; icon: typeof UserRound; group: 0 | 1 | 2; placeholder?: string[] }
> = {
  perfil: { label: 'Perfil', icon: UserRound, group: 0, placeholder: ['Nombre y contacto', 'Foto de perfil', 'Zona horaria'] },
  suscripcion: { label: 'Suscripción', icon: CreditCard, group: 0 },
  espacios: { label: 'Mis Espacios', icon: GalleryHorizontalEnd, group: 0, placeholder: ['Cámaras conectadas', 'Nombres de espacios'] },
  familia: { label: 'Familia', icon: Users, group: 0 },
  seguridad: { label: 'Seguridad', icon: ShieldCheck, group: 0, placeholder: ['Contraseña', 'Verificación en dos pasos', 'Sesiones activas'] },
  privacidad: { label: 'Privacidad y Datos', icon: Lock, group: 1, placeholder: ['Retención de actividad', 'Exportar mis datos', 'Eliminar cuenta'] },
  contactos: { label: 'Contactos de Emergencia', icon: PhoneCall, group: 1 },
  instrucciones: { label: 'Instrucciones del Hogar', icon: SlidersHorizontal, group: 1, placeholder: ['Rutinas y horarios habituales', 'Quién vive en la casa'] },
  alertas: { label: 'Alertas y Emergencias', icon: Bell, group: 1 },
  idioma: { label: 'Idioma', icon: Globe, group: 1, placeholder: ['Español (Argentina)'] },
  recursos: { label: 'Recursos', icon: Folders, group: 2, placeholder: ['Centro de ayuda', 'Guías de instalación'] },
  terminos: { label: 'Términos y Privacidad', icon: FileText, group: 2, placeholder: ['Términos de Servicio', 'Política de Privacidad'] },
  ayuda: { label: 'Ayuda', icon: HelpCircle, group: 2, placeholder: ['Contactar soporte', 'Preguntas frecuentes'] },
};

const GROUP_LABELS = ['Mi cuenta', 'Sistema', 'Acerca'];

function SettingsInner() {
  const router = useRouter();
  const search = useSearchParams();
  const initialTab = (search.get('tab') as SectionKey) ?? 'familia';
  const [tab, setTab] = useState<SectionKey>(SECTIONS[initialTab] ? initialTab : 'familia');
  const [channels, setChannels] = useState({ push: true, email: false, sms: true });
  const [plan, setPlan] = useState<'Founding' | 'Premium'>('Founding');
  const [contacts, setContacts] = useState(mockEmergencyContacts);
  const [newContact, setNewContact] = useState({ name: '', phone: '' });

  const current = SECTIONS[tab];

  function addContact() {
    if (!newContact.name.trim() || !newContact.phone.trim()) return;
    setContacts((c) => [
      ...c,
      {
        id: `ec-${Date.now()}`,
        user_id: mockUser.id,
        name: newContact.name.trim(),
        phone: newContact.phone.trim(),
        relationship: 'other',
        priority: c.length + 1,
        confirmed: false,
      },
    ]);
    setNewContact({ name: '', phone: '' });
  }

  return (
    <div>
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-transparent bg-background/85 px-4 backdrop-blur">
        <button onClick={() => router.push('/home')} className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="rounded-full bg-background px-4 py-2 text-xs font-medium">Configuración</div>
        <div className="w-8" />
      </header>

      <main className="mx-auto flex max-w-5xl gap-8 px-6 pb-16 pt-3 sm:px-10">
        <nav className="hidden w-[220px] flex-none flex-col gap-4 md:flex">
          {GROUP_LABELS.map((groupLabel, gi) => (
            <div key={groupLabel}>
              <div className="px-2 pb-1 text-xs text-muted-foreground">{groupLabel}</div>
              <div className="flex flex-col">
                {(Object.entries(SECTIONS) as [SectionKey, (typeof SECTIONS)[SectionKey]][])
                  .filter(([, s]) => s.group === gi)
                  .map(([key, s]) => (
                    <button
                      key={key}
                      onClick={() => setTab(key)}
                      className={`flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-sm ${
                        tab === key ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <s.icon className="h-4 w-4 flex-none" />
                      <span className="flex-1 truncate">{s.label}</span>
                    </button>
                  ))}
                {gi === 2 && (
                  <button
                    onClick={() => router.push('/login')}
                    className="flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-sm text-foreground hover:bg-secondary"
                  >
                    <LogOut className="h-4 w-4 flex-none" />
                    <span className="flex-1">Cerrar sesión</span>
                  </button>
                )}
              </div>
            </div>
          ))}
        </nav>

        <div className="min-w-0 flex-1">
          <div className="mb-2 flex gap-2 overflow-x-auto pb-2 md:hidden">
            {(Object.entries(SECTIONS) as [SectionKey, (typeof SECTIONS)[SectionKey]][]).map(([key, s]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`flex-none rounded-full border px-3 py-1.5 text-[13px] font-medium ${
                  tab === key ? 'border-[#d4d4d4] bg-secondary text-foreground' : 'border-border text-muted-foreground'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>

          <h1 className="heading-display mt-1 text-[28px]">{current.label}</h1>

          {tab === 'familia' && (
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

          {tab === 'suscripcion' && (
            <div className="mt-6 flex flex-col gap-3.5">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {(
                  [
                    { name: 'Founding' as const, price: '$[PRECIO FOUNDING] ARS / mes', note: 'Precio congelado mientras dure la beta', features: ['1 cámara', 'Comprensión contextual completa', 'Contactos de emergencia', 'Memoria de actividad sin límite'] },
                    { name: 'Premium' as const, price: '$[PRECIO PREMIUM] ARS / mes', note: '', features: ['Hasta [N] cámaras', 'Todo lo de Founding', 'Soporte prioritario', 'Contactos ilimitados'] },
                  ]
                ).map((p) => {
                  const isCurrent = plan === p.name;
                  return (
                    <div key={p.name} className={`rounded-3xl border p-4.5 ${isCurrent ? 'border-[#d4d4d4] bg-secondary/40' : 'border-border'}`}>
                      <div className="flex items-baseline justify-between gap-2">
                        <div className="heading-display text-xl">{p.name}</div>
                        {isCurrent && <span className="rounded-full bg-[#ececec] px-2.5 py-1 text-[11px] font-semibold">Actual</span>}
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
                        variant={isCurrent ? 'secondary' : 'default'}
                        disabled={isCurrent}
                        onClick={() => setPlan(p.name)}
                        className="mt-4 w-full"
                      >
                        {isCurrent ? 'Plan actual' : `Cambiar a ${p.name}`}
                      </Button>
                    </div>
                  );
                })}
              </div>
              <div className="rounded-3xl border border-border bg-background p-4.5">
                <div className="text-[12.5px] font-semibold">Facturación</div>
                <p className="mt-1 text-[11.5px] leading-relaxed text-muted-foreground">
                  Tarjeta terminada en 4421 · próximo cobro el 1 de septiembre de 2026. Si cambiás de plan, el nuevo precio aplica en tu próximo ciclo.
                </p>
              </div>
            </div>
          )}

          {tab === 'contactos' && (
            <div className="mt-6 flex flex-col gap-3.5">
              <p className="text-sm text-muted-foreground">
                Artemisa los contacta, en orden, si detecta una emergencia real. El 911 siempre antecede a esta lista.
              </p>
              <div className="flex flex-col gap-2">
                {contacts.map((c) => (
                  <div key={c.id} className="flex items-center gap-3 rounded-2xl border border-border bg-background p-3">
                    <span className="flex h-7.5 w-7.5 flex-none items-center justify-center rounded-full bg-secondary text-xs font-semibold">
                      {c.name[0]}
                    </span>
                    <div className="min-w-[120px] flex-1">
                      <div className="text-[13.5px] font-semibold">{c.name}</div>
                      <div className="mt-0.5 text-xs text-muted-foreground">{c.phone}</div>
                    </div>
                    <span className="rounded-full border border-border px-2.5 py-1 text-[11.5px] text-muted-foreground">
                      {c.confirmed ? 'Confirmado' : 'Pendiente'}
                    </span>
                    <button
                      onClick={() => setContacts((cs) => cs.filter((x) => x.id !== c.id))}
                      title="Quitar"
                      className="flex h-6.5 w-6.5 flex-none items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex flex-col gap-2 rounded-2xl border border-dashed border-[#d4d4d4] p-3.5 sm:flex-row sm:items-center">
                <Input
                  placeholder="Nombre"
                  value={newContact.name}
                  onChange={(e) => setNewContact((n) => ({ ...n, name: e.target.value }))}
                />
                <Input
                  placeholder="+54 9 11 ..."
                  value={newContact.phone}
                  onChange={(e) => setNewContact((n) => ({ ...n, phone: e.target.value }))}
                />
                <Button onClick={addContact} disabled={!newContact.name.trim() || !newContact.phone.trim()}>
                  Agregar
                </Button>
              </div>
            </div>
          )}

          {tab === 'alertas' && (
            <div className="mt-6 flex flex-col gap-3.5">
              <div className="rounded-3xl border border-border bg-background p-1">
                <div className="p-4 pb-1">
                  <div className="heading-display text-xl">Cómo te contactamos</div>
                  <p className="mt-1.5 text-[13px] text-muted-foreground">Las emergencias siempre te llegan, incluso en horario silencioso.</p>
                </div>
                <div className="flex flex-col gap-2 p-2.5">
                  {(
                    [
                      ['push', 'Push en tu teléfono', 'Llega en un par de segundos.'],
                      ['email', 'Resumen por email', 'Un resumen cada noche.'],
                      ['sms', 'Mensaje de texto', 'Solo emergencias, con costo de tu operador.'],
                    ] as const
                  ).map(([key, label, hint]) => (
                    <div key={key} className="flex items-center gap-3 rounded-2xl border border-border p-3.5">
                      <div className="flex-1">
                        <div className="text-[13.5px] font-semibold">{label}</div>
                        <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div>
                      </div>
                      <Switch checked={channels[key]} onCheckedChange={(v) => setChannels((c) => ({ ...c, [key]: v }))} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {current.placeholder && (
            <div className="mt-6">
              <div className="flex flex-col">
                {current.placeholder.map((pc) => (
                  <div key={pc} className="flex items-center gap-2.5 border-b border-border py-3">
                    <current.icon className="h-4 w-4 flex-none text-muted-foreground" />
                    <div className="flex-1 text-[13px] text-foreground">{pc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
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

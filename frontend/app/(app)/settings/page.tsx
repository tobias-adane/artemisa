'use client';

import { Suspense, useEffect, useState } from 'react';
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
import { useI18n, format } from '@/lib/i18n/context';
import type { Dictionary } from '@/lib/i18n/es';
import { useBackendUser } from '@/lib/use-backend-user';
import { listContacts, createContact } from '@/lib/api';

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

function sectionsFor(dict: Dictionary): Record<SectionKey, { label: string; icon: typeof UserRound; group: 0 | 1 | 2; placeholder?: string[] }> {
  const s = dict.settings.sections;
  return {
    perfil: { label: s.perfil.label, icon: UserRound, group: 0, placeholder: s.perfil.placeholder },
    suscripcion: { label: s.suscripcion.label, icon: CreditCard, group: 0 },
    espacios: { label: s.espacios.label, icon: GalleryHorizontalEnd, group: 0, placeholder: s.espacios.placeholder },
    familia: { label: s.familia.label, icon: Users, group: 0 },
    seguridad: { label: s.seguridad.label, icon: ShieldCheck, group: 0, placeholder: s.seguridad.placeholder },
    privacidad: { label: s.privacidad.label, icon: Lock, group: 1, placeholder: s.privacidad.placeholder },
    contactos: { label: s.contactos.label, icon: PhoneCall, group: 1 },
    instrucciones: { label: s.instrucciones.label, icon: SlidersHorizontal, group: 1, placeholder: s.instrucciones.placeholder },
    alertas: { label: s.alertas.label, icon: Bell, group: 1 },
    idioma: { label: s.idioma.label, icon: Globe, group: 1 },
    recursos: { label: s.recursos.label, icon: Folders, group: 2, placeholder: s.recursos.placeholder },
    terminos: { label: s.terminos.label, icon: FileText, group: 2, placeholder: s.terminos.placeholder },
    ayuda: { label: s.ayuda.label, icon: HelpCircle, group: 2, placeholder: s.ayuda.placeholder },
  };
}

function SettingsInner() {
  const router = useRouter();
  const search = useSearchParams();
  const { dict, locale, setLocale } = useI18n();
  const SECTIONS = sectionsFor(dict);
  const GROUP_LABELS = [dict.settings.groupAccount, dict.settings.groupSystem, dict.settings.groupAbout];
  const initialTab = (search.get('tab') as SectionKey) ?? 'familia';
  const [tab, setTab] = useState<SectionKey>(SECTIONS[initialTab] ? initialTab : 'familia');
  const [channels, setChannels] = useState({ push: true, email: false, sms: true });
  const [plan, setPlan] = useState<'Founding' | 'Premium'>('Founding');
  const { userId, available } = useBackendUser();
  const [contacts, setContacts] = useState(mockEmergencyContacts);
  const [newContact, setNewContact] = useState({ name: '', phone: '' });

  const current = SECTIONS[tab];

  useEffect(() => {
    if (!available) return;
    let cancelled = false;
    listContacts(userId).then((res) => {
      if (!cancelled && res.ok) setContacts(res.data);
    });
    return () => {
      cancelled = true;
    };
  }, [available, userId]);

  async function addContact() {
    if (!newContact.name.trim() || !newContact.phone.trim()) return;
    const name = newContact.name.trim();
    const phone = newContact.phone.trim();
    setNewContact({ name: '', phone: '' });

    if (available) {
      const res = await createContact({ user_id: userId, name, phone, relationship: 'other', priority: contacts.length + 1 });
      if (res.ok) {
        setContacts((c) => [...c, res.data]);
        return;
      }
    }
    // Backend Python no disponible acá — se agrega solo localmente.
    setContacts((c) => [
      ...c,
      {
        id: `ec-${Date.now()}`,
        user_id: mockUser.id,
        name,
        phone,
        relationship: 'other',
        priority: c.length + 1,
        confirmed: false,
      },
    ]);
  }

  return (
    <div>
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-transparent bg-background/85 px-4 backdrop-blur">
        <button onClick={() => router.push('/home')} className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="rounded-full bg-background px-4 py-2 text-xs font-medium">{dict.settings.pageTitle}</div>
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
                    <span className="flex-1">{dict.settings.logout}</span>
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
                <div className="heading-display text-xl">{dict.settings.familia.title}</div>
                <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">
                  {dict.settings.familia.body}
                </p>
              </div>
              <div className="flex flex-col gap-2 p-2.5">
                {[
                  { name: mockUser.name, email: mockUser.email, role: dict.settings.familia.role },
                  { name: 'Valentina Vidal', email: 'valentina@artemisa.app', role: dict.settings.familia.role },
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
                    { name: 'Founding' as const, price: dict.settings.suscripcion.founding.price, note: dict.settings.suscripcion.founding.note, features: dict.settings.suscripcion.founding.features },
                    { name: 'Premium' as const, price: dict.settings.suscripcion.premium.price, note: '', features: dict.settings.suscripcion.premium.features },
                  ]
                ).map((p) => {
                  const isCurrent = plan === p.name;
                  return (
                    <div key={p.name} className={`rounded-3xl border p-4.5 ${isCurrent ? 'border-[#d4d4d4] bg-secondary/40' : 'border-border'}`}>
                      <div className="flex items-baseline justify-between gap-2">
                        <div className="heading-display text-xl">{p.name}</div>
                        {isCurrent && <span className="rounded-full bg-[#ececec] px-2.5 py-1 text-[11px] font-semibold">{dict.settings.suscripcion.current}</span>}
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
                        {isCurrent ? dict.settings.suscripcion.currentPlan : format(dict.settings.suscripcion.changeTo, { plan: p.name })}
                      </Button>
                    </div>
                  );
                })}
              </div>
              <div className="rounded-3xl border border-border bg-background p-4.5">
                <div className="text-[12.5px] font-semibold">{dict.settings.suscripcion.billingTitle}</div>
                <p className="mt-1 text-[11.5px] leading-relaxed text-muted-foreground">
                  {dict.settings.suscripcion.billingBody}
                </p>
              </div>
            </div>
          )}

          {tab === 'contactos' && (
            <div className="mt-6 flex flex-col gap-3.5">
              <p className="text-sm text-muted-foreground">
                {dict.settings.contactos.body}
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
                      {c.confirmed ? dict.settings.contactos.confirmed : dict.settings.contactos.pending}
                    </span>
                    <button
                      onClick={() => setContacts((cs) => cs.filter((x) => x.id !== c.id))}
                      title={dict.settings.contactos.remove}
                      className="flex h-6.5 w-6.5 flex-none items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex flex-col gap-2 rounded-2xl border border-dashed border-[#d4d4d4] p-3.5 sm:flex-row sm:items-center">
                <Input
                  placeholder={dict.settings.contactos.namePlaceholder}
                  value={newContact.name}
                  onChange={(e) => setNewContact((n) => ({ ...n, name: e.target.value }))}
                />
                <Input
                  placeholder={dict.settings.contactos.phonePlaceholder}
                  value={newContact.phone}
                  onChange={(e) => setNewContact((n) => ({ ...n, phone: e.target.value }))}
                />
                <Button onClick={addContact} disabled={!newContact.name.trim() || !newContact.phone.trim()}>
                  {dict.settings.contactos.add}
                </Button>
              </div>
            </div>
          )}

          {tab === 'alertas' && (
            <div className="mt-6 flex flex-col gap-3.5">
              <div className="rounded-3xl border border-border bg-background p-1">
                <div className="p-4 pb-1">
                  <div className="heading-display text-xl">{dict.settings.alertas.title}</div>
                  <p className="mt-1.5 text-[13px] text-muted-foreground">{dict.settings.alertas.body}</p>
                </div>
                <div className="flex flex-col gap-2 p-2.5">
                  {(
                    [
                      ['push', dict.settings.alertas.push.label, dict.settings.alertas.push.hint],
                      ['email', dict.settings.alertas.email.label, dict.settings.alertas.email.hint],
                      ['sms', dict.settings.alertas.sms.label, dict.settings.alertas.sms.hint],
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

          {tab === 'idioma' && (
            <div className="mt-6">
              <p className="text-sm text-muted-foreground">{dict.settings.idioma.body}</p>
              <div className="mt-4 flex flex-col">
                {(
                  [
                    ['es', dict.settings.idioma.spanish],
                    ['en', dict.settings.idioma.english],
                  ] as const
                ).map(([code, label]) => (
                  <button
                    key={code}
                    onClick={() => setLocale(code)}
                    className="flex items-center justify-between gap-2.5 border-b border-border py-3 text-left text-[13px] text-foreground"
                  >
                    <span>{label}</span>
                    {locale === code && <span className="text-muted-foreground">✓</span>}
                  </button>
                ))}
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

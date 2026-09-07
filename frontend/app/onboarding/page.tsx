'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';

const STEPS = ['personal', 'home', 'contacts', 'space', 'done'] as const;
const HOME_TYPES = [
  { key: 'house', label: 'Casa' },
  { key: 'apartment', label: 'Departamento' },
  { key: 'small_business', label: 'Comercio' },
] as const;

const IP_RE = /^(\d{1,3}\.){3}\d{1,3}$/;

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [homeType, setHomeType] = useState<(typeof HOME_TYPES)[number]['key']>('house');
  const [hasChildren, setHasChildren] = useState(false);
  const [customInstructions, setCustomInstructions] = useState('');
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('+54 9 ');
  const [spaceName, setSpaceName] = useState('');
  const [camIp, setCamIp] = useState('');
  const [camState, setCamState] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle');

  const key = STEPS[step];
  const first = name.trim().split(/\s+/)[0] || 'vecino';

  function testCamera(ip: string) {
    setCamIp(ip);
    if (!IP_RE.test(ip.trim())) {
      setCamState('idle');
      return;
    }
    setCamState('testing');
    setTimeout(() => {
      // 192.168.1.1 deliberately reproduces the connection-error state.
      setCamState(ip.trim() === '192.168.1.1' ? 'error' : 'ok');
    }, 900);
  }

  function advance() {
    if (step === STEPS.length - 1) {
      router.push('/home');
      return;
    }
    setStep((s) => s + 1);
  }

  const canContinue =
    key !== 'space' || camState === 'ok' || camState === 'idle';

  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary/40 px-5 py-8">
      <div className="w-full max-w-lg rounded-[26px] border border-border bg-background p-1 shadow-lg">
        <div className="rounded-[22px] bg-secondary/60 px-9 py-9">
          <div className="flex items-center justify-between">
            {step > 0 ? (
              <button onClick={() => setStep((s) => Math.max(0, s - 1))} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
                <ChevronLeft className="h-3.5 w-3.5" /> Atrás
              </button>
            ) : (
              <span />
            )}
            <div className="flex gap-1">
              {STEPS.map((_, i) => (
                <span key={i} className={`h-1 rounded-full transition-all ${i === step ? 'w-4 bg-primary' : i < step ? 'w-1 bg-primary' : 'w-1 bg-border'}`} />
              ))}
            </div>
          </div>

          <h1 className="heading-display mt-6 text-[28px] leading-tight">
            {key === 'personal' && 'Empecemos a proteger tu hogar.'}
            {key === 'home' && '¿A quién estamos protegiendo?'}
            {key === 'contacts' && '¿A quién llamamos si pasa algo?'}
            {key === 'space' && 'Configurá tus espacios.'}
            {key === 'done' && `Listo, ${first}.`}
          </h1>

          {key === 'personal' && (
            <div className="mt-6">
              <label className="mb-1.5 block text-xs font-semibold">Tu nombre</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="María Álvarez" />
            </div>
          )}

          {key === 'home' && (
            <div className="mt-5 flex flex-col gap-5">
              <div>
                <label className="mb-1.5 block text-xs font-semibold">Tipo de hogar</label>
                <div className="flex flex-wrap gap-2">
                  {HOME_TYPES.map((h) => (
                    <button
                      key={h.key}
                      onClick={() => setHomeType(h.key)}
                      className={`h-8 rounded-full border px-3.5 text-[12.5px] font-medium ${
                        homeType === h.key ? 'border-[#d4d4d4] bg-background text-foreground' : 'border-border text-muted-foreground'
                      }`}
                    >
                      {h.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between rounded-2xl border border-border bg-background p-3.5">
                <div>
                  <div className="text-[13.5px] font-semibold">¿Viven chicos en casa?</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">Ajusta cómo Artemisa distingue lo normal de lo que amerita tu atención.</div>
                </div>
                <Switch checked={hasChildren} onCheckedChange={setHasChildren} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold">¿Qué es lo que más te preocupa?</label>
                <textarea
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  placeholder="Ej: la mucama viene los martes a las 10am. Nadie debería estar en casa después de las 23hs entre semana."
                  className="min-h-[96px] w-full resize-none rounded-2xl border border-border bg-background p-3 text-sm outline-none"
                />
              </div>
            </div>
          )}

          {key === 'contacts' && (
            <div className="mt-5 flex flex-col gap-4">
              <p className="text-sm leading-relaxed text-muted-foreground">
                Agregá al menos una persona de confianza. Artemisa la va a contactar — en orden — si detecta una emergencia real. El 911 siempre se contacta primero.
              </p>
              <div>
                <label className="mb-1.5 block text-xs font-semibold">Nombre</label>
                <Input value={contactName} onChange={(e) => setContactName(e.target.value)} placeholder="Valentina Vidal" />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold">Teléfono</label>
                <Input value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} placeholder="+54 9 11 2233 4455" />
              </div>
            </div>
          )}

          {key === 'space' && (
            <div className="mt-5 flex flex-col gap-4">
              <p className="text-sm leading-relaxed text-muted-foreground">
                Un espacio es cualquier lugar donde tengas una cámara. Nombralo y probá la conexión — podés agregar el resto una vez adentro.
              </p>
              <div>
                <label className="mb-1.5 block text-xs font-semibold">Nombre del espacio</label>
                <Input value={spaceName} onChange={(e) => setSpaceName(e.target.value)} placeholder="Living" />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold">Dirección IP de la cámara</label>
                <Input value={camIp} onChange={(e) => testCamera(e.target.value)} placeholder="192.168.1.42" />
              </div>
              {camState === 'testing' && <p className="text-xs text-muted-foreground">Probando conexión…</p>}
              {camState === 'ok' && <p className="text-xs font-medium text-[var(--status-normal)]">Conectada correctamente.</p>}
              {camState === 'error' && (
                <div className="rounded-2xl border border-[#f0d4d4] bg-[#fdf2f2] p-3.5">
                  <p className="text-[13px] font-medium text-[#dc2626]">No pudimos conectar.</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">Revisá la URL o intentá de nuevo — el resto del formulario queda como está.</p>
                  <button
                    onClick={() => testCamera(camIp)}
                    className="mt-2.5 inline-flex items-center gap-1.5 text-xs font-medium text-foreground underline underline-offset-2"
                  >
                    <RefreshCw className="h-3 w-3" /> Reintentar
                  </button>
                </div>
              )}
            </div>
          )}

          {key === 'done' && (
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Guardamos tu perfil de hogar. Vamos a tu Inicio para que veas cómo se siente Artemisa.
            </p>
          )}

          <Button onClick={advance} disabled={!canContinue} className="mt-8 w-full">
            {key === 'done' ? 'Ir a Artemisa' : 'Continuar'}
          </Button>
        </div>
      </div>
    </div>
  );
}

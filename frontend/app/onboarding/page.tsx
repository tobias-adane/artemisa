'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const STEPS = ['personal', 'home', 'contacts', 'space', 'done'] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');

  const key = STEPS[step];
  const first = name.trim().split(/\s+/)[0] || 'vecino';

  function advance() {
    if (step === STEPS.length - 1) {
      router.push('/home');
      return;
    }
    setStep((s) => s + 1);
  }

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
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Contanos sobre tu hogar en el siguiente paso — cuántas personas viven, si hay chicos, y qué es lo que más te preocupa. Esto ayuda a Artemisa a distinguir una noche normal de un problema real.
            </p>
          )}

          {key === 'contacts' && (
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Agregá al menos una persona de confianza. Artemisa la va a contactar — en orden — si detecta una emergencia real. El 911 siempre se contacta primero.
            </p>
          )}

          {key === 'space' && (
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Un espacio es cualquier lugar donde tengas una cámara. Podés agregar los que quieras — por IP o escaneando el QR de la cámara — una vez que entres a tu cuenta.
            </p>
          )}

          {key === 'done' && (
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Guardamos tu perfil de hogar. Vamos a tu Inicio para que veas cómo se siente Artemisa.
            </p>
          )}

          <Button onClick={advance} className="mt-8 w-full">
            {key === 'done' ? 'Ir a Artemisa' : 'Continuar'}
          </Button>
        </div>
      </div>
    </div>
  );
}

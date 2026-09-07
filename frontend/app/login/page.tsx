'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Mode = 'login' | 'signup' | 'forgot' | 'verify';

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

function AppleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="#0a0a0a">
      <path d="M17.05 12.53c-.02-2.02 1.65-2.99 1.72-3.04-.94-1.37-2.4-1.56-2.92-1.58-1.24-.13-2.42.73-3.05.73-.63 0-1.6-.71-2.63-.69-1.35.02-2.6.79-3.29 2-.14.24-.35.7-.35.7s-1.29 3.71.9 6.9c.66.95 1.44 2.02 2.47 1.98 1-.04 1.37-.64 2.58-.64 1.2 0 1.54.64 2.6.62 1.07-.02 1.75-.97 2.4-1.93.42-.61.75-1.32.75-1.32s-1.68-.75-1.7-2.63zM15.1 6.05c.55-.67.92-1.6.82-2.53-.79.03-1.75.53-2.32 1.19-.51.59-.96 1.54-.84 2.44.88.07 1.79-.45 2.34-1.1z" />
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [sent, setSent] = useState(false);

  function submit() {
    if (mode === 'signup') {
      router.push('/onboarding');
      return;
    }
    if (mode === 'forgot') {
      setSent(true);
      return;
    }
    if (mode === 'verify') {
      router.push('/home');
      return;
    }
    router.push('/home');
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary/40 px-5 py-8">
      <div className="w-full max-w-md rounded-[26px] border border-border bg-background p-1 shadow-lg">
        <div className="rounded-[22px] bg-secondary/60 px-8 py-11">
          <div className="mx-auto flex h-8 w-8 items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/artemisa-logo.svg" alt="Artemisa" width={24} height={24} />
          </div>

          {mode === 'forgot' ? (
            <>
              <h1 className="heading-display mt-4 text-center text-[29px] leading-tight">Recuperá tu contraseña</h1>
              <p className="mt-2 text-center text-[13px] leading-relaxed text-muted-foreground">
                {sent
                  ? `Si existe una cuenta con ${email || 'ese email'}, te enviamos un link para recuperarla.`
                  : 'Te mandamos un link a tu email para que elijas una nueva.'}
              </p>
              {!sent && (
                <div className="mt-8">
                  <label className="mb-1.5 block text-xs font-semibold">Correo electrónico</label>
                  <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nombre@email.com" />
                </div>
              )}
              <Button className="mt-5 w-full" onClick={submit} disabled={sent && false}>
                {sent ? 'Reenviar link' : 'Enviar link'}
              </Button>
            </>
          ) : mode === 'verify' ? (
            <>
              <h1 className="heading-display mt-4 text-center text-[29px] leading-tight">Verificá tu email</h1>
              <p className="mt-2 text-center text-[13px] leading-relaxed text-muted-foreground">
                Te mandamos un código de 6 dígitos a {email || 'tu email'}.
              </p>
              <div className="mt-8 flex justify-center gap-2">
                {code.map((d, i) => (
                  <input
                    key={i}
                    value={d}
                    maxLength={1}
                    onChange={(e) => {
                      const v = e.target.value.replace(/\D/g, '');
                      setCode((c) => c.map((x, j) => (j === i ? v : x)));
                      if (v && e.target.nextElementSibling instanceof HTMLInputElement) e.target.nextElementSibling.focus();
                    }}
                    className="h-12 w-10 rounded-xl border border-border bg-background text-center text-lg outline-none focus:border-[#a3a3a3]"
                  />
                ))}
              </div>
              <button className="mx-auto mt-4 block text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground">
                Reenviar código
              </button>
              <Button className="mt-5 w-full" onClick={submit} disabled={code.some((d) => !d)}>
                Verificar
              </Button>
            </>
          ) : (
            <>
              <h1 className="heading-display mt-4 text-center text-[29px] leading-tight">
                {mode === 'signup' ? 'Creá tu cuenta de Artemisa' : 'Iniciá sesión en Artemisa'}
              </h1>
              <p className="mt-2 text-center text-[13px] leading-relaxed text-muted-foreground">
                {mode === 'signup'
                  ? 'Configurá tu hogar, invitá a tu familia y empezá a monitorear en minutos.'
                  : '¡Qué bueno tenerte de vuelta! Tus espacios te esperan.'}
              </p>

              <div className="mt-8 flex flex-col gap-2.5">
                <button className="flex h-10 w-full items-center justify-center gap-2.5 rounded-[22px] border border-border bg-background text-[13.5px] font-medium hover:bg-secondary">
                  <GoogleIcon /> {mode === 'signup' ? 'Registrarte con Google' : 'Continuar con Google'}
                </button>
                <button className="flex h-10 w-full items-center justify-center gap-2.5 rounded-[22px] border border-border bg-background text-[13.5px] font-medium hover:bg-secondary">
                  <AppleIcon /> {mode === 'signup' ? 'Registrarte con Apple' : 'Continuar con Apple'}
                </button>
              </div>

              <div className="my-6 flex items-center gap-3">
                <div className="h-px flex-1 bg-border" />
                <span className="text-[11px] tracking-wide text-muted-foreground/70">O</span>
                <div className="h-px flex-1 bg-border" />
              </div>

              <div className="flex flex-col gap-3.5">
                {mode === 'signup' && (
                  <div>
                    <label className="mb-1.5 block text-xs font-semibold">Nombre</label>
                    <Input placeholder="María Álvarez" />
                  </div>
                )}
                <div>
                  <label className="mb-1.5 block text-xs font-semibold">Correo electrónico</label>
                  <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nombre@email.com" />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-semibold">Contraseña</label>
                  <Input type="password" placeholder="mínimo 8 caracteres" />
                </div>
                {mode === 'signup' && (
                  <div>
                    <label className="mb-1.5 block text-xs font-semibold">Confirmar contraseña</label>
                    <Input type="password" placeholder="repetí la contraseña" />
                  </div>
                )}
              </div>

              {mode === 'login' && (
                <div className="mt-2.5 flex justify-end">
                  <button onClick={() => setMode('forgot')} className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground">
                    ¿Olvidaste tu contraseña?
                  </button>
                </div>
              )}

              <Button
                className="mt-5 w-full"
                onClick={() => {
                  if (mode === 'signup') {
                    setMode('verify');
                    return;
                  }
                  submit();
                }}
              >
                {mode === 'signup' ? 'Crear cuenta' : 'Iniciar sesión'}
              </Button>
            </>
          )}
        </div>

        <div className="px-5 py-4 text-center text-[13px]">
          {mode === 'forgot' || mode === 'verify' ? (
            <button
              onClick={() => {
                setMode('login');
                setSent(false);
              }}
              className="font-medium text-muted-foreground underline underline-offset-2 hover:text-foreground"
            >
              Volver a iniciar sesión
            </button>
          ) : (
            <>
              {mode === 'signup' ? '¿Ya tenés una cuenta?' : '¿Todavía no tenés cuenta?'}{' '}
              <button
                onClick={() => setMode(mode === 'signup' ? 'login' : 'signup')}
                className="font-medium text-muted-foreground underline underline-offset-2 hover:text-foreground"
              >
                {mode === 'signup' ? 'Iniciar sesión' : 'Creá una cuenta'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

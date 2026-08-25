'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Mode = 'login' | 'signup';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>('login');

  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary/40 px-5 py-8">
      <div className="w-full max-w-md rounded-[26px] border border-border bg-background p-1 shadow-lg">
        <div className="rounded-[22px] bg-secondary/60 px-8 py-11">
          <div className="mx-auto flex h-8 w-8 items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/artemisa-logo.svg" alt="Artemisa" width={24} height={24} />
          </div>
          <h1 className="heading-display mt-4 text-center text-[29px] leading-tight">
            {mode === 'signup' ? 'Creá tu cuenta de Artemisa' : 'Iniciá sesión en Artemisa'}
          </h1>
          <p className="mt-2 text-center text-[13px] leading-relaxed text-muted-foreground">
            {mode === 'signup'
              ? 'Configurá tu hogar, invitá a tu familia y empezá a monitorear en minutos.'
              : '¡Qué bueno tenerte de vuelta! Tus espacios te esperan.'}
          </p>

          <div className="mt-8 flex flex-col gap-3.5">
            {mode === 'signup' && (
              <div>
                <label className="mb-1.5 block text-xs font-semibold">Nombre</label>
                <Input placeholder="María Álvarez" />
              </div>
            )}
            <div>
              <label className="mb-1.5 block text-xs font-semibold">Correo electrónico</label>
              <Input type="email" placeholder="nombre@email.com" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold">Contraseña</label>
              <Input type="password" placeholder="mínimo 8 caracteres" />
            </div>
          </div>

          {mode === 'login' && (
            <div className="mt-2.5 flex justify-end">
              <button className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground">
                ¿Olvidaste tu contraseña?
              </button>
            </div>
          )}

          <Button
            className="mt-5 w-full"
            onClick={() => router.push(mode === 'signup' ? '/onboarding' : '/home')}
          >
            {mode === 'signup' ? 'Crear cuenta' : 'Iniciar sesión'}
          </Button>
        </div>

        <div className="px-5 py-4 text-center text-[13px]">
          {mode === 'signup' ? '¿Ya tenés una cuenta?' : '¿Todavía no tenés cuenta?'}{' '}
          <button
            onClick={() => setMode(mode === 'signup' ? 'login' : 'signup')}
            className="font-medium text-muted-foreground underline underline-offset-2 hover:text-foreground"
          >
            {mode === 'signup' ? 'Iniciar sesión' : 'Creá una cuenta'}
          </button>
        </div>
      </div>
    </div>
  );
}

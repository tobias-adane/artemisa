'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowUp, Mic, Paperclip, Plus, SquarePen } from 'lucide-react';
import { PageHeader } from '@/components/artemisa/page-header';
import { AlertCard } from '@/components/artemisa/alert-card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { mockActivity, mockSpaces, mockThreads, mockUser } from '@/lib/mock-data';

type ChatMessage = { role: 'user' | 'assistant'; text: string };

function greetingFor(date: Date) {
  const h = date.getHours();
  if (h < 6) return 'Buenas noches';
  if (h < 12) return 'Buenos días';
  if (h < 20) return 'Buenas tardes';
  return 'Buenas noches';
}

function replyFor(msg: string) {
  const m = msg.toLowerCase();
  if (/(familia|chicos|quien esta|quién está|todo el mundo)/.test(m))
    return 'Están todos en casa. Vi a Sofía en la cocina hace unos 20 minutos, y Rocky está dormido cerca de la puerta de atrás desde las 8. Nadie salió desde que llegaste.';
  if (/(actividad|paso|pasó|reciente|hoy)/.test(m))
    return 'Un día tranquilo. La puerta principal se cerró sola a las 21:14, y a las 14:30 dejaron un paquete que todavía nadie retiró. Nada que necesitara tu atención urgente.';
  if (/(pasando|ahora|estado)/.test(m))
    return 'Todo tranquilo por ahora. La cámara de la entrada está sin señal, el resto de tus espacios sigue mirando con normalidad.';
  if (/(puerta|cerrad|llave)/.test(m))
    return 'Todas las puertas están cerradas. La principal se cerró por última vez a las 21:14.';
  return 'Estoy mirando la casa y todo parece tranquilo. Preguntame quién está en casa, qué pasó hoy, o por cualquier habitación, y te cuento lo que veo.';
}

const QUICK_ACTIONS = ['¿Cómo está mi familia?', '¿Qué está pasando en casa?', 'Actividad reciente'];

export default function HomePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);

  const greeting = useMemo(() => greetingFor(new Date()), []);
  const day1 = mockActivity.length === 0;
  const conversing = messages.length > 0 || thinking;

  const attentionThread = mockThreads.find((t) => t.classification === 'attention' && !t.escalated_to_reasoning);
  const attentionSpace = attentionThread ? mockSpaces.find((s) => s.id === attentionThread.space_id) : undefined;

  function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || thinking) return;
    setMessages((m) => [...m, { role: 'user', text: msg }]);
    setInput('');
    setThinking(true);
    setTimeout(() => {
      setMessages((m) => [...m, { role: 'assistant', text: replyFor(msg) }]);
      setThinking(false);
    }, 900);
  }

  return (
    <div>
      <PageHeader
        title="Inicio"
        right={
          <button
            title="Chat nuevo"
            onClick={() => setMessages([])}
            className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground"
          >
            <SquarePen className="h-3 w-3" />
          </button>
        }
      />

      <section className="mx-auto flex min-h-[calc(100vh-320px)] max-w-2xl flex-col items-center justify-center px-6 pb-4 pt-8">
        {!conversing && (
          <div className="text-center leading-tight">
            <h1 className="heading-display text-3xl">
              {greeting}, <span className="text-[#bcbcbc]">{mockUser.name.split(' ')[0]}</span>
            </h1>
            <p className="heading-display text-3xl text-foreground">
              {day1 ? 'Recién empezamos a cuidar tu hogar.' : 'Todo está en orden en casa.'}
            </p>
          </div>
        )}

        {conversing && (
          <div className="flex w-full max-h-[52vh] flex-col overflow-y-auto py-1">
            {messages.map((m, i) => (
              <div key={i} className={`mb-4 flex animate-fade-up ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {m.role === 'user' ? (
                  <div className="max-w-[78%] rounded-[24px_6px_20px_20px] border border-border bg-background px-4 py-3 text-sm">
                    {m.text}
                  </div>
                ) : (
                  <div className="heading-display max-w-[94%] text-lg leading-snug">{m.text}</div>
                )}
              </div>
            ))}
            {thinking && (
              <div className="mb-3 flex justify-start">
                <div className="flex gap-1.5 rounded-3xl bg-secondary px-4 py-3.5">
                  {[0, 1, 2].map((i) => (
                    <span key={i} className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground" style={{ animationDelay: `${i * 0.2}s` }} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {attentionThread && attentionSpace && !conversing && (
          <div className="mt-6 w-full">
            <AlertCard thread={attentionThread} spaceName={attentionSpace.name} />
          </div>
        )}

        <div className="mt-8 w-full rounded-[36px] border border-border bg-background p-4 shadow-[0_6px_28px_rgba(0,0,0,0.05)]">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Preguntá lo que quieras sobre tu casa"
            className="h-auto border-none px-1 py-2 text-sm shadow-none focus-visible:ring-0"
          />
          <div className="mt-1 flex items-center gap-1.5">
            <button title="Adjuntar" className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground">
              <Plus className="h-3 w-3" />
            </button>
            <div className="flex-1" />
            {input.trim() ? (
              <button onClick={() => send()} title="Enviar" className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button title="Voz" className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground">
                <Mic className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {!conversing && (
          <div className="mt-5 flex flex-wrap justify-center gap-2.5">
            {(day1 ? QUICK_ACTIONS.slice(0, 2) : QUICK_ACTIONS).map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                className="rounded-full border border-border bg-background px-3 py-2 text-[13px] text-muted-foreground shadow-[0_10px_34px_rgba(0,0,0,0.10)] hover:text-foreground"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </section>

      {!conversing && (
        <section className="mx-auto max-w-5xl px-6 pb-8 sm:px-10">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {mockSpaces.map((space) => (
              <Link
                key={space.id}
                href={`/spaces/${space.id}`}
                className="group relative aspect-[4/3] overflow-hidden rounded-3xl bg-secondary"
              >
                <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/55 to-transparent" />
                <span className="absolute bottom-3.5 left-4 text-xs text-white [text-shadow:0_1px_8px_rgba(0,0,0,0.3)]">
                  {space.name}
                </span>
                {space.status === 'offline' && (
                  <span className="absolute right-3.5 top-3.5 h-2 w-2 rounded-full" style={{ background: 'var(--status-offline)' }} />
                )}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

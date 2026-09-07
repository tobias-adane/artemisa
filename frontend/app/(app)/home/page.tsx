'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowUp, Camera as CameraIcon, Globe, Mic, MoreHorizontal, Paperclip, Plus, SquarePen } from 'lucide-react';
import { PageHeader } from '@/components/artemisa/page-header';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { mockSpaces, mockUser } from '@/lib/mock-data';

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
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [toast, setToast] = useState('');

  const greeting = useMemo(() => greetingFor(new Date()), []);
  const conversing = messages.length > 0 || thinking;

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(''), 2400);
  }

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

  function pickFile() {
    const el = document.createElement('input');
    el.type = 'file';
    el.multiple = true;
    el.click();
  }

  function pickPhoto() {
    const el = document.createElement('input');
    el.type = 'file';
    el.accept = 'image/*';
    el.setAttribute('capture', 'environment');
    el.click();
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
            <p className="heading-display text-3xl text-foreground">Todo está en orden en casa.</p>
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
                  <div className="max-w-[94%] text-[14.5px] leading-relaxed">{m.text}</div>
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
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button title="Opciones" className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground">
                  <Plus className="h-3 w-3" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" className="w-[220px]">
                <DropdownMenuLabel>Opciones</DropdownMenuLabel>
                <DropdownMenuItem onClick={pickFile}>
                  <Paperclip className="h-4 w-4" /> Agregar Archivos o Fotos
                </DropdownMenuItem>
                <DropdownMenuItem onClick={pickPhoto}>
                  <CameraIcon className="h-4 w-4" /> Tomar Foto
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>Espacios</DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    {mockSpaces.map((sp) => (
                      <DropdownMenuItem key={sp.id} onClick={() => flash(`Espacio ${sp.name} agregado al contexto`)}>
                        {sp.name}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuItem onClick={() => flash('A tu Alrededor llega pronto')}>
                  <Globe className="h-4 w-4" /> A tu Alrededor
                  <span className="ml-auto text-[11px] font-semibold text-[#2563eb]">Beta</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
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
            {QUICK_ACTIONS.map((q) => (
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
                className="flex aspect-[4/3] flex-col rounded-3xl border border-border bg-secondary p-1"
              >
                <div className="flex min-h-0 flex-1 flex-col justify-end rounded-[18px] border border-border bg-secondary p-2">
                  <div className="flex items-center gap-2 rounded-xl px-1.5 py-1">
                    <span className="flex-1 truncate text-sm">{space.name}</span>
                    <button
                      title="Más"
                      onClick={(e) => e.preventDefault()}
                      className="flex h-4 w-4 flex-none items-center justify-center text-muted-foreground hover:text-foreground"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {toast && (
        <div className="fixed bottom-24 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-primary px-3.5 py-2 text-xs font-medium text-primary-foreground shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}

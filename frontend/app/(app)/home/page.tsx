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
import { useI18n, format } from '@/lib/i18n/context';
import type { Dictionary } from '@/lib/i18n/es';

type ChatMessage = { role: 'user' | 'assistant'; text: string };

function greetingFor(date: Date, dict: Dictionary) {
  const h = date.getHours();
  if (h < 12) return dict.home.greetingMorning;
  if (h < 20) return dict.home.greetingAfternoon;
  return dict.home.greetingNight;
}

function replyFor(msg: string, dict: Dictionary) {
  const m = msg.toLowerCase();
  if (/(familia|chicos|quien esta|quién está|todo el mundo|family|kids|who.?s home)/.test(m)) return dict.home.replyFamily;
  if (/(actividad|paso|pasó|reciente|hoy|activity|happened|today)/.test(m)) return dict.home.replyActivity;
  if (/(pasando|ahora|estado|going on|status)/.test(m)) return dict.home.replyStatus;
  if (/(puerta|cerrad|llave|door|lock)/.test(m)) return dict.home.replyDoors;
  return dict.home.replyDefault;
}

export default function HomePage() {
  const router = useRouter();
  const { dict } = useI18n();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [toast, setToast] = useState('');

  const QUICK_ACTIONS = [dict.home.quick1, dict.home.quick2, dict.home.quick3];
  const greeting = useMemo(() => greetingFor(new Date(), dict), [dict]);
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
      setMessages((m) => [...m, { role: 'assistant', text: replyFor(msg, dict) }]);
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
        title={dict.home.pageTitle}
        right={
          <button
            title={dict.home.newChatTooltip}
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
            <p className="heading-display text-3xl text-foreground">{dict.home.subtitle}</p>
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
            placeholder={dict.home.inputPlaceholder}
            className="h-auto border-none px-1 py-2 text-sm shadow-none focus-visible:ring-0"
          />
          <div className="mt-1 flex items-center gap-1.5">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button title={dict.home.optionsTooltip} className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground">
                  <Plus className="h-3 w-3" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" className="w-[220px]">
                <DropdownMenuLabel>{dict.home.optionsTooltip}</DropdownMenuLabel>
                <DropdownMenuItem onClick={pickFile}>
                  <Paperclip className="h-4 w-4" /> {dict.home.addFilesPhotos}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={pickPhoto}>
                  <CameraIcon className="h-4 w-4" /> {dict.home.takePhoto}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>{dict.home.spacesSubmenu}</DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    {mockSpaces.map((sp) => (
                      <DropdownMenuItem key={sp.id} onClick={() => flash(format(dict.home.spaceAddedToast, { name: sp.name }))}>
                        {sp.name}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuItem onClick={() => flash(dict.home.aroundMeSoonToast)}>
                  <Globe className="h-4 w-4" /> {dict.home.aroundMe}
                  <span className="ml-auto text-[11px] font-semibold text-[#2563eb]">{dict.home.aroundMeBeta}</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <div className="flex-1" />
            {input.trim() ? (
              <button onClick={() => send()} title={dict.home.sendTooltip} className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button title={dict.home.voiceTooltip} className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground">
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
                      title={dict.spaces.moreTooltip}
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

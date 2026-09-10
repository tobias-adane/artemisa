'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowUp, Camera as CameraIcon, ChevronLeft, Globe, Mic, Paperclip, Plus, SquarePen } from 'lucide-react';
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
import { mockSpaces } from '@/lib/mock-data';
import { useI18n, format } from '@/lib/i18n/context';
import { useChatThread } from '@/lib/use-chat';
import { CHAT_SEED_KEY } from '@/lib/chat-seed';

/**
 * Vista de chat de pantalla completa — SOLO se navega acá desde el
 * composer de Home en mobile (ver home/page.tsx `send()`). En desktop
 * el chat vive inline en Home; esta ruta no aparece en ningún nav.
 */
export default function ChatPage() {
  const router = useRouter();
  const { dict } = useI18n();
  const { messages, thinking, sendMessage, reset } = useChatThread(dict);
  const [input, setInput] = useState('');
  const [toast, setToast] = useState('');
  const seeded = useRef(false);

  useEffect(() => {
    if (seeded.current) return;
    seeded.current = true;
    try {
      const seed = sessionStorage.getItem(CHAT_SEED_KEY);
      if (seed) {
        sessionStorage.removeItem(CHAT_SEED_KEY);
        sendMessage(seed);
      }
    } catch {
      // best-effort
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(''), 2400);
  }

  function send() {
    const msg = input.trim();
    if (!msg || thinking) return;
    sendMessage(msg);
    setInput('');
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
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-transparent bg-background/85 px-5 backdrop-blur">
        <button
          title={dict.chat.backTooltip}
          onClick={() => router.push('/home')}
          className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </button>
        <div className="rounded-full bg-background px-4 py-2 text-xs font-medium">{dict.chat.pageTitle}</div>
        <button
          title={dict.chat.newChatTooltip}
          onClick={reset}
          className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground"
        >
          <SquarePen className="h-3 w-3" />
        </button>
      </header>

      <section className="mx-auto flex min-h-[calc(100vh-220px)] max-w-2xl flex-col justify-end px-6 pb-4 pt-4">
        <div className="flex w-full flex-1 flex-col justify-end overflow-y-auto py-1">
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

        <div className="mt-4 w-full rounded-[36px] border border-border bg-background p-4 shadow-[0_6px_28px_rgba(0,0,0,0.05)]">
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
            autoFocus
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
              <button onClick={send} title={dict.home.sendTooltip} className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button title={dict.home.voiceTooltip} className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground">
                <Mic className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      </section>

      {toast && (
        <div className="fixed bottom-24 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-primary px-3.5 py-2 text-xs font-medium text-primary-foreground shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}

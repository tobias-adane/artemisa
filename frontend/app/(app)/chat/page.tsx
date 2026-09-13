'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, SquarePen } from 'lucide-react';
import { ChatComposer } from '@/components/artemisa/chat-composer';
import { SpaceFocusCard } from '@/components/artemisa/space-focus-card';
import { mockSpaces } from '@/lib/mock-data';
import { useI18n } from '@/lib/i18n/context';
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
  const [selectedSpaceId, setSelectedSpaceId] = useState<string | null>(null);
  const activeSpace = selectedSpaceId ? mockSpaces.find((s) => s.id === selectedSpaceId) : undefined;
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

        {activeSpace && (
          <div className="mb-2 w-full">
            <SpaceFocusCard space={activeSpace} onClear={() => setSelectedSpaceId(null)} />
          </div>
        )}

        <div className="mt-4">
          <ChatComposer
            input={input}
            onInputChange={setInput}
            onSend={send}
            onSelectSpace={(sp) => setSelectedSpaceId(sp.id)}
            onAroundMe={() => flash(dict.home.aroundMeSoonToast)}
            dict={dict}
            autoFocus
          />
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

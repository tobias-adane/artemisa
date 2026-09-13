'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { SquarePen } from 'lucide-react';
import { PageHeader } from '@/components/artemisa/page-header';
import { AlertBanner } from '@/components/artemisa/alert-banner';
import { SpaceCard } from '@/components/artemisa/space-card';
import { ChatComposer } from '@/components/artemisa/chat-composer';
import { mockActivity, mockSpaces, mockThreads, mockUser } from '@/lib/mock-data';
import { useI18n } from '@/lib/i18n/context';
import type { Dictionary } from '@/lib/i18n/es';
import { useDay1 } from '@/lib/day1';
import { useChatThread } from '@/lib/use-chat';
import { useIsMobile } from '@/lib/use-mobile';
import { CHAT_SEED_KEY } from '@/lib/chat-seed';

function greetingFor(date: Date, dict: Dictionary) {
  const h = date.getHours();
  if (h < 12) return dict.home.greetingMorning;
  if (h < 20) return dict.home.greetingAfternoon;
  return dict.home.greetingNight;
}

export default function HomePage() {
  const router = useRouter();
  const { dict } = useI18n();
  const isMobile = useIsMobile();
  const { messages, thinking, sendMessage, reset, context, setContext } = useChatThread(dict);
  const [input, setInput] = useState('');
  const [toast, setToast] = useState('');

  const day1 = useDay1();
  const QUICK_ACTIONS = day1 ? [dict.home.quick1, dict.home.quick2] : [dict.home.quick1, dict.home.quick2, dict.home.quick3];
  const greeting = useMemo(() => greetingFor(new Date(), dict), [dict]);
  const conversing = messages.length > 0 || thinking;

  const attentionThread = day1 ? undefined : mockThreads.find((t) => t.classification === 'attention' && !t.escalated_to_reasoning);
  const attentionActivity = attentionThread ? mockActivity.find((a) => a.thread_id === attentionThread.id) : undefined;

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(''), 2400);
  }

  function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || thinking) return;
    if (isMobile) {
      const prefix = context ? `[${context.label}] ` : '';
      try {
        sessionStorage.setItem(CHAT_SEED_KEY, prefix + msg);
      } catch {
        // best-effort
      }
      setInput('');
      router.push('/chat');
      return;
    }
    sendMessage(msg);
    setInput('');
  }

  return (
    <div>
      <PageHeader
        title={dict.home.pageTitle}
        right={
          <button
            title={dict.home.newChatTooltip}
            onClick={reset}
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
            <p className="heading-display text-3xl text-foreground">{day1 ? dict.home.day1Subtitle : dict.home.subtitle}</p>
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

        {attentionThread && attentionActivity && !conversing && (
          <Link href="/activity" className="mt-6 w-full">
            <AlertBanner
              title={attentionActivity.title}
              description={attentionActivity.description}
              classification={attentionThread.classification}
            />
          </Link>
        )}

        <ChatComposer
          input={input}
          onInputChange={setInput}
          onSend={() => send()}
          context={context}
          onSetContext={setContext}
          onAroundMe={() => flash(dict.home.aroundMeSoonToast)}
          dict={dict}
        />

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
              <SpaceCard key={space.id} space={space} moreTooltip={dict.spaces.moreTooltip} />
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

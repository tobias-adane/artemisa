'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowUp, Camera as CameraIcon, Globe, Mic, Paperclip, Plus, SquarePen } from 'lucide-react';
import { PageHeader } from '@/components/artemisa/page-header';
import { AlertBanner } from '@/components/artemisa/alert-banner';
import { SpaceCard } from '@/components/artemisa/space-card';
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
import { mockActivity, mockSpaces, mockThreads, mockUser } from '@/lib/mock-data';
import { useI18n, format } from '@/lib/i18n/context';
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
  const { messages, thinking, sendMessage, reset } = useChatThread(dict);
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
      try {
        sessionStorage.setItem(CHAT_SEED_KEY, msg);
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

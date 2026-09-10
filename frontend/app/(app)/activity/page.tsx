'use client';

import { useState } from 'react';
import { AlignJustify, EllipsisVertical, MessageCircle, MessageSquareMore, Option, Phone, Share } from 'lucide-react';
import { PageHeader } from '@/components/artemisa/page-header';
import { mockActivity, mockThreads, STATUS_COLOR_VAR, STATUS_LABEL } from '@/lib/mock-data';
import { useI18n } from '@/lib/i18n/context';

export default function ActivityPage() {
  const { dict } = useI18n();
  const [reasonOpen, setReasonOpen] = useState<Record<string, boolean>>({});
  const [moreOpenId, setMoreOpenId] = useState<string | null>(null);

  const MORE_ITEMS = [
    { key: 'reasoning', icon: AlignJustify, label: dict.activity.itemReasoning },
    { key: 'thread', icon: Option, label: dict.activity.itemThread },
    { key: 'share', icon: Share, label: dict.activity.itemShare },
    { key: 'comments', icon: MessageSquareMore, label: dict.activity.itemComments },
  ] as const;

  return (
    <div>
      <PageHeader title={dict.activity.pageTitle} />
      <main className="mx-auto max-w-2xl px-6 pb-16 pt-8 sm:px-14">
        <div className="mb-1.5 text-sm text-muted-foreground">{dict.activity.subtitle}</div>
        <h1 className="heading-display mb-8 text-4xl">{dict.activity.headline}</h1>

        {mockActivity.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-[#d4d4d4] px-6 py-14 text-center">
            <div className="heading-display text-xl">{dict.activity.emptyTitle}</div>
            <p className="mx-auto mt-2.5 max-w-[42ch] text-[13.5px] leading-relaxed text-muted-foreground">
              {dict.activity.emptyBody}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-12">
            {mockActivity
              .slice()
              .reverse()
              .map((e) => {
                const thread = e.thread_id ? mockThreads.find((t) => t.id === e.thread_id) : undefined;
                const classification = thread?.classification ?? 'normal';
                const reasoning = thread?.reasoning ?? dict.activity.defaultReasoning;
                const open = !!reasonOpen[e.id];

                return (
                  <div key={e.id} className="flex animate-fade-up gap-5">
                    <span className="h-fit flex-none rounded-full border border-[#d4d4d4] px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                      {new Date(e.timestamp).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false })}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="text-[15.5px] font-semibold">{e.title}</div>
                          <p className="mt-1.5 text-[13.5px] leading-relaxed text-muted-foreground">{e.description}</p>
                        </div>
                        <div className="relative flex-none">
                          <button
                            title={dict.activity.moreTooltip}
                            onClick={() => setMoreOpenId((id) => (id === e.id ? null : e.id))}
                            className="flex h-4 w-4 items-center justify-center text-muted-foreground hover:text-foreground"
                          >
                            <EllipsisVertical className="h-4 w-4" />
                          </button>
                          {moreOpenId === e.id && (
                            <>
                              <div className="fixed inset-0 z-[65]" onClick={() => setMoreOpenId(null)} />
                              <div className="absolute right-0 top-[calc(100%+6px)] z-[70] w-[214px] rounded-[22px] border border-border bg-background p-1 shadow-lg">
                                <div className="px-2 py-1.5 text-xs text-muted-foreground">{dict.activity.moreOptions}</div>
                                {MORE_ITEMS.map((mi) => (
                                  <button
                                    key={mi.key}
                                    onClick={() => {
                                      setMoreOpenId(null);
                                      if (mi.key === 'reasoning') setReasonOpen((o) => ({ ...o, [e.id]: !o[e.id] }));
                                    }}
                                    className="flex w-full items-center gap-2.5 rounded-xl px-2 py-1.5 text-left text-sm text-foreground hover:bg-secondary"
                                  >
                                    <mi.icon className="h-4 w-4 flex-none" />
                                    <span className="flex-1">{mi.label}</span>
                                  </button>
                                ))}
                              </div>
                            </>
                          )}
                        </div>
                      </div>

                      <div className="mt-3.5 aspect-[16/10] w-full rounded-3xl border border-border bg-secondary" />

                      {open && (
                        <div className="mt-3">
                          <div className="text-xs font-medium text-muted-foreground">{dict.activity.whyMattered}</div>
                          <p className="mt-2 max-w-[520px] text-[12.5px] leading-relaxed text-muted-foreground">{reasoning}</p>
                        </div>
                      )}

                      <div className="mt-4 flex flex-wrap items-center justify-between gap-2.5">
                        <div className="inline-flex items-center rounded-full px-3 py-1.5" style={{ boxShadow: 'inset 0 0 0 1px #d4d4d4' }}>
                          <span className="text-xs font-medium" style={{ color: STATUS_COLOR_VAR[classification] }}>
                            {STATUS_LABEL[classification]}
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <button className="inline-flex h-8 items-center gap-1.5 rounded-full border border-border px-3 text-[13px] font-medium hover:bg-secondary">
                            <Phone className="h-3.5 w-3.5" /> {dict.activity.requestHelp}
                          </button>
                          <button className="inline-flex h-8 items-center gap-1.5 rounded-full bg-primary px-3 text-[13px] font-medium text-primary-foreground hover:bg-primary/90">
                            <MessageCircle className="h-3.5 w-3.5" /> {dict.activity.askAnything}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </main>
    </div>
  );
}

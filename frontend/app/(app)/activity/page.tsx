'use client';

import { useState } from 'react';
import { AlignJustify, MessageSquareMore, Option, Share } from 'lucide-react';
import { PageHeader } from '@/components/artemisa/page-header';
import { AlertBanner } from '@/components/artemisa/alert-banner';
import { ThreadCard } from '@/components/artemisa/thread-card';
import { mockActivity, mockLayers, mockSpaces, mockThreads } from '@/lib/mock-data';
import { useI18n } from '@/lib/i18n/context';
import { useDay1 } from '@/lib/day1';

type Panel = 'reasoning' | 'thread';

export default function ActivityPage() {
  const { dict } = useI18n();
  const day1 = useDay1();
  const [panelOpen, setPanelOpen] = useState<Record<string, Panel | undefined>>({});
  const [moreOpenId, setMoreOpenId] = useState<string | null>(null);

  const attentionThread = day1 ? undefined : mockThreads.find((t) => t.classification === 'attention' && !t.escalated_to_reasoning);
  const attentionActivity = attentionThread ? mockActivity.find((a) => a.thread_id === attentionThread.id) : undefined;
  const visibleActivity = day1 ? [] : mockActivity;

  const MORE_ITEMS = [
    { key: 'reasoning' as const, icon: AlignJustify, label: dict.activity.itemReasoning },
    { key: 'thread' as const, icon: Option, label: dict.activity.itemThread },
    { key: 'share' as const, icon: Share, label: dict.activity.itemShare },
    { key: 'comments' as const, icon: MessageSquareMore, label: dict.activity.itemComments },
  ];

  return (
    <div>
      <PageHeader title={dict.activity.pageTitle} />
      <main className="mx-auto max-w-2xl px-6 pb-16 pt-8 sm:px-14">
        <div className="mb-1.5 text-sm text-muted-foreground">{dict.activity.subtitle}</div>
        <h1 className="heading-display mb-8 text-4xl">{dict.activity.headline}</h1>

        {attentionThread && attentionActivity && (
          <div className="mb-8">
            <AlertBanner
              title={attentionActivity.title}
              description={attentionActivity.description}
              classification={attentionThread.classification}
            />
          </div>
        )}

        {visibleActivity.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-[#d4d4d4] px-6 py-14 text-center">
            <div className="heading-display text-xl">{day1 ? dict.activity.day1Title : dict.activity.emptyTitle}</div>
            <p className="mx-auto mt-2.5 max-w-[42ch] text-[13.5px] leading-relaxed text-muted-foreground">
              {day1 ? dict.activity.day1Body : dict.activity.emptyBody}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-12">
            {visibleActivity
              .slice()
              .reverse()
              .map((e) => {
                const thread = e.thread_id ? mockThreads.find((t) => t.id === e.thread_id) : undefined;
                const threadLayers = thread ? mockLayers.filter((l) => thread.layers.includes(l.id)) : [];
                const threadSpace = thread ? mockSpaces.find((s) => s.id === thread.space_id) : undefined;
                const items = thread && threadLayers.length > 0 ? MORE_ITEMS : MORE_ITEMS.filter((mi) => mi.key !== 'thread');

                return (
                  <ThreadCard
                    key={e.id}
                    entry={e}
                    thread={thread}
                    threadLayers={threadLayers}
                    threadSpace={threadSpace}
                    moreItems={items}
                    moreOpen={moreOpenId === e.id}
                    onToggleMore={() => setMoreOpenId((id) => (id === e.id ? null : e.id))}
                    onCloseMore={() => setMoreOpenId(null)}
                    panel={panelOpen[e.id]}
                    onSelectPanel={(key) => setPanelOpen((o) => ({ ...o, [e.id]: o[e.id] === key ? undefined : key }))}
                    dict={dict.activity}
                  />
                );
              })}
          </div>
        )}
      </main>
    </div>
  );
}

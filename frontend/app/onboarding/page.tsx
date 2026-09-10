'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { useI18n, format } from '@/lib/i18n/context';

const STEPS = ['personal', 'home', 'contacts', 'space', 'done'] as const;

const IP_RE = /^(\d{1,3}\.){3}\d{1,3}$/;

export default function OnboardingPage() {
  const router = useRouter();
  const { dict } = useI18n();
  const HOME_TYPES = [
    { key: 'house', label: dict.onboarding.homeTypes.house },
    { key: 'apartment', label: dict.onboarding.homeTypes.apartment },
    { key: 'small_business', label: dict.onboarding.homeTypes.small_business },
  ] as const;
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [homeType, setHomeType] = useState<(typeof HOME_TYPES)[number]['key']>('house');
  const [hasChildren, setHasChildren] = useState(false);
  const [customInstructions, setCustomInstructions] = useState('');
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('+54 9 ');
  const [spaceName, setSpaceName] = useState('');
  const [camIp, setCamIp] = useState('');
  const [camState, setCamState] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle');

  const key = STEPS[step];
  const first = name.trim().split(/\s+/)[0] || dict.onboarding.defaultName;

  function testCamera(ip: string) {
    setCamIp(ip);
    if (!IP_RE.test(ip.trim())) {
      setCamState('idle');
      return;
    }
    setCamState('testing');
    setTimeout(() => {
      // 192.168.1.1 deliberately reproduces the connection-error state.
      setCamState(ip.trim() === '192.168.1.1' ? 'error' : 'ok');
    }, 900);
  }

  function advance() {
    if (step === STEPS.length - 1) {
      router.push('/home');
      return;
    }
    setStep((s) => s + 1);
  }

  const canContinue =
    key !== 'space' || camState === 'ok' || camState === 'idle';

  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary/40 px-5 py-8">
      <div className="w-full max-w-lg rounded-[26px] border border-border bg-background p-1 shadow-lg">
        <div className="rounded-[22px] bg-secondary/60 px-9 py-9">
          <div className="flex items-center justify-between">
            {step > 0 ? (
              <button onClick={() => setStep((s) => Math.max(0, s - 1))} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
                <ChevronLeft className="h-3.5 w-3.5" /> {dict.onboarding.back}
              </button>
            ) : (
              <span />
            )}
            <div className="flex gap-1">
              {STEPS.map((_, i) => (
                <span key={i} className={`h-1 rounded-full transition-all ${i === step ? 'w-4 bg-primary' : i < step ? 'w-1 bg-primary' : 'w-1 bg-border'}`} />
              ))}
            </div>
          </div>

          <h1 className="heading-display mt-6 text-[28px] leading-tight">
            {key === 'personal' && dict.onboarding.stepPersonalTitle}
            {key === 'home' && dict.onboarding.stepHomeTitle}
            {key === 'contacts' && dict.onboarding.stepContactsTitle}
            {key === 'space' && dict.onboarding.stepSpaceTitle}
            {key === 'done' && format(dict.onboarding.stepDoneTitle, { name: first })}
          </h1>

          {key === 'personal' && (
            <div className="mt-6">
              <label className="mb-1.5 block text-xs font-semibold">{dict.onboarding.nameLabel}</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={dict.onboarding.namePlaceholder} />
            </div>
          )}

          {key === 'home' && (
            <div className="mt-5 flex flex-col gap-5">
              <div>
                <label className="mb-1.5 block text-xs font-semibold">{dict.onboarding.homeTypeLabel}</label>
                <div className="flex flex-wrap gap-2">
                  {HOME_TYPES.map((h) => (
                    <button
                      key={h.key}
                      onClick={() => setHomeType(h.key)}
                      className={`h-8 rounded-full border px-3.5 text-[12.5px] font-medium ${
                        homeType === h.key ? 'border-[#d4d4d4] bg-background text-foreground' : 'border-border text-muted-foreground'
                      }`}
                    >
                      {h.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between rounded-2xl border border-border bg-background p-3.5">
                <div>
                  <div className="text-[13.5px] font-semibold">{dict.onboarding.hasChildrenLabel}</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">{dict.onboarding.hasChildrenHint}</div>
                </div>
                <Switch checked={hasChildren} onCheckedChange={setHasChildren} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold">{dict.onboarding.concernsLabel}</label>
                <textarea
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  placeholder={dict.onboarding.concernsPlaceholder}
                  className="min-h-[96px] w-full resize-none rounded-2xl border border-border bg-background p-3 text-sm outline-none"
                />
              </div>
            </div>
          )}

          {key === 'contacts' && (
            <div className="mt-5 flex flex-col gap-4">
              <p className="text-sm leading-relaxed text-muted-foreground">
                {dict.onboarding.contactsBody}
              </p>
              <div>
                <label className="mb-1.5 block text-xs font-semibold">{dict.onboarding.contactNameLabel}</label>
                <Input value={contactName} onChange={(e) => setContactName(e.target.value)} placeholder={dict.onboarding.contactNamePlaceholder} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold">{dict.onboarding.contactPhoneLabel}</label>
                <Input value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} placeholder={dict.onboarding.contactPhonePlaceholder} />
              </div>
            </div>
          )}

          {key === 'space' && (
            <div className="mt-5 flex flex-col gap-4">
              <p className="text-sm leading-relaxed text-muted-foreground">
                {dict.onboarding.spaceBody}
              </p>
              <div>
                <label className="mb-1.5 block text-xs font-semibold">{dict.onboarding.spaceNameLabel}</label>
                <Input value={spaceName} onChange={(e) => setSpaceName(e.target.value)} placeholder={dict.onboarding.spaceNamePlaceholder} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold">{dict.onboarding.camIpLabel}</label>
                <Input value={camIp} onChange={(e) => testCamera(e.target.value)} placeholder={dict.onboarding.camIpPlaceholder} />
              </div>
              {camState === 'testing' && <p className="text-xs text-muted-foreground">{dict.onboarding.testingConnection}</p>}
              {camState === 'ok' && <p className="text-xs font-medium text-[var(--status-normal)]">{dict.onboarding.connectedOk}</p>}
              {camState === 'error' && (
                <div className="rounded-2xl border border-[#f0d4d4] bg-[#fdf2f2] p-3.5">
                  <p className="text-[13px] font-medium text-[#dc2626]">{dict.onboarding.connectFailedTitle}</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{dict.onboarding.connectFailedBody}</p>
                  <button
                    onClick={() => testCamera(camIp)}
                    className="mt-2.5 inline-flex items-center gap-1.5 text-xs font-medium text-foreground underline underline-offset-2"
                  >
                    <RefreshCw className="h-3 w-3" /> {dict.onboarding.retry}
                  </button>
                </div>
              )}
            </div>
          )}

          {key === 'done' && (
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              {dict.onboarding.doneBody}
            </p>
          )}

          <Button onClick={advance} disabled={!canContinue} className="mt-8 w-full">
            {key === 'done' ? dict.onboarding.goToArtemisa : dict.onboarding.continueBtn}
          </Button>
        </div>
      </div>
    </div>
  );
}

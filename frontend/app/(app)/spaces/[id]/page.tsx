'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ChevronLeft, FileText, MessageCircle, MoreHorizontal, Pencil, RefreshCw, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { CameraStatus } from '@/components/artemisa/camera-status';
import { mockSpaces } from '@/lib/mock-data';
import { useI18n, format } from '@/lib/i18n/context';
import { useBackendUser } from '@/lib/use-backend-user';
import { listSpaces } from '@/lib/api';
import type { SpacePublic } from '@/lib/types/artemisa-types';

type ModalKind = 'instructions' | 'edit' | null;

export default function SpaceDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { dict } = useI18n();
  const { userId, available } = useBackendUser();
  const [backendSpaces, setBackendSpaces] = useState<SpacePublic[]>([]);
  const [reconnected, setReconnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [toast, setToast] = useState('');
  const [modal, setModal] = useState<ModalKind>(null);
  const [instructions, setInstructions] = useState('');
  const [nameField, setNameField] = useState('');
  const [spaceName, setSpaceName] = useState<string | null>(null);

  useEffect(() => {
    if (!available) return;
    let cancelled = false;
    listSpaces(userId).then((res) => {
      if (!cancelled && res.ok) setBackendSpaces(res.data);
    });
    return () => {
      cancelled = true;
    };
  }, [available, userId]);

  const allSpaces = [...backendSpaces, ...mockSpaces];
  const space = allSpaces.find((s) => s.id === params.id) ?? mockSpaces[0];
  const displayName = spaceName ?? space.name;
  const isOffline = space.status === 'offline' && !reconnected;

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(''), 2200);
  }

  function reconnect() {
    setReconnecting(true);
    flash(dict.spaceDetail.reconnectingToast);
    setTimeout(() => {
      setReconnecting(false);
      setReconnected(true);
      flash(dict.spaceDetail.reconnectedToast);
    }, 1300);
  }

  function openInstructions() {
    setNameField('');
    setModal('instructions');
  }

  function openEdit() {
    setNameField(displayName);
    setModal('edit');
  }

  function saveInstructions() {
    setModal(null);
    flash(dict.spaceDetail.instructionsToast);
  }

  function saveEdit() {
    if (!nameField.trim()) return;
    setSpaceName(nameField.trim());
    setModal(null);
    flash(dict.spaceDetail.editToast);
  }

  function deleteSpace() {
    flash(dict.spaceDetail.deleteToast);
    setTimeout(() => router.push('/spaces'), 1000);
  }

  return (
    <div>
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-transparent bg-background/85 px-4 backdrop-blur">
        <button onClick={() => router.push('/spaces')} className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="rounded-full border border-border bg-background px-4 py-2 text-xs font-medium">{displayName}</div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button title={dict.spaceDetail.moreTooltip} className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-foreground hover:text-foreground">
              <MoreHorizontal className="h-4 w-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-[206px]">
            <DropdownMenuItem onClick={openInstructions}>
              <FileText className="h-4 w-4" /> {dict.spaceDetail.menuInstructions}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={openEdit}>
              <Pencil className="h-4 w-4" /> {dict.spaceDetail.menuEdit}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={deleteSpace} className="text-[var(--status-emergency)] focus:bg-[#fef2f2] focus:text-[var(--status-emergency)]">
              <Trash2 className="h-4 w-4" /> {dict.spaceDetail.menuDelete}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>

      <main className="mx-auto max-w-3xl px-5 pb-32 pt-2 sm:px-8">
        <div className="rounded-[26px] border border-border bg-secondary p-1">
          <div className="h-[360px] rounded-[22px] border border-border bg-secondary sm:h-[520px]" />
        </div>

        <div className="mt-5">
          <CameraStatus label={isOffline ? dict.spaceDetail.offlineNote : reconnecting ? dict.spaceDetail.reconnectingNote : dict.spaceDetail.activeNote} />
        </div>

        <h1 className="heading-display mt-3.5 text-[28px] leading-tight">
          {isOffline
            ? dict.spaceDetail.offlineHeadline
            : format(dict.spaceDetail.calmHeadline, { name: displayName, genderSuffix: displayName.endsWith('a') ? 'a' : '' })}
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed text-muted-foreground">
          {isOffline ? dict.spaceDetail.offlineBody : dict.spaceDetail.calmBody}
        </p>

        {isOffline && (
          <Button onClick={reconnect} disabled={reconnecting} className="mt-4">
            <RefreshCw className={`h-3.5 w-3.5 ${reconnecting ? 'animate-spin' : ''}`} /> {dict.spaceDetail.reconnect}
          </Button>
        )}
      </main>

      <div className="fixed inset-x-0 bottom-24 z-30 flex justify-center">
        <Button onClick={() => router.push(`/home?space=${space.id}`)} className="rounded-full px-5 py-3 shadow-lg">
          <MessageCircle className="h-3.5 w-3.5" /> {dict.spaceDetail.askAnything}
        </Button>
      </div>

      {toast && (
        <div className="fixed bottom-24 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-primary px-3.5 py-2 text-xs font-medium text-primary-foreground shadow-lg">
          {toast}
        </div>
      )}

      <Dialog open={modal === 'instructions'} onOpenChange={(open) => !open && setModal(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dict.spaceDetail.instructionsModalTitle}</DialogTitle>
            <DialogDescription>{dict.spaceDetail.instructionsModalSubhead}</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3.5">
            <div>
              <label className="mb-1.5 block text-xs font-semibold">{dict.spaceDetail.instructionsFieldLabel}</label>
              <Input
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder={dict.spaceDetail.instructionsPlaceholder}
              />
            </div>
            <Button onClick={saveInstructions} className="mt-1">
              {dict.spaceDetail.instructionsSave}
            </Button>
            <p className="text-center text-xs text-muted-foreground">
              {dict.spaceDetail.instructionsFoot}{' '}
              <button onClick={() => setModal(null)} className="font-medium underline underline-offset-2 hover:text-foreground">
                {dict.spaceDetail.modalCancel}
              </button>
            </p>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={modal === 'edit'} onOpenChange={(open) => !open && setModal(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dict.spaceDetail.editModalTitle}</DialogTitle>
            <DialogDescription>{dict.spaceDetail.editModalSubhead}</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3.5">
            <div>
              <label className="mb-1.5 block text-xs font-semibold">{dict.spaceDetail.editFieldLabel}</label>
              <Input
                value={nameField}
                onChange={(e) => setNameField(e.target.value)}
                placeholder={dict.spaceDetail.editPlaceholder}
              />
            </div>
            <Button onClick={saveEdit} disabled={!nameField.trim()} className="mt-1">
              {dict.spaceDetail.editSave}
            </Button>
            <p className="text-center text-xs text-muted-foreground">
              {dict.spaceDetail.editFoot}{' '}
              <button onClick={() => setModal(null)} className="font-medium underline underline-offset-2 hover:text-foreground">
                {dict.spaceDetail.modalCancel}
              </button>
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

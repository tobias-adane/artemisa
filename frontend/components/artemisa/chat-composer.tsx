'use client';

import { ArrowUp, Camera as CameraIcon, Globe, Mic, Paperclip, Plus } from 'lucide-react';
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
import { iconForSpace } from '@/lib/space-icons';
import type { SpacePublic } from '@/lib/types/artemisa-types';
import type { Dictionary } from '@/lib/i18n/es';

/**
 * Composer de Home y Chat — mismo input en ambas pantallas. Elegir un
 * espacio en "Espacios" NO agrega un chip de texto acá adentro — el
 * caller (Home/Chat) lo muestra como una miniatura flotante arriba del
 * composer (ver components/artemisa/space-focus-card.tsx), igual que
 * una foto adjunta.
 */
export function ChatComposer({
  input,
  onInputChange,
  onSend,
  onSelectSpace,
  onAroundMe,
  autoFocus = false,
  dict,
}: {
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onSelectSpace: (space: SpacePublic) => void;
  onAroundMe: () => void;
  autoFocus?: boolean;
  dict: Dictionary;
}) {
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
    <div className="w-full rounded-[36px] border border-border bg-background p-4 shadow-[0_6px_28px_rgba(0,0,0,0.05)]">
      <Input
        value={input}
        onChange={(e) => onInputChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSend();
          }
        }}
        placeholder={dict.home.inputPlaceholder}
        className="h-auto border-none px-1 py-2 text-sm shadow-none focus-visible:ring-0"
        autoFocus={autoFocus}
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
                {mockSpaces.map((sp) => {
                  const Icon = iconForSpace(sp.id);
                  return (
                    <DropdownMenuItem key={sp.id} onClick={() => onSelectSpace(sp)}>
                      <Icon className="h-4 w-4" /> {sp.name}
                    </DropdownMenuItem>
                  );
                })}
              </DropdownMenuSubContent>
            </DropdownMenuSub>
            <DropdownMenuItem onClick={onAroundMe}>
              <Globe className="h-4 w-4" /> {dict.home.aroundMe}
              <span className="ml-auto rounded-full bg-[#eff6ff] px-1.5 py-0.5 text-[10px] font-semibold text-[#2563eb]">{dict.home.aroundMeBeta}</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <div className="flex-1" />
        {input.trim() ? (
          <button onClick={onSend} title={dict.home.sendTooltip} className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <ArrowUp className="h-3.5 w-3.5" />
          </button>
        ) : (
          <button title={dict.home.voiceTooltip} className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground">
            <Mic className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

'use client';

import { ArrowUp, Camera as CameraIcon, Globe, Mic, Paperclip, Plus, X } from 'lucide-react';
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
import type { ChatContext } from '@/lib/use-chat';
import type { Dictionary } from '@/lib/i18n/es';

/**
 * Composer de Home y Chat — mismo input en ambas pantallas (CLAUDE.md
 * §8/§9). Elegir un espacio en "Espacios" fija ese espacio como
 * `context` de la conversación: se muestra como chip (ícono + label +
 * quitar) acá arriba del input, y se antepone `[label] ` al mensaje al
 * enviar (ver lib/use-chat.ts). Es distinto de un archivo adjunto —
 * singular, con prefijo, no una lista de nombres al final.
 */
export function ChatComposer({
  input,
  onInputChange,
  onSend,
  context,
  onSetContext,
  onAroundMe,
  autoFocus = false,
  dict,
}: {
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  context: ChatContext;
  onSetContext: (context: ChatContext) => void;
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
      {context && (
        <div className="mb-2 flex flex-wrap gap-1.5 px-1">
          <span className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-border bg-secondary py-1 pl-2.5 pr-1 text-xs">
            <context.icon className="h-3.5 w-3.5 flex-none text-muted-foreground" />
            <span className="truncate">{context.label}</span>
            <button
              onClick={() => onSetContext(null)}
              title={dict.common.cancel}
              className="flex h-4.5 w-4.5 flex-none items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        </div>
      )}
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
                {mockSpaces.map((sp) => (
                  <DropdownMenuItem key={sp.id} onClick={() => onSetContext({ label: sp.name, icon: iconForSpace(sp.id) })}>
                    {sp.name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuSubContent>
            </DropdownMenuSub>
            <DropdownMenuItem onClick={onAroundMe}>
              <Globe className="h-4 w-4" /> {dict.home.aroundMe}
              <span className="ml-auto text-[11px] font-semibold text-[#2563eb]">{dict.home.aroundMeBeta}</span>
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

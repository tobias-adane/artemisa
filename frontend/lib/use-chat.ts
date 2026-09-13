'use client';

import { useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import type { Dictionary } from './i18n/es';

export type ChatMessage = { role: 'user' | 'assistant'; text: string };

/**
 * Contexto activo del composer — "estás preguntando sobre esto", no un
 * archivo adjunto. Se muestra como chip (ícono + label + quitar) y se
 * antepone como `[label] ` al mensaje al enviar. Distinto de los
 * attachments (plural, sin prefijo, van al final del mensaje).
 */
export type ChatContext = { label: string; icon: LucideIcon } | null;

export function replyFor(msg: string, dict: Dictionary) {
  const m = msg.toLowerCase();
  if (/(familia|chicos|quien esta|quién está|todo el mundo|family|kids|who.?s home)/.test(m)) return dict.home.replyFamily;
  if (/(actividad|paso|pasó|reciente|hoy|activity|happened|today)/.test(m)) return dict.home.replyActivity;
  if (/(pasando|ahora|estado|going on|status)/.test(m)) return dict.home.replyStatus;
  if (/(puerta|cerrad|llave|door|lock)/.test(m)) return dict.home.replyDoors;
  return dict.home.replyDefault;
}

/** Estado + lógica del hilo de chat, compartido entre Home (desktop) y Chat (mobile). */
export function useChatThread(dict: Dictionary) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [thinking, setThinking] = useState(false);
  const [context, setContext] = useState<ChatContext>(null);

  function sendMessage(text: string) {
    const msg = text.trim();
    if (!msg || thinking) return;
    const prefix = context ? `[${context.label}] ` : '';
    setMessages((m) => [...m, { role: 'user', text: prefix + msg }]);
    setThinking(true);
    setTimeout(() => {
      setMessages((m) => [...m, { role: 'assistant', text: replyFor(msg, dict) }]);
      setThinking(false);
    }, 900);
  }

  function reset() {
    setMessages([]);
    setThinking(false);
    setContext(null);
  }

  return { messages, thinking, sendMessage, reset, context, setContext };
}

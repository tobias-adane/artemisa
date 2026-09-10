'use client';

import { useState } from 'react';
import type { Dictionary } from './i18n/es';

export type ChatMessage = { role: 'user' | 'assistant'; text: string };

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

  function sendMessage(text: string) {
    const msg = text.trim();
    if (!msg || thinking) return;
    setMessages((m) => [...m, { role: 'user', text: msg }]);
    setThinking(true);
    setTimeout(() => {
      setMessages((m) => [...m, { role: 'assistant', text: replyFor(msg, dict) }]);
      setThinking(false);
    }, 900);
  }

  function reset() {
    setMessages([]);
    setThinking(false);
  }

  return { messages, thinking, sendMessage, reset };
}

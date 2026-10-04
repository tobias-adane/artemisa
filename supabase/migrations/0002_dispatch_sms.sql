-- Fase 0: los avisos salen por SMS hasta que exista la app (00-DECISIONES.md, 11).
-- Idempotente: se puede correr más de una vez.

alter type dispatch_channel add value if not exists 'sms';

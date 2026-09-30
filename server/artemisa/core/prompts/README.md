# Prompts

Generados desde `docs/04-MODELOS.md`, uno por archivo. Si cambian allá, se
actualizan acá (y al revés: cambiar un prompt se pregunta antes, ver
`CLAUDE.md`).

- `*.system.txt`: el mensaje de sistema de cada rol.
- `*.user.txt`: la plantilla del mensaje de usuario.
- `reason.user_extra.txt`: lo que `reason` agrega a la plantilla de `analyze`.
- `chat.thread_focus.txt`: lo que se agrega cuando la pregunta es sobre un thread.
- `analyze_hard` usa los mismos prompts que `analyze`.

Las llaves `{así}` son variables que completa el código. `chat.system.txt` se
reescribe antes de la Fase 1, cuando el Cloud Bridge empiece a grabar.

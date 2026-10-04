# Progreso

**Fase actual:** Fase 0, laboratorio.
**Paso en curso:** 12.
**Siguiente:** 13.

Al terminar cada paso: tests y chequeos limpios, marcar el paso acá y hacer
commit. Qué leer en cada paso: tabla de `CLAUDE.md`.

## Fase 0

- [x] 1. Esqueleto del repositorio, herramientas y CI (tipos, lint, tests y guardas).
- [x] 2. Supabase de laboratorio: migraciones, `lab_only` y `seed_demo.py`.
- [x] 3. Registro de modelos, clientes de proveedores, costo y `pipeline_runs`.
- [x] 4. Bridge: go2rtc en tmpfs, lector, entrega de un frame por segundo, canal de control con latido, `VIDEO_SOURCE`.
- [x] 5. Paso 1 y Paso 2a en la API: endpoint de frames, movimiento, descripción, estado del space.
- [x] 6. Sesionización y threads en composing.
- [x] 7. `LISTEN` / `NOTIFY`, scheduler y Paso 2b.
- [x] 8. Paso 3 con refuerzo.
- [x] 9. Paso 4 con notificaciones y `dispatches`; salud de la caja y de las cámaras.
- [x] 10. `artemisa-lab report`.
- [x] 11. App: RN Reusables, tokens, fuentes, textos, layout, modo laboratorio.
- [ ] 12. App: Home en tiempo real.
- [ ] 13. App: Detalle.
- [ ] 14. App: Feed en vivo y lectura en vivo.
- [ ] 15. App: voz y chat (pedir el diseño del chat antes).
- [ ] 16. App: Conectar cámara.
- [ ] 17. Correr el laboratorio y medir los criterios de éxito.

## Notas

(Lo que haga falta recordar entre sesiones: decisiones chicas, bloqueos, qué
quedó a medias.)

- **Paso 12: lectura de la base en modo lab.** Para que la app lea la base con
  la clave anónima hace falta decidir una política de lectura para el
  laboratorio. No está escrita.
- **Paso 12: tipos de la base.** `mobile/lib/types/db.ts` no se generó en el
  paso 11: la CLI de Supabase necesita la imagen de pg-meta y la red de la
  sesión no la deja bajar. Generarlo con la CLI contra un Postgres local con
  las migraciones aplicadas y tipar `createClient<Database>` en
  `lib/supabase.ts`.
- **App, dependencias por paso.** En el paso 11 entró solo lo que usa la base.
  `expo-video`, `expo-notifications`, `expo-device`, `expo-audio`,
  `expo-linear-gradient`, `expo-speech-recognition` y Sentry se instalan en el
  paso que los usa (Sentry, cuando haya DSN, con la config de abajo).
- **App, primitivas.** Si `reactnativereusables.com` está bloqueado por la red,
  el JSON del registro está en GitHub
  (`founded-labs/react-native-reusables`, `apps/docs/public/r/nativewind/`).
  Así se agregaron las del paso 11, sin editar más que los imports.
- **Canal de control: comandos de la nube.** El lado servidor está desde el
  paso 9 (`hello`, `heartbeat`, `health`). Los comandos se suman encima:
  `start_stream` y `stop_stream` en el paso 14, `add_camera` y `remove_camera`
  en el paso 16.
- **Al agregar Sentry** (entra en la Fase 0 según `08`, pero ningún paso lo
  nombra): configurarlo con `include_local_variables=False`,
  `send_default_pii=False` y `max_request_body_size="never"`. `jpeg`, `body` y
  `messages` (con el base64) son variables locales en `frames.py`,
  `describe.py` y `app.py`, y Sentry las manda por defecto. Es lo que ya pide
  `06`, Observabilidad. Revisión de privacidad del paso 5, hallazgo 3.
- **Al haber Dockerfile** (hoy solo go2rtc corre en Docker; el servicio `lab` de
  `06` todavía no existe): correr la API con `read_only: true` y tmpfs solo para
  los logs. El test de la guarda de `05` simula el solo-lectura a nivel Python y
  no ve escrituras de código nativo. Revisión de privacidad del paso 5,
  hallazgo 4.
- **Límite conocido de los pasos 7 y 8: nadie actúa todavía.** El Paso 3 guarda
  su decisión y calcula el nivel (`resolve_action_level`), pero solo lo
  loguea: `act` es del paso 9. Un `attention` queda sin acción hasta el paso 9,
  y también el `informar` o el aviso de resguardo cuando falla el Paso 3. Con `ANALYSIS_MAX_FAILURES` fallos y un flag
  urgente, la narrativa pasa a `fallback.urgentNarrative`, pero el aviso de
  resguardo se ejecuta recién en el paso 9.
- **Worker en el laboratorio.** Corre dentro de `artemisa-lab` y las señales
  `analyze_now` y `boost` van por memoria. `LISTEN` / `NOTIFY` está hecho y probado contra
  Postgres para cuando el worker sea otro proceso. El punto de entrada
  `artemisa-worker` no está en `pyproject.toml` todavía.
- **Para revisar en el laboratorio:** `last_analyzed_at` es la hora al terminar
  el análisis. Un layer capturado antes de esa hora pero guardado después (la
  descripción tarda unos segundos) no vuelve a marcar el thread como pendiente.
  La regla de palabras vigiladas no ve palabras de 3 letras ("dog", "gas") y no
  traduce: si las custom instructions están en inglés y los layers en
  castellano, casi no coincide. Además, palabras comunes como "door" o "home"
  pueden mandar casi todo a `analyze_hard`. Medirlo con `report` (paso 10).
- **Historia de 48 h del Paso 3 sin tope (pasos 10 y 17).** En el laboratorio
  entra entera al prompt de `reason`. En una casa real con mucha actividad
  puede crecer mucho: medir `input_tokens` de `reason` en `pipeline_runs` antes
  de la Fase 1.

- **Ida y vuelta entre el Paso 2b y el Paso 3 (pasos 10 y 17).** Si el Paso 2b
  sigue diciendo `attention` y el Paso 3 decidió `normal`, cada reanálisis es
  "más grave" y vuelve a mandar el thread al Paso 3 (regla de 03). En la prueba
  de punta a punta con el modelo simulado, un thread de 4 minutos se razonó 3
  veces, con un solo refuerzo. Además, la confianza baja del primer análisis
  queda y los siguientes van a `analyze_hard`. Medir cuánto pasa y cuánto
  cuesta.

### Para el paso 17 (hallazgos de las pruebas del paso 7)

1. **Un desconocido sale `attention` por la instrucción nocturna.** Con el
   contexto de una casa, todo thread con una persona desconocida salió
   `attention` (0,78 a 0,86). Con el contexto de la escuela salió `normal`. Con
   esa confianza no pasa por el Paso 3 (umbral `LOW_CONFIDENCE` 0,6): entra
   solo si el desconocido vuelve en otro thread dentro de la hora o si el
   análisis pide `escalate`.
2. **Las palabras vigiladas mandan casi todo a `analyze_hard`** cuando
   comparten palabras comunes del lugar (por ejemplo "staircase").
3. **Falso positivo del Paso 1:** un frame de movimiento sin persona (una
   puerta, una luz) abrió un thread.
4. **"Avisame si alguien que no conozco viene" no se puede responder** mirando
   un frame sin reconocimiento de personas. Hay que decidir cómo se pide esa
   instrucción, o cómo responde Artemisa cuando no puede saberlo.
5. **La razón de cada escalada no se guarda.** `artemisa-lab report` cuenta
   las llamadas a `analyze_hard` y las corridas del Paso 3 por thread, pero no
   por qué. Guardar la razón de `analyze_hard` y el disparador del Paso 3
   pediría una columna nueva en `pipeline_runs`: decidirlo antes del
   laboratorio con casa real. El esquema no se tocó.
6. **Límites del informe** (paso 10): los frames que el Paso 1 descarta no pasan
   por la base, así que solo se cuentan los descriptos (`describe` y `state`).
   Los tokens de imagen salen "sin dato" porque `visual_tokens` viene vacío.
   Las horas de cámara son una estimación (del primer al último
   `pipeline_run` de cada space, en sesiones cortadas por huecos de más de 15
   minutos); `--camera-hours` acepta el valor exacto.

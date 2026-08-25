# ARTEMISA — 01 · DEFINICIÓN DE PRODUCTO

---

## 1. QUÉ ES

**Artemisa no analiza cámaras. Comprende lo que ocurre en tu hogar.**

Es una capa de inteligencia que se conecta a las cámaras IP que una
familia ya tiene. Convierte video en descripciones de texto,
construye contexto sobre la rutina de ese hogar específico, y actúa
automáticamente cuando detecta algo que realmente importa — sin
almacenar video ni imagen en ningún punto del proceso.

### Propuesta de valor

> **Artemisa hace que las familias dejen de preocuparse.**

La emoción que vende no es "seguridad" en abstracto — es la
tranquilidad de saber que, si algo pasa, va a haber una respuesta.

### La premisa operativa

> "La cámara por sí sola no puede hacer nada. Lo único que deja es
> la evidencia de lo que pasó. Se necesita que se tome acción en el
> preciso instante en el cual las cosas suceden, no 20 minutos
> después."

**Regla de decisión de producto:** si una feature, pantalla o flujo
no ayuda a que la respuesta sea más rápida o más clara, no es
prioritaria. Es una app de reacción, no de vigilancia pasiva.

---

## 2. EL PROBLEMA QUE RESUELVE

Las cámaras tradicionales producen información, no comprensión.
Detectan movimiento, graban video, envían notificaciones — pero
dejan al usuario el trabajo importante:

- ¿Quién entró?
- ¿Es alguien de la casa?
- ¿Es normal que esté ahí a esta hora?
- ¿Está pasando algo peligroso?
- ¿Tengo que hacer algo?

Artemisa resuelve esa última capa: **convertir observaciones en
contexto, y contexto en decisiones.**

### Los dos fracasos del mercado actual

| Enfoque | Falla |
|---|---|
| Alarmas / detección de movimiento | Fatiga de alertas. Tantos falsos positivos que el usuario deja de prestar atención. |
| Cámaras "inteligentes" (Ring, Nest) | Entienden algo de contexto, pero a costa de almacenar todo el video en la nube de una corporación. |

Artemisa resuelve las dos a la vez: entiende contexto **sin**
necesitar guardar video.

---

## 3. CICLO CONCEPTUAL

**Observar → Detectar → Comprender → Recordar → Razonar → Actuar**

| Etapa | Qué hace |
|---|---|
| Observar | Las cámaras proveen información del entorno |
| Detectar | Un sistema liviano identifica cambios relevantes. No tiene sentido mandar un living vacío a un modelo multimodal |
| Comprender | Cuando ocurre algo relevante, se genera información estructurada: **layers** (representaciones semánticas, puramente factuales) |
| Recordar | Los layers relacionados forman **threads** — un evento a través del tiempo. La memoria evita interpretar cada evento como si fuera el primero |
| Razonar | Cuando la situación lo requiere, se activa un modelo más potente. Su trabajo es resolver situaciones que necesitan comprensión contextual |
| Actuar | Ejecutar una acción definida por el usuario. La inteligencia no termina en la observación — termina en una acción útil |

---

## 4. FEATURES

### Primarias

**1. Accessible Protection**
Funciona con cualquier cámara IP compatible RTSP/ONVIF que la
familia ya tenga. Sin hardware nuevo, sin kit caro.

**2. Real-Time Understanding**
No son alertas de movimiento — es comprensión de lo que está
pasando a medida que ocurre, distinguiendo momentos cotidianos de
situaciones que necesitan atención.

**3. Contextual Intelligence**
Entiende qué pasó antes, qué está pasando ahora, y por qué importa.
Es lo que termina con la fatiga de alertas — el diferenciador más
importante de todo el producto.

**4. Auto Dispatch**
Cuando se detecta una emergencia real, contacta a servicios de
emergencia y a las personas de confianza automáticamente,
manteniendo al usuario informado. Es la feature de mayor
responsabilidad legal del producto.

### Secundarias

**5. Natural Interaction**
Chat en lenguaje natural: "¿cómo está mi familia?", "¿quién vino
hoy?" — respuestas generadas desde los threads reales del día.

**6. Living Memory**
En vez de grabaciones infinitas, un registro de eventos
significativos navegable por día. Nunca video crudo.

### Transversal: Privacy by Design

**"Lo que pasa en casa, se queda en casa."** No es una feature más —
es una restricción arquitectónica transversal. El video nunca se
persiste en ningún punto del pipeline.

---

## 5. LOS 4 NIVELES DE ACCIÓN

No todo evento relevante merece la misma respuesta. La acción está
jerarquizada:

| Nivel | Nombre | Qué hace |
|---|---|---|
| 1 | **Informar** | Relevante pero no urgente. Se registra en Activity, sin interrumpir |
| 2 | **Alertar** | Requiere atención del usuario ahora. Alert card simple, sin dispatch |
| 3 | **Contactar** | Mensajes o llamadas a una persona de confianza (no 911), con ventana de cancelación de 90s |
| 4 | **Emergencia** | Protocolos de emergencia real — 911 + contactos, vía Twilio, con ventana de cancelación de 30s |

### Regla de oro

> **Cuanto mayor el impacto de una acción, mayor debe ser el nivel
> de certeza requerido antes de ejecutarla.**

El sistema debe evitar decisiones irreversibles basadas en evidencia
débil. Toda escalada a Nivel 4 pasa obligatoriamente por el paso de
razonamiento profundo (Paso 3) antes de disparar Twilio.

### Mapeo con la clasificación técnica

Ver `docs/ARTEMISA_03_DATOS.md` sección 4 para el detalle completo
y `resolve_action_level()` en `backend/artemisa_models.py` para la
implementación. Resumen:

```
classification: normal    → alert_level 1 → informar
classification: attention → severity_score < 0.7  → alert_level 2 → alertar
                           → severity_score >= 0.7 → alert_level 3 → contactar
classification: emergency → SIEMPRE pasa por Paso 3 →
                             severity_high True  → alert_level 4 → emergencia
                             severity_high False → alert_level 3 → contactar (degradado)
```

Nivel 3 (Contactar) puede originarse tanto de `attention` con
severidad alta como de una `emergency` que el Paso 3 no confirmó —
en ambos casos nunca llama al 911, así que no requiere el paso de
razonamiento profundo, solo su propia ventana de cancelación.

---

## 6. IDENTIDAD DEL HOGAR (reconocimiento de personas)

**No es reconocimiento facial tradicional.**

Artemisa construye perfiles contextuales con evidencia acumulada:

- Características físicas generales
- Vestimenta
- Objetos que suele llevar
- Patrones de movimiento
- Horarios habituales
- Lugares que frecuenta dentro del hogar
- Relaciones declaradas por el usuario
- Historial de eventos

La lógica nunca es *"es esta cara"* — es *"la persona observada
coincide suficientemente con el perfil de alguien que vive acá."*

### Decisión de v1 (beta)

**No implementar reconocimiento facial biométrico.** Embeddings
faciales son datos biométricos, categoría sensible bajo la Ley
25.326 argentina y regulaciones equivalentes.

En su lugar: **reconocimiento por patrón descriptivo**. El modelo de
visión ya describe "una persona con remera azul, pelo corto" — el
análisis puede notar patrones de recurrencia basados en esas
descripciones + horario + contexto, sin identificar biométricamente
a nadie. Esto cubre el caso de uso central: distinguir "visita
recurrente esperada" de "presencia nueva no esperada".

Reconocimiento biométrico real, si se implementa después: solo
opt-in explícito por persona, nunca automático sobre visitantes.

**Pregunta abierta de producto (ver doc 04, tensión #4):** falta
validar si la fidelidad del patrón descriptivo alcanza para que el
usuario sienta que Artemisa "reconoce" a su familia de forma
creíble. Es la primera cosa a medir con la beta real.

---

## 7. TONO Y COMUNICACIÓN

### Idioma de la beta

**Español rioplatense (voseo), Argentina.** Toda la UI, las
narrativas generadas por el pipeline (`narrative`, `reasoning`) y
los mensajes de Twilio van en español. El set de copy validado y
autoritativo vive en `frontend/CLAUDE.md` — este documento mantiene
los ejemplos conceptuales en español; para el texto exacto a usar en
componentes, la fuente de verdad es ese archivo.

### La incertidumbre es válida

Artemisa nunca debería inventar certeza. En vez de:

> ❌ "Llegó tu hija."

Cuando la confianza no alcanza:

> ✅ "Parece que llegó tu hija, pero no estoy completamente segura."

La confianza del usuario importa más que aparentar precisión.

### Contextual y humano, nunca técnico

| ❌ Nunca | ✅ Siempre |
|---|---|
| "Movimiento detectado en cámara 3" | "Tu hija llegó hace 15 minutos. Está en su habitación." |
| "Persona detectada" | "Llegó tu marido." |
| "Sin eventos registrados" | "No pasó nada importante desde que te fuiste." |

### Reglas duras de copy

- **Nunca** mencionar "AI", "inteligencia artificial", "modelo",
  "vision model", "chain of thought" en ningún texto visible de la
  UI — ni labels, ni estados vacíos, ni tooltips, ni notificaciones
- Nunca dramatizar el peligro para generar urgencia de conversión
- El razonamiento de Artemisa se comunica en su voz humana, nunca
  como log de sistema — ver la distinción entre `Thread.reasoning`
  (humano, UI) y el `reasoning` interno de `EmergencyVerification`
  (técnico, nunca UI) en `docs/ARTEMISA_03_DATOS.md` sección 4

---

## 8. EL CONCEPTO DE TRANQUILIDAD

La tranquilidad no significa avisar de todo. Significa lo contrario:
filtrar el ruido y comunicar solamente lo que importa.

> La mejor experiencia no es recibir cien alertas.
> Es recibir una sola cuando realmente hacía falta.

### Métrica real del producto

No: *"¿cuántas cosas detectamos?"*

Sino: **"¿cuántas veces ayudamos al usuario a tomar una mejor
decisión?"**

---

## 9. EL CLIENTE DE V1

La visión de largo plazo es *"un lugar seguro para todos, en todos
lados"*. Pero v1 se enfoca en un solo perfil, en un solo país:

> **La familia clásica argentina: mamá, papá, y dos hijos (17 y 8
> años). Ambos padres trabajan, la casa queda sola durante el día.**
> **Beta lanza en Argentina — español rioplatense, +54, Ley 25.326
> como marco de referencia legal para datos personales.**

Usar este escenario como default en mocks, seed data, ejemplos de
copy, y casos de uso durante el desarrollo. No diseñar todavía para
"la abuela sola" o "el adolescente" — eso viene después de validar
con esta cuña.

---

## 10. ETHOS — LOS 8 PRINCIPIOS

1. **Comprender antes de actuar** — Detectar algo no significa
   entenderlo
2. **La tranquilidad antes que las notificaciones** — El producto
   debe reducir ansiedad, no producirla
3. **La privacidad por defecto** — La información del hogar
   pertenece al hogar
4. **La incertidumbre es válida** — Artemisa nunca debería inventar
   certeza
5. **Contexto antes que eventos aislados** — Un evento tiene
   significado dentro de una historia
6. **Inteligencia donde importa** — El cómputo debe usarse para
   resolver problemas, no para procesar información irrelevante
7. **Acción con propósito** — Toda acción debe existir porque mejora
   la seguridad o tranquilidad del usuario
8. **Tecnología invisible** — El usuario no debería necesitar
   entender cómo funciona Artemisa para beneficiarse de ella

---

## 11. QUÉ DEBE DEMOSTRAR EL MVP

Una sola idea:

> **Artemisa puede comprender lo que ocurre en un hogar y
> comunicarlo de una manera que una cámara tradicional no puede.**

La prioridad no es cantidad de features. Es demostrar que el sistema
puede pasar de:

**imagen → contexto → comprensión → tranquilidad.**

---

## 12. PRINCIPIO DE DECISIÓN

Ante cualquier decisión de producto no cubierta explícitamente,
aplicar en orden:

1. ¿Esto ayuda a que la respuesta ante algo real sea más rápida o
   más clara? → si sí, prioridad alta
2. ¿Le habla a la familia argentina con ambos padres trabajando y la
   casa sola? → si no, probablemente no es para v1
3. ¿El copy suena a alguien genuinamente preocupado por proteger, o
   a una empresa vendiendo miedo? → si es lo segundo, reescribir
4. ¿Esto agrega complejidad sin acercar al usuario a sentir "si algo
   pasa, va a haber una respuesta"? → si sí, cortar o simplificar
5. ¿La acción propuesta es proporcional al nivel de certeza que
   realmente hay? → nunca ejecutar un Nivel 4 con evidencia de
   Nivel 2

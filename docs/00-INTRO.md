# Artemisa: introducción al producto

**Leé esto primero.** Es la puerta de entrada al proyecto para cualquier sesión
de Claude: Claude Code (construir), Claude Design (diseñar pantallas) o un chat
nuevo. Cuenta la idea completa y dónde está cada detalle. No reemplaza a los
demás documentos: los resume y los ordena.

**Precedencia.** Los documentos 01 a 10 ya integran todas las decisiones del
27/9 (el registro está en `00-DECISIONES.md`). Si aparece una contradicción,
gana lo más nuevo y se avisa. Si algo no está claro, se pregunta; no se resuelve
inventando.

Actualizado: 27/9/2026.

---

## En una línea

Artemisa hace que las familias dejen de preocuparse por su casa: entiende lo
que ven sus cámaras y avisa solo cuando importa.

---

## La idea

Una cámara sola no hace nada: deja evidencia para que alguien la mire después.
Las cámaras tradicionales producen información, no comprensión. Mandan cien
notificaciones por día (el perro, una sombra, el delivery de los martes) y le
dejan a la familia el trabajo importante: ¿quién entró?, ¿es de la casa?, ¿es
normal a esta hora?, ¿tengo que hacer algo?

Artemisa invierte eso. Mira por la familia, entiende lo que pasa en el contexto
de esa casa y cuenta solo lo que vale la pena, en el momento en que pasa. La
mayoría de los días no interrumpe a nadie, y eso también es el producto.

Tres ideas sostienen todo:

1. **Comprender en lugar de mirar.** La app abre con lo que Artemisa entendió
   del día, no con una cámara. Mirar en vivo es una opción, no el punto de
   partida.
2. **El día es una línea.** Lo que pasa en una casa son historias en el tiempo,
   no eventos sueltos. Artemisa agrupa lo que ve en *threads* (momentos con
   principio y fin) y los muestra en una línea continua.
3. **Actuar con proporción.** Cuanto más fuerte es la acción, más certeza hace
   falta para tomarla.

Lo que se vende no es "seguridad": es **tranquilidad**. Nada del producto tiene
que parecer vigilancia.

---

## Para quién

- **Primer cliente:** una familia argentina donde los dos adultos trabajan y la
  casa queda sola de día.
- **Mercado:** Argentina primero, después Latinoamérica.
- **Hogar de demo** (para mocks, datos de prueba y ejemplos de copy):
  Alexander, titular de la cuenta; su pareja; Maya, 15 años, vuelve del colegio
  a la tarde; Luna, la perra, se queda en casa.

---

## Las tres piezas

```
CASA                                   NUBE                          TELÉFONO
Cámaras (cualquier marca, o un DVR)    Artemisa                       La app
        │                              · detecta movimiento           · la línea del día
        ▼                              · describe lo que ve           · el detalle de cada momento
Cloud Bridge  ── solo sale ──────────▶ · entiende y clasifica  ─────▶ · ver en vivo
· habla con cada cámara                · decide si avisar             · chat y voz
· sube a la nube lo necesario          · no guarda nada visual        · ver grabaciones
· guarda la grabación, cifrada
```

1. **Cloud Bridge:** el aparato que se enchufa al router. Conecta las cámaras
   con Artemisa.
2. **La nube:** donde vive toda la inteligencia.
3. **La app:** donde la familia ve, entiende y pregunta.

---

## Cloud Bridge

### Por qué existe

Las cámaras viven en la red privada de cada casa. Desde internet no se puede
llegar a ellas sin abrir puertos en el router, que es inseguro, complicado para
cualquier persona y en muchas conexiones (con CGNAT) directamente imposible.
Además, cada marca habla su propio idioma y casi todas funcionan solo con su
propia app.

El Cloud Bridge resuelve las dos cosas: vive adentro de la red de la casa, habla
con cada cámara en su idioma y se conecta con Artemisa siempre desde adentro
hacia afuera. No hay que tocar el router.

### Qué hace, y qué no

- **Es un puente, no una computadora.** Obtiene video de las cámaras y lo envía
  a la nube. No procesa: el análisis corre en la nube. Por eso el hardware es
  liviano y barato.
- **Compatibiliza.** Adentro corre go2rtc, un traductor de video que entiende
  los protocolos estándar (RTSP y ONVIF) y las marcas más comunes: Hikvision,
  Dahua, Tapo, Xiaomi y la mayoría de las genéricas. El resto del sistema lee
  siempre del bridge, nunca directo de una cámara, así que sumar una marca es
  configuración, no código.
- **Se conecta a un DVR o NVR existente.** Si la casa ya tiene un sistema de
  cámaras con grabador central, el bridge trae todos sus canales. Es la única
  forma de llegar a cámaras analógicas viejas, que no tienen IP propia.
- **Guarda la grabación en la casa**, cifrada, en una memoria interna. Sirve
  para familias con DVR o sin él: la grabación se ve solo desde la app del
  dueño. Ni la nube ni el propio bridge pueden verla.
- **Guarda las contraseñas de las cámaras**, cifradas. Nunca salen de la casa.
- **Solo abre conexiones salientes.** Nunca abre puertos de entrada.

### Conexión fácil

1. Se enchufa al lado del router: un cable de red y uno de corriente.
2. En la app se escanea el QR de la base. El bridge queda vinculado a la cuenta.
3. El bridge busca solo las cámaras de la casa, estén por cable o por Wi Fi, y
   la app muestra la lista con marca y modelo.
4. La familia elige cuáles conectar y escribe la contraseña de cada una.
5. Listo. Escribir la dirección de una cámara a mano queda como camino
   alternativo, para las que no aparecen solas.

Arranca solo cuando vuelve la luz, se actualiza solo y nadie tiene que tocarlo
nunca más.

### Cómo es

- Caja blanca de 120 × 120 × 34 mm, plástico satinado, esquinas muy
  redondeadas. Pensada para quedar a la vista en un living: parece un objeto de
  la casa, no un aparato de seguridad.
- Arriba: el logo y una línea de luz de estado.
- Atrás: red, corriente por USB-C, ranura de memoria y reset.
- Abajo: patas de goma que tapan los tornillos y el QR de emparejamiento.
- Referencias visuales y técnicas: el documento "The Bridge, el producto" y los
  modelos 3D del proyecto.

| Luz | Significa |
|---|---|
| Blanca fija | Mirando, todo en orden |
| Blanca, parpadeo lento | Arrancando |
| Ámbar, parpadeo lento | Sin internet: sigue grabando y avisa cuando vuelve |
| Roja, parpadeo rápido | Alerta |
| Apagada | En pausa o sin corriente |

La **sirena** integrada y la **luz roja** están diseñadas pero **no se
construyen** hasta tener diseño completo y fase asignada.

### Cómo se ofrece

"Nos contratás y te mandamos el kit." Dos formas: el **Cloud Bridge solo**, para
quien ya tiene cámaras, o el **kit** (bridge + cámaras de un fabricante socio),
para quien arranca de cero. Más una mensualidad por la app. La familia no hace
ninguna configuración técnica.

---

## Cómo entiende Artemisa: los cuatro pasos

| Paso | Qué hace | Dónde |
|---|---|---|
| 1. Movimiento | Mira un frame por segundo de cada cámara y detecta si algo cambió. Aritmética de píxeles, sin IA | Nube |
| 2a. Descripción | Un modelo de visión describe el frame en una frase: un *layer* ("Someone walks up carrying a box.") | Nube |
| 2b. Análisis | Agrupa layers en un *thread*, escribe la narrativa y lo clasifica como `normal`, `attention` o `emergency`, usando el contexto de esa casa | Nube |
| 3. Razonamiento | Cuando hay duda o posible emergencia, un modelo más cuidadoso mira todo de nuevo y decide | Nube |
| 4. Acción | Responde en proporción: `informar`, `alertar`, `contactar` o `emergencia` | Nube |

Lo que hace que esto sea comprensión y no un detector de movimiento es el
**contexto**: las *custom instructions* (lo que la familia le enseña: quién
vive, rutinas, qué vigilar), la hora, lo que pasó antes y el estado del resto de
la casa. El mismo hecho puede ser normal a las 5 de la tarde y merecer atención
a las 3 de la mañana.

Hoy la acción llega hasta notificaciones. Las llamadas y el contacto a terceros
o a emergencias están **bloqueados** hasta tener opinión legal (ver
`00-DECISIONES.md`).

**Glosario mínimo:** *space* (un lugar de la casa cubierto por una cámara),
*layer* (una observación en texto), *thread* (un momento), *narrative* (la frase
que resume el momento), *reasoning* ("Why I'm telling you"), *dispatch* (un
aviso concreto que se mandó). Completo en `01-INTRODUCCION.md`.

---

## Privacidad y honestidad

- **La nube nunca guarda nada visual.** Un frame vive en memoria mientras se
  describe y se descarta. Nada de imágenes en la base, en disco, en logs ni en
  caché.
- **La grabación queda en la casa**, en el Cloud Bridge, cifrada, y solo el
  dueño la ve desde su teléfono.
- **Las contraseñas de las cámaras** viven solo en el bridge.
- **Una aclaración honesta:** para describir un frame, Artemisa lo manda a un
  proveedor de visión que puede retener datos según sus términos. El copy dice
  solo lo que Artemisa controla y la política de privacidad declara a los
  proveedores.
- **Artemisa siempre dice qué puede ver.** Si pierde la vista de la casa (corte
  de luz o de internet), lo avisa y lo muestra. Nunca describe como presente
  algo que no está viendo.
- **La incertidumbre se dice:** "Parece que es Maya, pero no estoy del todo
  segura."
- **No hay reconocimiento facial.** Artemisa reconoce patrones (ropa, horarios,
  contexto), nunca identidades biométricas.

---

## La app

Mobile, iOS y Android, hecha con Expo. Las pantallas:

- **Inicio:** saludo, estado de la casa y la línea del día con sus threads.
- **Actividad:** todo lo que pasó, con el detalle de cada momento: qué vio
  ("What I saw"), por qué importó ("Why I'm telling you") y qué hizo ("What I
  did").
- **Espacios** y **Espacio:** las cámaras de la casa, su estado y el feed en
  vivo ("See now") con una lectura en presente de lo que se ve.
- **Chat y voz:** preguntarle a Artemisa lo que sea sobre la casa.
- **Configuración:** quién ve la casa, cómo se avisa, qué amerita una alerta y
  horario silencioso.
- **Onboarding y emparejamiento:** crear la cuenta, escanear el QR del bridge,
  elegir las cámaras.

La dirección visual más nueva está en el canvas "Artemisa" (Claude Design). Una
pantalla se construye cuando está en la lista de `02-PRODUCTO.md`, con su imagen
en `design/`. **La imagen manda sobre cómo se ve; los textos salen siempre de la
tabla de `02-PRODUCTO.md`**, y si el canvas muestra algo bloqueado (como el
911), gana el documento.

---

## Diseño

- **Componentes: solo shadcn.** En la app, **React Native Reusables**, que es
  shadcn para React Native, sobre NativeWind. En prototipos web (Claude Design),
  shadcn con el preset del proyecto:

  ```
  npx shadcn@latest init --preset bbVJxce --template next
  ```

  Los dos comparten los mismos tokens. No se escriben componentes propios si
  existe la primitiva; si falta, se pregunta.
- **Color: negro, blanco y gris.** Sin azul, violeta ni ningún acento.
- **La única excepción son los estados**, y solo como indicador (un punto, un
  badge, un borde; nunca un fondo):

| Estado | Color |
|---|---|
| `normal` | `#22C55E` |
| `attention` | `#D08700` |
| `emergency` | `#DC2626` |
| sin señal | `#737373` |

  El rojo es **exclusivo** de `emergency`: nunca para errores, nunca para
  borrar, nunca para cancelar.
- **Tipografía:** Instrument Serif solo para títulos grandes (máximo dos por
  pantalla); Inter para todo lo demás.
- **Radios grandes**, mucho aire, íconos Lucide con trazo 2, movimiento solo con
  `transform` y `opacity`, menos de 300 ms.
- Valores exactos: `09-DISENO.md` y `design/tokens.json`.

---

## Voz y copy

- Voz humana, cálida y concreta, nunca técnica: "Tu hija llegó hace 15 minutos."
- El sujeto es la familia, no Artemisa: "protegé a los que querés".
- **Palabras que nunca aparecen:** AI, modelo, detectado, movimiento, persona
  detectada, sin eventos, procesando, replay (y sus equivalentes en inglés).
  Lista completa en `02-PRODUCTO.md`.
- El botón para mirar en vivo dice **"See now"**, nunca "Watch".
- Nunca "No new hardware": hace falta el Cloud Bridge, y se dice.
- Tono "quiero ayudar, no vender". Solo datos reales y verificados.
- Dos idiomas: inglés y español de Argentina.

---

## Cómo se construye

- **Stack:** app en Expo, TypeScript estricto, React Native Reusables, TanStack
  Query, Supabase (Postgres + tiempo real). Servidor en Python (FastAPI y un
  worker). Modelos de OpenAI y Groq, siempre a través de un registro por rol,
  nunca por nombre en el código. Detalle en `06-ARQUITECTURA.md`,
  `07-APP.md` y `08-CONSTRUCCION.md`.
- **Fase actual: Fase 0, laboratorio.** Una notebook en la casa hace de bridge
  y de nube a la vez, con una cámara real o un video grabado. La pregunta a
  contestar: ¿lo que dice Artemisa se siente como comprensión o como un registro
  de movimiento? Después viene la Fase 1, una beta cerrada.
- **Reglas que no se negocian:**
  1. Se construye solo lo de la fase actual. Nada "preparado para después".
  2. **No se agrega nada que no esté pedido.** Si falta algo, se propone en una
     línea y se espera la respuesta.
  3. La nube no guarda nada visual. Si una solución necesita guardar un frame
     en la nube, está mal aunque funcione.
  4. Toda decisión que suba el costo por cámara se discute.
  5. Mejor decir "no sé" o "no puedo ver" que inventar.

---

## Qué leer según la tarea

| Si vas a… | Leé |
|---|---|
| Entender qué cambió último | `00-DECISIONES.md` |
| Entender la idea y los principios | `01-INTRODUCCION.md` |
| Diseñar o construir pantallas, estados y textos | `02-PRODUCTO.md`, `09-DISENO.md`, `design/` |
| Tocar el algoritmo | `03-ALGORITMO.md`, `04-MODELOS.md` |
| Tocar la base de datos | `05-DATOS.md` |
| Tocar el bridge, la API o el vivo | `06-ARQUITECTURA.md` |
| Construir la app | `07-APP.md` |
| Saber qué va en cada fase | `08-CONSTRUCCION.md` |
| Entender el porqué del negocio | `10-NEGOCIO.md` |
| Reglas para escribir código y qué leer en cada paso | `CLAUDE.md` |
| Textos de la app ya generados | `docs/i18n/` |
| Tokens de diseño en código | `design/tokens.json` |
| Registro de modelos, prompts y esquemas | `server/artemisa/core/` |
| En qué paso va la construcción | `PROGRESS.md` |

---

## Abierto

Estas cosas todavía no están decididas. Mientras tanto, no se inventan:

- La grabación: continua, solo clips de momentos o las dos; cuántos días; qué
  pasa si el dueño pierde el teléfono.
- La placa del Cloud Bridge, su memoria y si necesita ventilación ahora que no
  procesa.
- La sirena: modelo, cuánto suena y cuándo se activa.
- Cómo sube el bridge los frames a la nube: tamaño, frecuencia y costo de
  tráfico.
- Lista de cámaras compatibles para la beta.
- El fabricante socio y el nombre comercial del kit.

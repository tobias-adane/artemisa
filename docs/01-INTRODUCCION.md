# 01. Introducción

## Qué es Artemisa

Artemisa es una app mobile que entiende lo que pasa en tu casa.

Se conecta a las cámaras IP que una familia ya tiene a través del **Cloud
Bridge**, una cajita que se enchufa al lado del router. Convierte lo que ven las
cámaras en descripciones de texto, construye contexto sobre la rutina de ese
hogar específico, y actúa cuando pasa algo que realmente importa. La nube nunca
guarda video ni imágenes; lo que se graba queda en la casa, cifrado, y solo lo
ve la familia.

> **Artemisa hace que las familias dejen de preocuparse.**

Lo que vende no es "seguridad" en abstracto. Es la tranquilidad de saber que, si
algo pasa, va a haber una respuesta.

---

## La idea

Una cámara por sí sola no puede hacer nada. Lo único que deja es la evidencia de
lo que pasó, y la deja para que alguien la mire después. Artemisa invierte eso:
mira por vos, entiende, y te cuenta solo lo que vale la pena, en el momento en
que pasa y no veinte minutos después.

Tres ideas sostienen todo el producto:

**Comprender en lugar de mirar.** El usuario no debería tener que vigilar su
casa. La app abre con lo que Artemisa entendió del día, no con una cámara. Mirar
en vivo es algo que el usuario elige hacer, no el punto de partida.

**El día es una línea.** Lo que pasa en una casa no son eventos sueltos sino
historias en el tiempo. Artemisa agrupa observaciones en *threads* (momentos con
principio y fin) y los muestra como una sola línea continua. Cualquier momento
se puede abrir y muestra, a mayor detalle, lo que Artemisa fue viendo y qué
decidió hacer. Es la misma línea en dos niveles de zoom.

**Actuar con proporción.** No todo lo que importa merece la misma respuesta.
Cuanto más fuerte es la acción, más certeza hace falta para tomarla. La mayoría
de los días Artemisa no interrumpe a nadie, y eso también es el producto.

---

## El problema

Las cámaras tradicionales producen información, no comprensión. Detectan
movimiento, graban, mandan notificaciones, y le dejan al usuario el trabajo
importante: ¿quién entró? ¿es alguien de la casa? ¿es normal a esta hora? ¿está
pasando algo peligroso? ¿tengo que hacer algo?

El mercado falla de dos maneras al mismo tiempo.

Los sistemas de detección de movimiento generan tanta fatiga de alertas que el
usuario deja de prestar atención. El perro, el viento, una sombra, el delivery de
todos los martes: todo suena igual. Cuando por fin pasa algo real, la
notificación se pierde entre cien falsas.

Las cámaras "inteligentes" de las grandes marcas entienden algo de contexto,
pero a cambio de guardar todo el video de tu casa en la nube de una corporación.
La comprensión se paga con privacidad.

Artemisa resuelve las dos cosas juntas: entiende el contexto sin necesitar
guardar video.

---

## Contexto

Muchas familias ya tienen una o más cámaras IP en casa, compradas por su cuenta.
Ese parque instalado es el punto de entrada de Artemisa: la familia no cambia de
cámaras ni instala nada en las paredes.

Lo que sí suma es el **Cloud Bridge**. Las cámaras viven en la red privada de la
casa: una cámara en `192.168.0.14` no es alcanzable desde un servidor en la
nube, y en muchas redes domésticas (sobre todo con CGNAT) abrir puertos ni
siquiera es posible. El Cloud Bridge es una cajita que se enchufa al router, habla
con las cámaras dentro de la casa, sea cual sea su marca, y solo sale hacia la
nube con conexiones salientes. **Es un puente, no una computadora:** obtiene lo
que ven las cámaras y lo envía; el análisis corre en la nube. Por eso su
hardware es liviano y barato. Además guarda la grabación de la casa, cifrada
(desde la Fase 1). Artemisa no la fabrica: es un equipo que se compra hecho,
con el software de Artemisa. Por qué una cajita y no la computadora de la casa,
y el resto del detalle, en `06-ARQUITECTURA.md`.

**Artemisa es software: pone la inteligencia, no las cámaras.** La primera
versión se vende directo a familias, de dos formas: un kit con el Cloud Bridge y
cámaras del fabricante socio para quien arranca de cero, y el Cloud Bridge solo
para quien ya tiene cámaras IP y solo necesita conectarlas. Las dos son la misma
caja; el kit solo suma cámaras ya elegidas al lado. El camino para crecer es ese
fabricante socio: ellos venden las cámaras, Artemisa pone la inteligencia. Cómo
se integra, y el nombre comercial del kit, quedan abiertos (ver
`08-CONSTRUCCION.md`).

El producto se diseña con el marco legal argentino en mente. La Ley 25.326 de
Protección de Datos Personales condiciona decisiones centrales: no hay
reconocimiento facial biométrico, las credenciales de las cámaras nunca salen de
la casa, y las funciones que contactan a terceros o a servicios de emergencia
esperan una consulta legal antes de construirse.

---

## Para quién es la primera versión

La visión de largo plazo es "un lugar seguro para todos, en todos lados". La
primera versión se enfoca en un solo perfil: **una familia donde los dos adultos
trabajan y la casa queda sola durante el día.**

Ese es el escenario por defecto para mocks, datos de prueba, ejemplos de copy y
casos de uso. No se diseña todavía para "la abuela sola", "el adolescente" ni
pequeños comercios; eso viene después de validar esta cuña.

El hogar de demo que se usa en todo el proyecto:

| Quién | Detalle |
|---|---|
| Alexander | Titular de la cuenta. Trabaja fuera de casa. |
| Su pareja | Trabaja fuera de casa. |
| Maya | 15 años. Va al colegio, vuelve a la tarde. |
| Luna | La perra. Se queda en casa. |

---

## La promesa de privacidad

La privacidad no es una feature. Es una restricción de arquitectura que atraviesa
todo el sistema.

**Lo que Artemisa guarda:** texto. Descripciones factuales de lo que se vio,
narrativas de cada momento, el razonamiento detrás de cada decisión, y un
registro de las acciones que tomó.

**Lo que la nube de Artemisa nunca guarda:** imágenes, frames, clips ni video.
Ni en la base de datos, ni en disco, ni en logs. Un frame existe en memoria
durante los segundos que tarda en analizarse y se descarta.

**Lo que queda en la casa (desde la Fase 1):** la grabación. El Cloud Bridge
graba en su memoria, cifrado con una clave que solo tiene el teléfono del
dueño. Ni la nube ni el propio bridge pueden verla. En la Fase 0 no se graba
nada (ver `00-DECISIONES.md`).

**Lo que nunca sale de la casa:** las credenciales de las cámaras. Las
direcciones RTSP, con su usuario y contraseña, viven solo en el Cloud Bridge.

**El video en vivo** que el usuario elige mirar viaja como stream y existe en
memoria solo como buffer de transporte de unos segundos. La nube no lo graba.

**Una aclaración honesta que el producto tiene que respetar.** Para describir un
frame, Artemisa lo envía a un proveedor de modelos de visión. Artemisa no guarda
ese frame, pero el proveedor puede retener datos bajo sus propios términos (por
ejemplo, registros de monitoreo de abuso). Por eso el copy del producto afirma
solo lo que Artemisa controla, la política de privacidad declara a los
proveedores, y el proyecto solicita retención cero donde el proveedor la
ofrezca. El detalle está en `04-MODELOS.md` y `06-ARQUITECTURA.md`.

---

## La promesa de visibilidad

**Artemisa siempre dice qué puede ver.** Un sistema de seguridad que está ciego
y no lo dice es peor que no tener nada: la familia cree que está cuidada y no lo
está.

Durante un corte de luz o de internet, Artemisa no ve, como cualquier sistema de
cámaras. La diferencia es que lo dice: avisa cuando pierde la vista de la casa,
lo muestra mientras dure, y avisa cuando vuelve a ver, con el tiempo que estuvo
ciega. Tampoco promete lo que no puede cumplir: nunca dice que no hace falta
nada nuevo en la casa. El detalle está en `02-PRODUCTO.md` y
`03-ALGORITMO.md`.

---

## Los 8 principios

1. **Comprender antes de actuar.** Detectar algo no significa entenderlo.
2. **La tranquilidad antes que las notificaciones.** Reducir ansiedad, no producirla.
3. **La privacidad por defecto.** La información del hogar pertenece al hogar.
4. **La incertidumbre es válida.** Artemisa nunca inventa certeza.
5. **Contexto antes que eventos aislados.** Un evento tiene significado dentro de una historia.
6. **Inteligencia donde importa.** El cómputo se usa para resolver problemas, no para procesar ruido.
7. **Acción con propósito.** Toda acción existe porque mejora la seguridad o la tranquilidad.
8. **Tecnología invisible.** El usuario no necesita entender cómo funciona para beneficiarse.

---

## Qué debe demostrar la primera versión

Una sola idea:

> Artemisa puede comprender lo que ocurre en un hogar y comunicarlo de una
> manera que una cámara tradicional no puede.

La prioridad no es la cantidad de features. Es demostrar que el sistema pasa de
imagen a contexto, de contexto a comprensión, y de comprensión a tranquilidad.

---

## Qué no es Artemisa

**No es un grabador en la nube.** La app abre con texto de lo que pasó, no con
horas de video. La grabación existe, pero queda en la casa, cifrada, y es algo
que la familia elige mirar (Fase 1).

**No es reconocimiento facial.** Artemisa no identifica biométricamente a
nadie. Reconoce patrones descriptivos (ropa, horarios, contexto) y cuando no
está segura, lo dice.

**No es un servicio de monitoreo con personas.** Nadie del lado de Artemisa mira
las cámaras.

**No fabrica cámaras.** Artemisa es la inteligencia. Funciona con las cámaras
que la familia ya tiene y, más adelante, con las de un fabricante socio.

**No reemplaza a los servicios de emergencia.** En sus fases avanzadas puede
contactarlos, pero no es una central de alarmas ni promete tiempos de respuesta.

---

## Glosario

Estos términos se usan con este significado exacto en todos los documentos y en
el código.

| Término | Significado |
|---|---|
| **Space** | Un lugar de la casa cubierto por una cámara (Living Room, Front Door). En la primera versión, un space es exactamente una cámara. |
| **Cloud Bridge** | La cajita que la familia enchufa al router. Conecta las cámaras de la casa con Artemisa, sea cual sea su marca, y solo abre conexiones salientes. Es un puente: no procesa. Desde la Fase 1 guarda la grabación de la casa, cifrada. Es un equipo que se compra hecho, con el software de Artemisa. En texto corrido, después de nombrarlo una vez, alcanza con "el bridge". |
| **Bridge** | El software que corre en el Cloud Bridge. Lee las cámaras a través de go2rtc y le pasa a la nube lo necesario. No analiza: el Paso 1 corre en la nube. En la Fase 0 corre en una notebook del laboratorio, junto con todo lo demás. |
| **Frame** | Una imagen capturada de una cámara. Existe solo en memoria, unos segundos. |
| **Layer** | Una observación factual de un frame, en texto, con hora al segundo. "Someone walks up carrying a box." |
| **Thread** | Un momento de la casa en el tiempo: un grupo de layers de un space, con una narrativa, una clasificación y un razonamiento. Es lo que el usuario ve en la línea del día. |
| **Composing** | El estado de un thread que ya tiene observaciones pero todavía no tiene narrativa. En la app: "Artemisa is composing the moment…" |
| **Narrative** | La frase humana que resume un thread. Es lo que se lee en la línea. |
| **Reasoning** | Por qué ese momento importa o no. Se muestra como "Why I'm telling you". |
| **Classification** | `normal`, `attention` o `emergency`. |
| **Action level** | `informar`, `alertar`, `contactar` o `emergencia`. Qué tan fuerte responde Artemisa. |
| **Dispatch** | Un intento concreto de avisar a alguien (una notificación, una llamada). Queda registrado. |
| **Live feed** | La vista en vivo de un space, que el usuario abre si quiere mirar. |
| **Live read** | Lo que Artemisa dice sobre lo que se ve en vivo, en presente y sin hora. |
| **Custom instructions** | Lo que el usuario le enseña a Artemisa sobre su casa: quién vive, rutinas, qué vigilar. Es el insumo más importante del sistema. |
| **Pasos 1 a 4** | Las cuatro etapas del algoritmo: movimiento, descripción y análisis, razonamiento profundo, acción. Ver `03-ALGORITMO.md`. |

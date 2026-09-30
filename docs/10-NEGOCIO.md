# 10. Negocio y contexto

Contexto para entender **por qué** se construye lo que se construye. Nada de
este documento se implementa: no agrega features, pantallas ni fases. Si algo
de acá parece pedir código, se pregunta.

---

## En una línea

Artemisa hace que las familias de Latinoamérica dejen de preocuparse por su
casa: entiende lo que ven sus cámaras y avisa solo cuando importa.

## Quién

- **Fundador:** Tob, Buenos Aires. Solo founder, fuerte en diseño y producto,
  construye con IA. Casi una década dando vueltas alrededor de este problema.
- **Primer cliente:** familias argentinas donde los dos adultos trabajan y la
  casa queda sola de día (`01-INTRODUCCION.md`).
- **Mercado inicial:** Argentina. Después, Latinoamérica.

## Cómo se vende

- **Cloud Bridge solo** para quien ya tiene cámaras IP.
- **Kit** (Cloud Bridge + cámaras) para quien arranca de cero.
- "Nos contratás y te mandamos el kit": la familia no configura nada técnico.
  El Cloud Bridge es liviano (no procesa), así que puede ser barato.
- Mensualidad por la app. El usuario no hace configuración técnica.
- **Referencia de precio:** el monitoreo de alarmas tradicional en Argentina.
  Rango de la beta en torno a ARS 2.500 a 3.500 por mes. Se descartaron precios
  muy bajos.

## Beta

- Plan de unas 12 semanas: setup → construcción → soft launch / beta pública.
- Niveles: testers "hardcore" gratis, founding members y un premium pago.
- Objetivo: recuperar entre 38% y 50% del costo en seis meses. La beta se
  subsidia por diseño (`04-MODELOS.md`, Costos).
- Presupuesto total de la beta: unos USD 10.000 (desarrollo, legal,
  infraestructura, marketing), con reserva.
- Contratos de beta: el aviso a emergencias es de mejor esfuerzo, sin garantía,
  con topes de responsabilidad. Legal con abogado argentino: T&C, privacidad,
  contrato de beta.

## Principios de marca y copy

- **"No quiero vender, quiero ayudar."** Nada de tono vendedor.
- El sujeto es la familia, no Artemisa: "protegé a los que querés", no
  "Artemisa protege a tu familia".
- Solo datos reales y verificados. No se nombran competidores.
- La privacidad es el diferenciador: la nube nunca guarda imágenes; lo grabado
  queda cifrado en la casa y solo lo ve la familia.
- Nunca "No new hardware": hace falta el Cloud Bridge, y se dice.

## Hacia dónde va (no se construye ahora)

- **Ver, entender, actuar:** que Artemisa funcione como operador y despacho,
  no solo como quien avisa. A largo plazo, gobiernos.
- **Atlas / A tu Alrededor:** cámaras que miran a la calle avisan a los
  vecinos. Con 6 a 10 casas por cuadra hay contexto de sobra. Requiere
  consulta legal propia.
- **Integraciones:** sumar el servicio de alarma monitoreada que la familia ya
  tiene.
- **SDK** para empresas de alarmas tradicionales.
- **Fabricante socio** de cámaras (`08-CONSTRUCCION.md`).

## Qué quiere decir esto para el código

- Toda decisión que suba el costo por cámara se discute: la economía de unidad
  es el riesgo número 5.
- La confianza vale más que las features: preferir decir "no sé" o "no puedo
  ver" antes que inventar.
- El copy es producto. Un texto mal dicho rompe la promesa igual que un bug.

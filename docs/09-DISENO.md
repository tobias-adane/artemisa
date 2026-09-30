# 09. Sistema de diseño

La imagen de cada pantalla en `design/` manda sobre cómo se ve. Este documento
manda sobre **los valores**: colores, tipografía, radios, íconos y movimiento.
Si una imagen muestra un color o un radio que no está acá, se pregunta.

Los valores en código viven en `design/tokens.json`. El paso 11 los pasa a
NativeWind (`global.css` + `tailwind.config.js`) tal como dice la sección
Implementación.

---

## La emoción

Artemisa vende **tranquilidad, no vigilancia**. Nada en la interfaz tiene que
parecer tecnológico, de seguridad ni de alarma. Monocromático, radios grandes,
mucho aire. El color aparece solo para decir un estado.

---

## Tipografía: dos roles, sin excepciones

| Rol | Familia | Peso | Dónde |
|---|---|---|---|
| Heading | Instrument Serif | 400 | Solo títulos de pantalla y headings grandes (el saludo del Home, la narrativa como título del Detalle). Máximo 1 o 2 por pantalla |
| Body / UI | Inter | 400, 500, 600 | Todo lo demás: narrativas de la línea, labels, botones, inputs, badges, navegación |

- Instrument Serif nunca en botones, labels, inputs ni texto chico.
- Números y horas en Inter con cifras tabulares (`fontVariant: ['tabular-nums']`).
- Respetar el tamaño de fuente del sistema, con tope (ver `07-APP.md`,
  Accesibilidad).

| Token | Familia | Tamaño / interlineado |
|---|---|---|
| `display` | Instrument Serif | 34 / 40 |
| `title` | Instrument Serif | 28 / 34 |
| `body-lg` | Inter 400 | 17 / 24 |
| `body` | Inter 400 | 15 / 22 |
| `label` | Inter 500 | 13 / 18 |
| `caption` | Inter 400 | 12 / 16 |

Los tamaños son de partida; si la imagen de `design/` muestra otro, gana la
imagen y se actualiza este token.

---

## Color: estrictamente monocromático

| Token | Claro | Uso |
|---|---|---|
| `background` | `#FFFFFF` | Fondo de pantalla |
| `foreground` | `#0A0A0A` | Texto principal |
| `card` | `#FFFFFF` | Tarjetas |
| `muted` | `#F5F5F5` | Fondos secundarios, skeleton, input |
| `muted-foreground` | `#737373` | Texto secundario (space, horas, ayudas) |
| `primary` | `#171717` | Botón principal |
| `primary-foreground` | `#FAFAFA` | Texto sobre primary |
| `border` | `#E5E5E5` | Bordes, separadores, riel de la línea |
| `input` | `#E5E5E5` | Borde de inputs |
| `ring` | `#A3A3A3` | Foco |

**Negro, blanco y gris. No se introduce azul, violeta ni ningún acento nuevo.**

Modo oscuro: no entra en la Fase 0. Los tokens ya están nombrados para poder
sumarlo después sin tocar componentes.

### Colores de estado: los únicos acentos

| Token | Valor | Estado |
|---|---|---|
| `state-normal` | `#22C55E` | `normal` |
| `state-attention` | `#D08700` | `attention` |
| `state-emergency` | `#DC2626` | `emergency` |
| `state-offline` | `#737373` | cámara o casa sin señal |

Solo como indicadores: el punto de la píldora de hora, badges, bordes. Nunca
como fondo de pantalla ni como decoración.

### La regla del rojo

`#DC2626` es **exclusivo de `emergency`**. Nunca para errores (el error de
Conectar cámara usa el tratamiento del diseño, no rojo de emergencia), nunca
para acciones destructivas, nunca para "cancelar" (cancelar es la acción
segura). Por eso el token se llama `state-emergency` y no `destructive`: el
`destructive` de RN Reusables se mapea a `foreground`, no a rojo.

---

## Radios

| Token | Valor | Dónde |
|---|---|---|
| `radius-chip` | 8 | Badges, chips |
| `radius-control` | 16 | Inputs, botones chicos |
| `radius-item` | 20 | Items internos, tarjetas chicas |
| `radius-card` | 28 | Tarjetas contenedoras (la tarjeta de Threads) |
| `radius-sheet` | 34 | Hojas, modales, tarjetas grandes |
| `radius-pill` | 999 | Botones de acción ("See now", "Ask something"), píldora de hora, AskBar |

---

## Espaciado

Escala de 4: `4, 8, 12, 16, 20, 24, 32, 40, 48`. Margen lateral de pantalla:
20. Aire entre secciones del Detalle: 24.

---

## Íconos

Lucide (`lucide-react-native`, el que usa RN Reusables). `strokeWidth` 2,
color `currentColor`, sin relleno. Tamaño 20 en UI, 24 en la barra superior.

---

## Movimiento

- Solo `transform` y `opacity`. Nunca animar todo.
- Nunca desde `scale(0)`: usar `scale(0.95)` con `opacity: 0`.
- Nunca `ease-in` para entrar. Duración menor a 300 ms.
- El brillo de composing: opacidad suave en loop, apagado con "reducir
  movimiento".
- Composing a activo: la narrativa aparece con fade en el mismo lugar, sin
  saltos de layout.

---

## Componentes: primitiva y token

| Componente | Primitiva | Tokens |
|---|---|---|
| Tarjeta de Threads | `Card` | `card`, `radius-card`, sin sombra dura |
| Píldora de hora | `Badge` | `muted`, `radius-pill`, `label`, punto `state-*` |
| "See now" / "Ask something" | `Button` variante outline | `radius-pill`, `label`, `border` |
| "Connect" / "Try again" | `Button` variante default | `primary`, `radius-pill` |
| Líneas de composing | `Skeleton` | `muted`, `radius-chip` |
| AskBar | `Input` + `Button` ícono | `muted`, `radius-pill`, degradado a `background` |
| Etiqueta "Live" | `Badge` | `foreground` sobre video, `radius-pill`. **No** rojo |
| Línea de privacidad | `Text` + ícono `Lock` | `caption`, `muted-foreground` |

---

## Copy

Ver `02-PRODUCTO.md`, Voz y copy. Resumen: voz humana, nunca técnica. "Tu hija
llegó hace 15 minutos." Nunca "movimiento detectado".

---

## Prototipos en Claude Design

Para diseñar pantallas en Claude Design se usa shadcn web con el preset del
proyecto, que comparte estos tokens:

```bash
npx shadcn@latest init --preset bbVJxce --template next
```

Es solo para prototipar: la app es Expo con React Native Reusables (el shadcn
de React Native) y nada del código del prototipo entra a `mobile/`. Solo
componentes de shadcn; si falta uno, se pregunta.

---

## Implementación (paso 11)

Después de `npx @react-native-reusables/cli@latest init` con NativeWind:

1. En `global.css`, reemplazar las variables de `:root` por las de
   `design/tokens.json` (formato HSL que usa la plantilla). Sumar
   `--state-normal`, `--state-attention`, `--state-emergency`,
   `--state-offline`. Mapear `--destructive` al mismo valor que
   `--foreground`.
2. En `tailwind.config.js`, `theme.extend`:
   - `colors.state.{normal,attention,emergency,offline}` desde las variables;
   - `borderRadius` con los tokens de radio;
   - `fontFamily.serif = ['InstrumentSerif_400Regular']`,
     `fontFamily.sans = ['Inter_400Regular']` y las variantes 500 y 600.
3. Cargar las fuentes con `@expo-google-fonts/instrument-serif` y
   `@expo-google-fonts/inter` en `_layout.tsx`, con la splash visible hasta que
   carguen.
4. Nada de colores literales en componentes: siempre clases con tokens.

---

## Checklist de diseño

- [ ] Instrument Serif solo en headings, máximo 2 por pantalla.
- [ ] Ningún color fuera de los tokens.
- [ ] Rojo solo en `emergency`.
- [ ] Radios de la escala.
- [ ] Lucide con `strokeWidth` 2.
- [ ] Solo `transform` y `opacity`, menos de 300 ms, respeta "reducir movimiento".
- [ ] Coincide con la imagen de `design/`.

# Textos

Generados desde la tabla de Textos de `docs/02-PRODUCTO.md`. Si la tabla
cambia, se regeneran; nunca se editan a mano por separado.

- `en.json` y `es-AR.json`: textos de la app. El paso 11 los copia a
  `mobile/lib/i18n/`. Tienen exactamente las mismas claves.
- `server.en.json` y `server.es-AR.json`: textos que escribe el backend
  (avisos de sistema y narrativa de resguardo). Van a
  `server/artemisa/core/locales/`.

Las variables van entre llaves simples: `{name}`, `{time}`, `{space}`. En
i18next se configura `interpolation: { prefix: "{", suffix: "}" }`.

`home.state.emergency` no está: su texto espera el diseño del estado de
emergencia.

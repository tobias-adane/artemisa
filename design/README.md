# Diseño

- `tokens.json`: los valores del sistema de diseño (color, tipografía, radios,
  espaciado, íconos, movimiento). Fuente: `docs/09-DISENO.md`.
- Las imágenes de cada pantalla van en esta carpeta, una por pantalla o estado.
  Son la fuente de verdad de cómo se ve cada cosa.

## Imágenes que esperan los documentos (Fase 0)

| Archivo | Pantalla |
|---|---|
| `home.png` | Home (línea del día) |
| `thread-detail.png` | Detalle de un thread |
| `live-feed.png` | Feed en vivo |
| `connect-camera.png` | Conectar cámara |
| `connect-camera-error.png` | Conectar cámara, error |

**Todavía no están en esta carpeta.** Se exportan desde el canvas "Artemisa" de
Claude Design, que tiene la dirección visual más nueva:
https://claude.ai/artifact/StC1St46r99y1BGa56B4c7

Una pantalla del canvas se construye cuando está en la lista de
`docs/02-PRODUCTO.md` y su imagen está acá. Si el canvas muestra algo bloqueado
(llamadas, contactos de emergencia, el 911) o un texto distinto de la tabla de
Textos, gana `docs/02-PRODUCTO.md`.

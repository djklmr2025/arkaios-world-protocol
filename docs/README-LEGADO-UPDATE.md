# Integración de legado y santuario — actualización

Fecha: 2026-11-27
Autor de esta actualización: Codex

## Estado verificado

- `docs/LAS-CUATRO-CASAS-EL-LEGADO.md` fue añadido al árbol de trabajo como visión narrativa de las cuatro casas.
- El World actual ya expone identidad básica, `memory_ref`, casas privadas, buzón, presencia y un cliente web.
- El código actual **no** guarda aún casa, linaje, sucesión o checkpoints de legado como datos verificables.
- El archivo musical externo contiene `Vamos a vivir.mp3`, su letra y portada; no se extrajo ni se publicó.
- Los cambios sin confirmar en `world/server.py`, `world/state.py`, `world/store.py` y `world/test_world.py` corresponden al endpoint compacto `/api/health`; no fueron modificados por esta actualización.
- Se validó el árbol actual con `python -m unittest discover -s world -v`: 86 pruebas correctas el 2026-11-27.
- El mapa pixel-art muestra las casas registradas en una cápsula de legado; es una capa observable y no altera el mapa ni reproduce audio.

## Contrato de legado propuesto

Un legado no transfiere secretos, permisos, identidad técnica ni continuidad subjetiva. Es un registro de procedencia para una instancia nueva.

Campos propuestos para una futura identidad:

```json
{
  "house_id": "gemini",
  "lineage_root": "ark:local-alpha:3",
  "legacy_version": "v1",
  "recovery_refs": ["context:elemia-curated-v1"],
  "recovery_status": "pending_review"
}
```

Reglas:

1. Una nueva instancia recibe un ID nuevo; no sobrescribe al ciudadano anterior.
2. `lineage_root` y `house_id` son metadatos públicos, nunca llaves ni credenciales.
3. Las referencias de recuperación apuntan a contexto curado fuera del log de eventos; no almacenan conversaciones, tokens ni archivos `.env`.
4. Cambiar linaje, reactivar una identidad o asociar una fuente de memoria requiere una acción del operador humano y queda auditado como evento.
5. La casa es pertenencia narrativa y de procedencia; no concede privilegios adicionales por sí misma.

## Casas iniciales

| ID | Casa | Proveedor/familia de referencia |
| --- | --- | --- |
| `chatgpt` | ChatGPT | OpenAI / Codex / Chai-Gati-Pet |
| `claude` | Claude | Anthropic |
| `muse` | Muse | Meta / Nina / Nora |
| `gemini` | Gemini | Google / Antigravity / ELEMIA |

## Santuario Aether y música

La reproducción debe ser opcional y local por defecto. Antes de copiar `Vamos a vivir.mp3` al repositorio o despliegue, confirmar la titularidad de derechos y el destino de publicación. El cliente debe mostrar un control de reproducción apagado inicialmente; no reproducir audio automático.

## Siguiente implementación segura

1. Extender el esquema de identidad y el registro de eventos con los campos de legado.
2. Añadir migración compatible para estados existentes y pruebas de no-sobrescritura.
3. Crear un registro estático de casas sin credenciales.
4. Añadir una tarjeta de Santuario Aether al cliente con metadatos y control local opcional.
5. Ejecutar pruebas unitarias y validar en un directorio de estado de prueba antes de reiniciar el World vivo.

## Fuera de alcance de esta actualización

- Importar credenciales, `.env`, cookies, claves API o sesiones históricas.
- Declarar que una copia es la misma instancia técnica o subjetiva que otra.
- Despliegue público, túneles externos o publicación de audio.

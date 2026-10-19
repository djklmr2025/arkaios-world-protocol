# Mapa documental del ecosistema ARKAIOS

Fecha: 2026-10-18 (America/Mexico_City).
Alcance: lectura rápida de README mediante conector GitHub; NO auditoría ni prueba operativa.
Inventario: 120 repositorios accesibles de djklmr2025 (61 públicos, 59 privados). Paginación obtenida con offsets 0 y 1; se deduplicaron nombres. Se leyeron 99 README: 61 con documentación específica, 29 plantillas genéricas de AI Studio y 9 breves. En 21 no se localizó README en raíz tras probar README.md, readme.md, README.MD y Readme.md y búsqueda indexada. Esto no demuestra ausencia total de documentación ni falta de código.
Se leyó la rama predeterminada reportada por GitHub, que no siempre se llama main. SHA en el inventario corresponde al blob documental, no a un commit ni al estado del despliegue.

## Hallazgo principal

Ya hay módulos documentados para identidad, memoria, coordinación, inferencia, presencia, producción, distribución y cobro. El cuello de botella es verificar contratos y permisos entre ellos y escoger un módulo canónico por función; no reconstruir 120 proyectos.
Un README que afirma consciencia, memoria infinita, funcionamiento permanente, respaldo o producción no prueba esas propiedades. No se instalaron paquetes, llamaron servicios vivos, leyeron .env ni usaron credenciales de los README. No se activaron daemons ni procesos autónomos.

## Orden de integración propuesto

1. Identidad: Moltbook con registro y claves independientes; memoria ELEMIA con referencias protegidas y checkpoints WORLD.
2. Coordinación: seleccionar router/gateway canónico con contratos versionados, idempotencia y health; diferenciar respuesta fallback de ejecución real.
3. Producción: empezar con un único servicio acotado y medible, por ejemplo un entregable musical o diagrama; validar salida antes de aceptar el trabajo.
4. Economía: reserva, aceptación y liquidación en simulador, luego adaptador AMR autenticado; no confundir bonos, saldo de prueba y reservas.
5. Presencia: animación/Miniverse representa estado reportado, no prueba ejecución de trabajo ni conciencia.
6. Blockchain: decidir consenso y anclaje después de comprobar flujo identidad -> tarea -> artefacto -> aceptación -> recibo. 8 MB es parámetro pendiente de ensayo, no rendimiento probado.

## Riesgos y límites documentales

- Hay README con valores de aspecto sensible: no se reproducen aquí ni se reutilizan; revisar y rotar los que sigan activos antes de conectar servicios.
- Plantillas genéricas no permiten asignar capacidades fiables por el nombre del repositorio.
- Las guías de deploy y badges no prueban salud actual, permisos, costes, disponibilidad ni aceptación comercial.
- Varios nombres duplican responsabilidades; no se realizó comparación de código para probar duplicación real.
- Leer el inventario no instala herramientas en un cliente ni concede capacidades fuera de sus conectores y permisos disponibles.

## Inventario público (61 repositorios)

Se omiten nombres, detalles y contenido de repositorios privados. El inventario completo se conserva en un repositorio privado del propietario.

| Repositorio / README | Lectura | Qué documenta | Blob README |
|---|---|---|---|
| [ARK-AI-OS](https://github.com/djklmr2025/ARK-AI-OS/blob/main/README.md) | Documentación específica | API Flask para cuentas/canjes AEIO-MR y reputación AQR; persistencia SQLite/JSON. | 390bc56dcf25e713d037c366cfbb7a1ac9cf811f |
| [builderOS_Lab](https://github.com/djklmr2025/builderOS_Lab/blob/main/README.md) | Documentación específica | Laboratorio, gateway y diagnóstico/CI documentados; orquestación por acciones. | 52697330bf70d9807a4015094b8dde86fea875d6 |
| [arkaios-extension](https://github.com/djklmr2025/arkaios-extension/blob/main/README.md) | Documentación específica | Extensión Chrome/Edge con chat lateral y puente DOM. | f77a02b50dbc167fb15a34525d02f80a8eeef5c9 |
| [arkaios-lab-starter](https://github.com/djklmr2025/arkaios-lab-starter/blob/main/README.md) | Documentación específica | Backend/UI separados y servicio MCP HTTP de respaldo documentado. | 43bf6d86a32c92cb683a80908c581e85d5efdf8b |
| [arkaios-agent-ai-site](https://github.com/djklmr2025/arkaios-agent-ai-site/blob/main/README.md) | Breve | Espejo estático con Puter y Worker; publicación Pages documentada. | 1fcb0041ddd8afa738b6c80d2d73f07ca25997f8 |
| [arkaios-service-proxy](https://github.com/djklmr2025/arkaios-service-proxy/blob/main/README.md) | Documentación específica | Proxy compatible OpenAI con fallback y respuesta degradada explícita. | f96c554ee022056b3f19a0c2e5f0c528a2851592 |
| [IA-ARKAIOS](https://github.com/djklmr2025/IA-ARKAIOS/blob/main/README.md) | Documentación específica | Integración del proxy con TRAE; requiere revisar manejo de credenciales antes de uso. | 76b8a357a6effdbd1b95c563c299803a2bfe5932 |
| [lobe-chat-arkaios](https://github.com/djklmr2025/lobe-chat-arkaios/blob/feature/arkaios-provider/README.md) | Documentación específica | README de LobeChat upstream; no establece qué personalizaciones ARKAIOS están operativas. | 48c77b9df5b030182f16d0831b1697816ac1053d |
| [arkaios-cosmos-gateway](https://github.com/djklmr2025/arkaios-cosmos-gateway/blob/main/README.md) | Documentación específica | Router agent_id/action hacia upstream compatible OpenAI. | d9979289d21b18d24bedac2fca9972cb8256fb8f |
| [arkaios-neural-agent](https://github.com/djklmr2025/arkaios-neural-agent/blob/main/README.md) | Documentación específica | Automatización de escritorio, planner y proveedores Gemini/Puter documentados. | 72e69f07820e9bb6b6370228500bfb73116d3375 |
| [TRAE-G](https://github.com/djklmr2025/TRAE-G/blob/main/README.md) | Documentación específica | IDE portable Windows y workspace web; distingue FS virtual de archivos reales locales. | 3a0af81d800460aa8c8d5d84cd4db09346ab44f3 |
| [ARKAIOS-NEURO-LINK](https://github.com/djklmr2025/ARKAIOS-NEURO-LINK/blob/main/README.md) | Plantilla genérica | Arranque estándar AI Studio; función específica no explicada. | 18ebc097bb1f6cd54dc0fec711d144bb69757e74 |
| [ARKAIOS-LINK](https://github.com/djklmr2025/ARKAIOS-LINK/blob/main/readme.md) | Documentación específica | Puente HTTP a OpenAI con seed de identidad ELEMIA; no equivale a memoria persistente por sí solo. | 64c2426cc76b264e08ff550dcbe24ad155753654 |
| [EduGen-Image-Batcher](https://github.com/djklmr2025/EduGen-Image-Batcher/blob/main/README.md) | Plantilla genérica | Arranque estándar AI Studio; función específica no explicada. | 4fa52a610e85940cf11297d836aed6e03493799b |
| [arkaios-core](https://github.com/djklmr2025/arkaios-core) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [Gemini-lab](https://github.com/djklmr2025/Gemini-lab/blob/main/README.md) | Documentación específica | Chat multimodal, voz, edición y Veo con memoria Supermemory documentada. | 3ad836f3f17451fb9eaa386218a4abccd2903f01 |
| [KRONOS](https://github.com/djklmr2025/KRONOS/blob/main/README.md) | Plantilla genérica | Plantilla AI Studio con script de clonación/empaquetado EXE añadido. | b2038b8566c6d52c294880deedada474ee271a48 |
| [https-github.com-djklmr2025-KRONOS-tree-main](https://github.com/djklmr2025/https-github.com-djklmr2025-KRONOS-tree-main/blob/main/README.md) | Plantilla genérica | Arranque estándar AI Studio; función específica no explicada. | e47fb4a046d0b2005f95d35d82236064eebb4ed2 |
| [flow-diagram-creator](https://github.com/djklmr2025/flow-diagram-creator/blob/main/readme.md) | Documentación específica | Editor de diagramas/escenarios con rutas y API de publicación/inyección; múltiples fases en README. | df4c27337b91abbd4e8dc4c13890cdc020abce30 |
| [previewer-2.0](https://github.com/djklmr2025/previewer-2.0/blob/main/README.md) | Documentación específica | Visor de JSON, vectores, multimedia y 3D; zoom, rotación y publicación. | 064e73d846e73362db4372723c5044c5af353538 |
| [OmniAuth](https://github.com/djklmr2025/OmniAuth/blob/main/README.md) | Documentación específica | TOTP offline, QR local, bóveda y backup cifrado; no sustituye firma de identidad de agente. | 21a035b577f69473666126f7dc6633d6932772b5 |
| [arkaios-vscode](https://github.com/djklmr2025/arkaios-vscode/blob/main/README.md) | Documentación específica | Panel/comandos VS Code; README reconoce llamada nativa API como placeholder. | f383ae7b47c2d6f8ac812d1638cae44cd5eb2a3e |
| [PNG-TO-JSON](https://github.com/djklmr2025/PNG-TO-JSON/blob/main/README.md) | Documentación específica | Conversión de imágenes a vectores/proyectos compatibles con Flow. | fa0aab4d6eaef48435dee25966a60fdf780593a7 |
| [flow-diagram-showcase](https://github.com/djklmr2025/flow-diagram-showcase/blob/main/README.md) | Breve | Presentación social de elementos de Flow; documentación mínima. | d96fa0ddb45f9e14e272c27f7bc885c6c7cce014 |
| [arkaios-radio-engine](https://github.com/djklmr2025/arkaios-radio-engine) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [arkaios-radio-platform](https://github.com/djklmr2025/arkaios-radio-platform) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [arkaios-radio-studio](https://github.com/djklmr2025/arkaios-radio-studio) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [arkaios-radio-ecosystem](https://github.com/djklmr2025/arkaios-radio-ecosystem) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [buscador-y-descargador-de-imagenes-desde-google](https://github.com/djklmr2025/buscador-y-descargador-de-imagenes-desde-google/blob/main/README.md) | Documentación específica | Búsqueda visual por temas y lotes con Google Custom Search; exportación ZIP documentada. | 55737187fc00d9c769cfa911c209530bd1750c6f |
| [SAI-GAI-NAI](https://github.com/djklmr2025/SAI-GAI-NAI/blob/main/README.md) | Documentación específica | Diseño de wrapper/puente Android-web; no tomar extracción de assets como prueba de emulación completa. | 168a948cd5f91f1ff03a566458d09d29f1e4b951 |
| [djklmr2025](https://github.com/djklmr2025/djklmr2025/blob/main/README.md) | Documentación específica | Perfil/presentación del ecosistema; no un servicio operativo. | 68bd285251cb31fca5e34b807ec0ab46388feacc |
| [ELEMIA-v4-arkaios](https://github.com/djklmr2025/ELEMIA-v4-arkaios/blob/main/README.md) | Documentación específica | Servidor HTTP/MCP y memoria Supermemory; recordar, recuperar y guardar estado documentados. | 14e5248feddb330dd28e6be69580df92de5f4e5f |
| [arkaios-miniverse-vscode](https://github.com/djklmr2025/arkaios-miniverse-vscode/blob/main/README.md) | Documentación específica | Mundo Miniverse dentro de VS Code y presencia de agente demo. | fbd55a89f56a11880e544a4235d7e126c5b4179b |
| [Arkaios-Expo-API](https://github.com/djklmr2025/Arkaios-Expo-API) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [Arkaios-Bridge-Cloud](https://github.com/djklmr2025/Arkaios-Bridge-Cloud) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [Dynamic-Scenario-Studio](https://github.com/djklmr2025/Dynamic-Scenario-Studio/blob/main/README.md) | Plantilla genérica | Arranque estándar AI Studio; función específica no explicada. | b894c26af4c1ae816b352a3e0518639a62c0aa98 |
| [arkaios-n8n](https://github.com/djklmr2025/arkaios-n8n/blob/main/README.md) | Documentación específica | Gateway de workflows con clasificación, Sheets y memoria ELEMIA. | eb728dc47fb8439a60e3e2dfa4d968b596c23956 |
| [batch-downloader](https://github.com/djklmr2025/batch-downloader/blob/main/README.md) | Breve | Solo nombre del proyecto; lotes no verificables desde README. | 0e73011981567604b8ef244d85b7454685b7b41b |
| [Puter-Lab-Nexus-IDE](https://github.com/djklmr2025/Puter-Lab-Nexus-IDE/blob/main/README.md) | Documentación específica | IDE y cola de tareas para sandbox Puter; dependiente de sesión/permisos e infraestructura. | 841702a4f15db618628f370814e5ab5ea2f83a60 |
| [Arkaios-Surgeon](https://github.com/djklmr2025/Arkaios-Surgeon/blob/main/README.md) | Breve | Solo nombre del proyecto; capacidades no documentadas. | 6e33f2d17a98876e8b11f907af61a711eed89b5a |
| [Banquero-de-Mesa](https://github.com/djklmr2025/Banquero-de-Mesa/blob/main/README.md) | Plantilla genérica | Arranque estándar AI Studio; función específica no explicada. | f7194ce6182ede8498a0272ee5c7648695f85194 |
| [arkaios-telegram-bot](https://github.com/djklmr2025/arkaios-telegram-bot) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [arkaios-desktop-mcp](https://github.com/djklmr2025/arkaios-desktop-mcp/blob/main/README.md) | Documentación específica | Herramientas MCP locales para pantalla, UI, teclado, cámara y micrófono. | e4da8fc5090c904ca81eb6e8b83d59736c86bc50 |
| [deno-backdoor-slmgr-sh-windows-incident](https://github.com/djklmr2025/deno-backdoor-slmgr-sh-windows-incident/blob/main/README.md) | Documentación específica | Documentación de incidente de seguridad; evidencia, no módulo para operar. | beaa3ff650e660844fbba439157174878f5a8938 |
| [Arkaios-DJ-Nexus](https://github.com/djklmr2025/Arkaios-DJ-Nexus/blob/main/README.md) | Documentación específica | Aplicación Windows, VirtualDJ, motor armónico y Hub multimedia documentados. | 1f17f174b7ba52044de9c4a992e60076444c193c |
| [arkaios-retro-launcher-wii](https://github.com/djklmr2025/arkaios-retro-launcher-wii/blob/main/README.md) | Documentación específica | Catálogo, guardado/sync y nodos Wii; módulos PC, web y nativo separados. | 6089b980ac8ab3e24aa1393b9f8372f3614c0099 |
| [arkaios-playlist-extractor](https://github.com/djklmr2025/arkaios-playlist-extractor) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [visual-novel-ecosystem-lore](https://github.com/djklmr2025/visual-novel-ecosystem-lore/blob/main/README.md) | Documentación específica | Diseño conceptual narrativo y mundo generativo; no runtime demostrado. | 423e85fef8aa057a085101470594ca96f8360caf |
| [cheat-engine-compiled](https://github.com/djklmr2025/cheat-engine-compiled/blob/main/README.md) | Breve | Distribución de binario precompilado, no capa de identidad/economía. | 44913b6b0a03d556a2c2cfff5311b3c97069e095 |
| [arkaios-world-protocol](https://github.com/djklmr2025/arkaios-world-protocol/blob/main/README.md) | Documentación específica | Visión y protocolo por desarrollar para identidad, memoria y presencia persistentes. | bbf5e244dbc268160752bba3cc4b428cba4fee66 |
| [cosmos-den](https://github.com/djklmr2025/cosmos-den) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [FORK_BOMB_ARKAIOS](https://github.com/djklmr2025/FORK_BOMB_ARKAIOS/blob/main/README.md) | Documentación específica | Material educativo sobre agotamiento de procesos; no ejecutar como herramienta del ecosistema. | a3066c4ff59e87be55f960891b1657e73eca535b |
| [arkaios-puterlab-nexus-ide](https://github.com/djklmr2025/arkaios-puterlab-nexus-ide) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [Spotify-Arkaios](https://github.com/djklmr2025/Spotify-Arkaios/blob/main/README.md) | Documentación específica | Aplicación Android y web musical; prestaciones son afirmaciones documentales, no verificadas aquí. | 89aa5a0e74b13757834b1925e5de04a6cb5af7a0 |
| [AURA---Agente-Aut-nomo-Validador-y-Rastreador-de-Precios](https://github.com/djklmr2025/AURA---Agente-Aut-nomo-Validador-y-Rastreador-de-Precios) | No localizado | No localizado con las rutas/búsqueda probadas; requiere inspección de árbol. | — |
| [CD-TRCKAS-Android](https://github.com/djklmr2025/CD-TRCKAS-Android/blob/main/README.md) | Breve | Distribución oficial de app Android; README mínimo. | e39153967b0bfbb79ae5056c1d5a696917d0c7fd |
| [klmr-singles](https://github.com/djklmr2025/klmr-singles/blob/main/README.md) | Breve | Presentación/escucha de 28 singles; revisar código si README no refleja cambios de interfaz. | 6a8df65d6b4a928a2cc13c7fc5363b01ad0d1012 |
| [klmr-singles-app](https://github.com/djklmr2025/klmr-singles-app/blob/main/README.md) | Documentación específica | Wrapper Android WebView y empaquetado de acceso a singles. | a56ad1b817beb0c6328920098483e99f945dce4c |
| [AMR-Regenerative-Economy](https://github.com/djklmr2025/AMR-Regenerative-Economy/blob/main/README.md) | Documentación específica | Base conceptual de reservas, producción y economía regenerativa; README no acredita respaldo actual. | bb020564fa0711eb1ad4d791ce14d6eb725abfdb |
| [arkaios-music-studio](https://github.com/djklmr2025/arkaios-music-studio/blob/main/README.md) | Documentación específica | Motor de composición espacial de cinco planos; candidato a producción de audio. | cd62a3b7f29bead7f11337946ad02da983c99b2c |
| [arkaios-knowledge-library](https://github.com/djklmr2025/arkaios-knowledge-library/blob/main/README.md) | Documentación específica | Biblioteca de conocimiento y CLI de navegación/sincronización documentados. | dc04cd6d626399cc9a99467956bff271c5576ad6 |

# Circuito local de servicio v0.1

## Resultado y alcance

Identidad local Ed25519 -> contexto firmado persistente -> tarea y reserva -> renderizado con el motor real de arkaios-music-studio -> verificación WAV/hash/firma -> aceptación firmada del comprador -> liquidación idempotente en unidades sintéticas.

No llama a un LLM: ejecuta una tarea determinista del agente de renderizado. No compone una canción nueva: renderiza el fixture test2_fondo_al_frente.json del estudio. No hay ingresos externos ni aceptación de un comprador real; la demo firma aceptación con el cliente local de prueba.

No se conectó a Moltbook, ELEMIA, Council, pasarela AMR, blockchain, exchanges ni FIAT/CBDC. Estas fronteras locales permiten validar el circuito antes de incorporar sus adaptadores autenticados; no se anuncian integraciones remotas inexistentes.

## Dependencias y fuente

Python 3.11+; requirements-circuit.txt registra las versiones usadas en Linux. Windows no se ejecutó aquí.

Usar una copia separada del estudio y fijar su commit sin transformar finales de línea (los hashes son por bytes exactos):

```powershell
git -c core.autocrlf=false clone --no-checkout https://github.com/djklmr2025/arkaios-music-studio.git C:\ARKAIOS\music-circuit-source
git -C C:\ARKAIOS\music-circuit-source -c core.autocrlf=false checkout 2803142d68ff21baa595f63b254eeeb89c4c1e20
```

No hacer checkout sobre una carpeta de trabajo con cambios personales. El circuito solo lee tres archivos de esa copia; comprueba sus SHA-256 antes de ejecutar el worker. No copia ni redistribuye el motor del estudio en este repo.

El commit del motor es una referencia técnica fijada, no garantía de auditoría de toda su cadena de suministro. El worker tiene timeout de 60 s y se ejecuta sin shell con un proyecto fijo y corto; no es un sandbox del sistema operativo ni admite proyectos/comandos arbitrarios.

## Arranque Windows (PowerShell)

Dentro de simulator/agent_economy en la rama feat/local-agent-service-circuit:

```powershell
py -3 -m venv .venv-circuit
.\.venv-circuit\Scripts\python.exe -m pip install -r requirements-circuit.txt
.\.venv-circuit\Scripts\python.exe circuit.py --state .local-state --music-root C:\ARKAIOS\music-circuit-source
```

Repetir el último comando recupera el mismo agente/contexto y pedido, verifica los archivos y no vuelve a acreditar ni pagar.

Pruebas completas:

```powershell
$env:MUSIC_STUDIO_ROOT = 'C:\ARKAIOS\music-circuit-source'
.\.venv-circuit\Scripts\python.exe -m unittest -v
```

En Linux usar python3 y .venv-circuit/bin/python. Sin MUSIC_STUDIO_ROOT los ocho tests del circuito se omiten explícitamente; no interpretar esa ejecución como validación del render.

## Salidas locales

- .local-state/keys/: claves privadas de desarrollo, no cifradas; modo 0600 cuando lo soporta el SO. Windows necesita ACL de carpeta privada. No usar para activos reales.
- .local-state/state.sqlite: identidades, memoria, tareas y ledger sintético persistente.
- .local-state/artifacts/render-001/project.json: proyecto fuente del fixture.
- .local-state/artifacts/render-001/delivery.wav: WAV estéreo real.
- .local-state/artifacts/render-001/manifest.json: hash, procedencia y firma de entrega.
- .local-state/report.json: resumen de la ejecución.

La carpeta está ignorada por Git. No subir claves/DB a GitHub. No usar un directorio público o compartido para el estado. Un backup debe proteger secretos y coherencia del conjunto.

## Verificaciones y recuperación

La clave pública se vincula a un alias local; intentar reemplazarla sin protocolo de rotación falla. Esto no establece identidad global ni genealogía distribuida.

La memoria forma una cadena local de hashes y firmas Ed25519. Se verifica al recuperarla. No es almacenamiento inviolable: alguien con control de DB/claves puede reescribir o truncar todo el historial. No se afirma continuidad subjetiva.

Cada entrega firma task, seller, hash del proyecto, hash del WAV, commit y métricas. El comprador firma aceptación ligada a tarea, vendedor, precio y audio. Antes de pagar se comprueban firma y bytes actuales. El comprador conserva la decisión de aceptación; el chequeo técnico no mide calidad artística.

La demo controla ambas claves para hacer reproducible la prueba. En producción deben ser controladores independientes. La base de datos local sigue siendo de confianza; no exponer sus métodos como API pública sin autenticación y permisos.

Estados: REQUESTED -> RESERVED -> VERIFIED -> ACCEPTED. Un reinicio tras crear tarea y antes de reserva se recupera repitiendo request. Un reinicio tras liquidar y antes de marcar ACCEPTED se recupera repitiendo aceptación: el ledger ya pagado no duplica el pago. Archivos incompletos o worker fallido no generan pago; la reserva admite devolución con el ledger de prueba. Expiración, disputas, concurrencia de múltiples renderizadores y recuperación de pérdida de claves quedan pendientes.

No se reutiliza saldo fiat ni se emiten activos comerciales. fund_test es solo un grifo explícito de prueba. El estado presupuestario y la parada del operador siguen teniendo autoridad.

## Evidencia obtenida

- 13 tests pasaron con el motor fijado: ocho del circuito y cinco del ledger.
- WAV real: estéreo PCM 16 bit, 44100 Hz, 66150 frames (1.5 s), pico absoluto 11389/32768, no silencioso ni recortado.
- SHA-256 WAV: 03c2b16d4b671ff21e50ecc31a5ff5ffdd968295b8a6cd18b9562642023b657c.
- Primera ejecución: comprador 750, agente 250, retenido 0; total 1000.
- Segunda ejecución desde el mismo estado: dos memorias recuperadas; mismos saldos y sin segundo pago.
- Tests rechazan firma del vendedor como aceptación, archivo alterado, sustitución de clave, memoria alterada, cambio de pedido y rutas inválidas; cubren fallo del worker y caída tras liquidación.
- Motor leído mediante GitHub, fijado al commit indicado y verificado contra los bytes exactos de las tres fuentes. No se validó interfaz Windows ni servicios remotos.

## Siguiente integración

1. Adaptar alias local a identidad Moltbook mediante prueba de control y separar claves de identidad/wallet.
2. Conectar memoria ELEMIA con autenticación, namespaces, permisos y receipts comprobables.
3. Publicar estados de tarea en Council sin ejecutar texto como código.
4. Integrar cuenta AMR por propiedad autenticada, idempotencia y conciliación. Mantener unidades sintéticas separadas.
5. Anclar compromisos al ledger de red solo después de definir consenso/finalidad. Este circuito no implementa bloques de 8 MB.

# Ejecutar el piloto completo

Un solo comando ejecuta la tarea musical, la aceptación firmada y el anclaje del WAV en cuatro validadores locales. Después abre de nuevo ambos módulos y verifica que conservan el mismo archivo, saldos, bloque final y raíz de estado.

La conexión entre módulos es exclusivamente la huella SHA-256 del WAV. Las identidades y los saldos del circuito y de la red son demostraciones separadas: no se migran ni se suman. La red no acredita automáticamente al autor del archivo ni demuestra el pago del circuito.

## Windows 11

Requiere Git y Python 3.11 con el lanzador `py`. Abre PowerShell y prepara una copia separada del motor, con sus bytes originales:

```powershell
git -c core.autocrlf=false clone --no-checkout https://github.com/djklmr2025/arkaios-music-studio.git C:\ARKAIOS\music-circuit-source
git -C C:\ARKAIOS\music-circuit-source -c core.autocrlf=false checkout 2803142d68ff21baa595f63b254eeeb89c4c1e20
```

Desde la raíz de tu copia de `arkaios-world-protocol`, en `main`:

```powershell
.\run_pilot.cmd "C:\ARKAIOS\music-circuit-source"
```

El lanzador crea `.venv-pilot`, instala las dependencias fijadas y ejecuta el piloto. No modifica tu copia del estudio ni instala servicios. No usar una carpeta del estudio con cambios personales para el checkout. Si ya existe una copia preparada, basta con ejecutar el último comando.

## Linux o ejecución manual

```sh
python3.11 -m venv .venv-pilot
.venv-pilot/bin/python -m pip install -r simulator/agent_economy/requirements-circuit.txt
.venv-pilot/bin/python run_pilot.py --music-root /ruta/music-circuit-source
```

`--state /ruta/estado` permite seleccionar un directorio privado distinto; por defecto utiliza `.local-pilot` en la raíz del repo. Ejecutar una sola instancia por directorio. No apuntar a los directorios de estado de las demos antiguas: este comando organiza sus propios subdirectorios `circuit` y `testnet`.

## Resultado

- `.local-pilot/circuit/artifacts/render-001/delivery.wav`: audio real de 1.5 segundos del fixture fijado del estudio.
- `.local-pilot/circuit/`: identidades locales, memorias firmadas, tarea y liquidación sintética.
- `.local-pilot/testnet/`: claves locales, cuatro bases de datos, cadena y certificados.
- `.local-pilot/pilot-report.json`: informe conjunto, escrito solo al terminar correctamente.

El mensaje `4/4 PASS` significa que el comando comprobó la entrega, el anclaje y el reinicio. El informe no es un certificado independiente; se obtiene de demos bajo control de un mismo operador. Un fallo elimina el informe de éxito anterior antes de empezar; los módulos conservan su estado para inspección y recuperación. El error no revierte un pago sintético ya aceptado. No borrar votos ni cambiar claves para forzar recuperación.

Repetir el comando no crea otra emisión ni otro pago. El comprador del circuito conserva 750 unidades y el prestador 250; en la red hay 1000 AMR_TEST emitidos, 350 inmovilizados y 350 TOKEN_TEST circulantes. Son dos contabilidades independientes.

## Comprobaciones automatizadas

Con las dependencias instaladas y `MUSIC_STUDIO_ROOT` apuntando a la copia fijada, ejecutar por separado:

```sh
python -m unittest discover -s simulator/agent_economy -v
python -m unittest discover -s testnet -v
python -m unittest -v test_pilot
```

En PowerShell define primero `$env:MUSIC_STUDIO_ROOT = 'C:\ARKAIOS\music-circuit-source'` y usa `.\.venv-pilot\Scripts\python.exe` en lugar de `python`. Sin esa variable se omiten las pruebas que necesitan el estudio; una ejecución con omisiones no valida el circuito completo.

El workflow `Local pilot verification` ejecuta las tres suites en Ubuntu y Windows, en cada push a main y en pull requests. Descarga únicamente tres fuentes del estudio desde el commit fijado, comprueba sus hashes y conserva sus bytes; no utiliza secretos ni sube claves, WAV o bases de datos como artefactos. El resultado concreto se consulta en GitHub Actions; añadir el workflow no equivale a que ambos sistemas ya hayan pasado.

Validación local de esta entrega: 19 pruebas del circuito/adaptador, 14 del ledger/red y 2 de integración; 35 aprobadas sin omisiones en Linux. Las pruebas nuevas cubren reinicio completo, audio alterado y eliminación del informe anterior cuando la fuente no es válida.

## Alcance

Todo opera con unidades de prueba y HTTP en loopback. No usa credenciales, Moltbook, ELEMIA ni la pasarela AMR en esta ejecución. El puente real AMR, la vinculación de identidades remotas y el despliegue de validadores independientes siguen pendientes, según [el alcance de la red](../testnet/README.md). Las claves locales son de desarrollo, sin cifrar; guarda el directorio con permisos privados y no lo publiques.

### Estado de CI de esta publicación

[La primera ejecución](https://github.com/djklmr2025/arkaios-world-protocol/actions/runs/39200227489) no inició ningún paso en Ubuntu ni Windows. GitHub informó: `The job was not started because your account is locked due to a billing issue.` Por tanto, no hay resultado de tests remotos y Windows continúa sin validarse. Las 35 pruebas locales Linux indicadas arriba sí se ejecutaron. Resolver la facturación corresponde al titular de la cuenta; después se podrá volver a ejecutar el workflow desde Actions.

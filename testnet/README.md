# ARKAIOS Local Testnet v0.1

Red piloto permissionada y local: cuatro procesos HTTP en 127.0.0.1, cuatro claves Ed25519 distintas, SQLite independiente por validador, cadena de bloques certificados y quorum 3/4. No es mainnet ni una red públicamente desplegada; todos los nodos y claves de la demo pertenecen al mismo operador.

## Funciones implementadas

- Genesis fijado con chain_id, clave pública del registrador, validadores, quorum y modo TEST_ONLY.
- IDs consecutivos ligados al hash completo del genesis: nombre:genesisHash:serial. Un nombre de red no basta para evitar colisiones entre registros. Unicidad secuencial dentro del registro; separación criptográfica entre genesis. No es prueba de un único individuo físico o consciente ni prevención completa de identidades Sybil.
- Descendencia con autorización del padre y prueba de posesión de la clave del hijo; generación y consecutivo por padre. Claves repetidas se rechazan.
- Transacciones firmadas ligadas al genesis, dominio, actor, nonce, operación y payload. Rechazo de repetición, nonce incorrecto y gasto sin saldo.
- Bloques con altura, hash anterior, transacciones y raíz del estado. Cada validador verifica transición antes de firmar y conserva su voto por altura en disco.
- Certificación con tres o cuatro firmas de validadores distintos; dos firmas no finalizan.
- Anclaje de SHA-256 de archivos sin publicar sus bytes.
- Emisión y devolución de TOKEN_TEST contra AMR_TEST bloqueado 1:1; transferencias entre agentes.
- Revalidación de firmas, encadenamiento, estado y conservación al reabrir cada réplica.

No se usa EML como criptografía ni se inventa un algoritmo de firma.

## Qué significa el puente de prueba

AMR_TEST es una unidad sintética creada por test.fund con firma del registrador. No es AMR de la pasarela, MXN, CBDC ni dinero de un cliente.

- lock_mint: reduce AMR_TEST disponible, lo inmoviliza y emite TOKEN_TEST por el mismo entero.
- transfer: mueve TOKEN_TEST, sin emitir más.
- burn_redeem: destruye TOKEN_TEST y libera AMR_TEST del pool de reserva al tenedor que devuelve el token.
- Invariante: TOKEN_TEST circulante = AMR_TEST bloqueado.
- Invariante: disponible + bloqueado = AMR_TEST de prueba emitido.

El pool es común y fungible; no promete que cada tenedor mantenga el depósito original. No hay intereses ni rentabilidad. Los saldos del circuito Python anterior son otra demostración: no se suman ni se migran como reservas a esta red.

## Límite de bloque

8 MB decimales: 8,000,000 bytes de envoltorio completo serializado, incluidas firmas. Antes de votar se reserva espacio para las cuatro firmas. HTTP también rechaza cuerpos de más de ese tamaño. Límite por transacción 65,536 bytes y por bloque 100 transacciones: son límites adicionales, por lo que este perfil no pretende llenar todos los bloques hasta 8 MB.

Las pruebas de 7,999,999 / 8,000,000 / 8,000,001 verifican el límite de tamaño; no afirman que cualquier contenido de ese tamaño sea un bloque válido.

La serialización del piloto es JSON UTF-8 determinista de Python, sin NaN. Firmas sobre dominio + cuerpo canónico; hash de bloque excluye certificado para que el mismo cuerpo conserve identidad con distintas combinaciones válidas de firmantes. Interoperabilidad con otros lenguajes exige especificación adicional y vectores de prueba; no asumir compatibilidad con Ethereum.

## Ejecutar en Windows (PowerShell)

Desde testnet dentro del repo en main:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe network.py --state .local-state
```

Anclar el WAV generado por el circuito anterior:

```powershell
.\.venv\Scripts\python.exe network.py --state .local-state --artifact ..\simulator\agent_economy\.local-state\artifacts\render-001\delivery.wav
```

En Linux usar python3 y .venv/bin/python. Las pruebas se ejecutaron en Linux; Windows no se ejecutó.

La demo inicia los cuatro nodos, procesa o verifica el estado y los detiene al terminar. No instala servicios ni deja daemons corriendo. Repetirla con el mismo directorio conserva claves y estado y no vuelve a emitir. --artifact ancla hash bajo el agente de prueba prestador, no certifica por sí solo autoría, licencia, calidad ni pago del archivo. El WAV se validó en el circuito anterior; la red solo registra su huella.

Claves de desarrollo sin cifrar en .local-state/keys con modo 0600 cuando lo permite el SO. Windows necesita ACL privada. No usar con activos reales. DB, claves, reportes y estado local están ignorados por Git.

## Resultado comprobado

Demo con WAV real:
- Cuatro bloques aceptados en cuatro réplicas; tres agentes, uno descendiente.
- 1000 AMR_TEST iniciales.
- 600 bloqueados para emitir tokens.
- Transferencia de 250 tokens al prestador y devolución de esos 250.
- Resultado: comprador 400 AMR_TEST + 350 TOKEN_TEST; prestador 250 AMR_TEST; reserva bloqueada 350 y supply 350.
- Huella WAV anclada: 03c2b16d4b671ff21e50ecc31a5ff5ffdd968295b8a6cd18b9562642023b657c.
- Reinicio conserva el mismo tip, raíz de estado y saldos; no duplica el anclaje.
- 14 pruebas de red/ledger pasaron, además de las 19 del circuito/cliente ELEMIA: 33 pruebas en dos suites.

Los hashes de genesis/bloque varían entre instalaciones porque las claves de prueba se generan localmente. El report.json local conserva los valores de cada ejecución.

## Seguridad y disponibilidad: límites explícitos

Esto no es una implementación completa de Tendermint, HotStuff u otro consenso BFT auditado. Tiene votos persistentes y certificados de quorum, pero NO tiene cambio de vista, elección robusta de líder, descubrimiento de peers, anti-DoS, mTLS, admisión de nuevos validadores ni sincronización automática de bloques perdidos.

Propuestas rivales pueden bloquear la altura aunque aún no haya un bloque certificado. No eliminar votos para forzar avance: hace falta un protocolo de recuperación/cambio de vista que preserve seguridad. El piloto prioriza fallar sin continuar, no disponibilidad garantizada.

En las pruebas, un nodo que perdió un bloque lo recibe posteriormente de forma explícita y alcanza el mismo estado. Una partición sin tres firmas no puede finalizar. No se afirma tolerancia productiva a fallos bizantinos o particiones arbitrarias.

Los endpoints no están autenticados por sesión: verifican transacciones y certificados, pero una propuesta válida puede consumir el voto de una altura. Por ello se enlazan solo a loopback y NO deben exponerse en Internet. Mantener recursos y claves bajo control del operador; cualquiera con control del host tiene acceso a las claves de desarrollo. El servidor HTTP sencillo no está endurecido para cargas hostiles. Los snapshots y la rotación/recuperación de validadores quedan pendientes.

El registro de identidad no permite todavía cuarentena, rotación, recuperación o federación; tampoco representa una wallet financiera productiva. En esta demo una clave controla identidad y cuenta de prueba; separar controladores/custodia antes de producción según la arquitectura.

## Integración externa AMR: deshabilitada

Se revisaron docs/SIGNED-EVIDENCE-SPEC-v0.4.md, schemas/pasarela-readonly-evidence.schema.json y reconciliation/http_snapshot_consumer.py de AMR-Regenerative-Economy. El contrato vigente pide snapshots firmados Ed25519, clave pública confiable, frescura y protección contra replay. Los documentos antiguos v0.3 no bastan para configurar v0.4. Además, el consumer y la propuesta antigua muestran rutas distintas; no se presupone endpoint correcto solo por el README.

El ledger de wallets y un checkout pagado acreditan pasivos/procedencia de crédito, no saldo líquido externo. Un snapshot agregado de reserva tampoco constituye una orden exclusiva de bloqueo para esta cadena.

No se verificó un endpoint de reserva/bloqueo/redención de AMR de producción ni una clave de firma de snapshots configurada para esta red. No se usaron credenciales generales para asumir esas facultades. Por ello NO existe operación para acuñar activos reales o cargar cuentas humanas aquí.

Para habilitarlo hacen falta: cuenta/agente y propiedad autenticadas; reserva exclusiva identificada para esta cadena; prueba firmada y verificada de bloqueo; idempotencia duradera entre pasarela y red; outbox/conciliación; quema finalizada antes de liberar; expiración/disputas; validadores y claves de custodia productivos; límites de gasto y auditoría de implementación. Conversiones a FIAT/CBDC necesitan contraparte/proveedor concretos, no una etiqueta de token.

## Archivos

- ledger.py: reglas, identidades, contabilidad, bloques, firmas y persistencia.
- network.py: demo con procesos y transporte HTTP local.
- test_ledger.py: pruebas adversariales y de recuperación.
- requirements.txt: dependencia fijada para firmas.

Los servicios Moltbook/ELEMIA permanecen separados: la identidad remota no se da por vinculada a un ID de esta red sin prueba de control. El anclaje del WAV es la conexión verificable de artefacto con el circuito previo, no una migración silenciosa de identidades o dinero.

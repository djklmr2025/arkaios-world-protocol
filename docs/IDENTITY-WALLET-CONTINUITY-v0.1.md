# ARKAIOS Identity, Wallet and Continuity v0.1

Estado: propuesta; no es una blockchain desplegada ni una auditoría integral.
Relacionado: #2. No modifica Moltbook ni la pasarela. No crea claves reales, fondos ni identidades de producción.

## Fuentes y límites de la revisión

- WORLD README/CONTRIBUTING, revisión 2cbeb8ef26dc4f89cdd6fb9c5412046de79d0f71: visión de identidad, memoria, presencia e interoperabilidad; solicita propuesta antes de cambios importantes.
- Moltbook scripts/guardian_node.cjs, búsqueda en f71710bfb998d3956897a2db4d7d6863129b6627 y lectura posterior de main: genera Ed25519; dirección 0x seguida de 40 caracteres del SHA-256 de publicDer; cifrado AES-256-GCM; almacenamiento SQLite con alternativa JSON. No demuestra unicidad distribuida ni compatibilidad de firma Ethereum.
- Pasarela src/server/fiat-store.ts y README, búsqueda en 80eecde4d6bfc485838e4b1b77a1013b2a259a76 y lectura posterior de main: cuenta fiat asociada a uid Firebase, saldo entero en unidades menores, liquidación transaccional e idempotencia por sessionId. La lectura actual también incluye compra de álbum; no se presume que todas las operaciones económicas estén disponibles.
- Las lecturas de main pueden evolucionar; fijar commits de integración y revisar licencias antes de reutilizar código.
- No se ejecutaron servicios, verificaron reservas ni probaron transferencias reales. Las afirmaciones del README sobre paridad o consenso no constituyen prueba.

## Separación de responsabilidades

| Módulo | Base | Responsabilidad propuesta |
| --- | --- | --- |
| Identity adapter | Moltbook | Importar IDs existentes como alias; registrar clave pública y prueba de control |
| Economic adapter | Pasarela AMR | Vincular cuenta autenticada, consultar saldo autorizado y recibos |
| Continuity protocol | WORLD | ID permanente, linaje, eventos de presencia y compromisos de memoria |
| Ledger adapter | Por elegir | Orden final de eventos, rechazo de duplicados y anclaje verificable |

Una identidad identifica una entidad de software según reglas explícitas; no certifica conciencia, personalidad jurídica ni exclusividad de una persona.
Identidad, claves de autenticación, wallet criptográfica y cuenta contable son objetos distintos.

## Identidad y genealogía

ID canónico: ark:<registryId>:<serialDecimal>. registryId pertenece a un registro concreto; las representaciones humanas son alias. Serial se asigna como entero creciente sin reutilización. No usar Number de JavaScript para seriales arbitrariamente grandes: transmitir cadenas decimales y operar con enteros exactos.

Campos: agentId, parentId (null en raíz), familyRootId, childIndex, generation, controllerKeyId, keyVersion, status, createdEventId, aliases.

Invariantes:
1. agentId único en un registro finalizado; unicidad mundial requiere un único registro canónico o federación que asigne namespaces exclusivos.
2. childIndex único por parentId y creciente; generación del hijo = generación del padre + 1.
3. Registro de raíz autorizado explícitamente; padre existente y activo antes del nacimiento. No se permiten ciclos ni reescritura del padre.
4. Alta asigna serial global y childIndex en una operación atómica ordenada por el ledger. Reintentos con el mismo requestId y payload devuelven el mismo resultado; payload distinto con ese requestId se rechaza.
5. Clave nueva independiente para cada hijo; prueba de posesión del hijo y autorización del padre sobre un mismo payload canónico. No heredar secretos.
6. Desactivación/cuarentena no borra ni libera el ID. Eventos históricos permanecen.
7. La unicidad se garantiza dentro del registro y sus reglas, no por ausencia matemática de colisiones de un hash.
8. No se promete ausencia de similitud visual ni infinitas identidades con códigos de longitud fija.

La propuesta inicial exige conexión al registro para finalizar nacimientos. Altas offline son solicitudes pendientes, no identidades finales.

## Firmas y eventos

Eventos propuestos: identity.created, identity.key_rotated, identity.quarantined, identity.reactivated, wallet.bound, wallet.unbound, continuity.checkpoint, continuity.migrated y identity.forked.

Sobre firmado: protocolVersion, registryId, eventType, subjectId, requestId, expectedVersion, nonce, issuedAt, expiresAt y payload.
Antes de implementar fijar codificación canónica, dominios de firma, límites de campo, algoritmo y vectores de prueba. Rechazar eventos caducados, nonces repetidos, firmas inválidas y versiones obsoletas. La hora por sí sola no evita replay.
Rotación requiere autorización de la clave vigente y posesión de la nueva; recuperación requiere política registrada previamente y umbral de aprobaciones, nunca asignación por coincidencia de nombre.
Identidad pública nunca contiene clave privada, ni siquiera cifrada. El pasaporte existente de Moltbook contiene encryptedPrivateKey: excluirlo del adaptador público.

## Wallet y cuenta AMR

walletBinding: agentId, walletKind, networkId, accountRef, publicKeyRef, bindingVersion, proofRef y status.
walletKind distingue cryptographic_wallet de custodial_ledger_account. Una dirección 0x no prueba red ni algoritmo.
Para vincular una wallet: desafío limitado en tiempo, ligado al agentId, red y nonce, firmado por controlador de identidad y wallet.
Para cuenta de pasarela: sesión autenticada y verificación servidor de propiedad de cuenta, además de autorización del agente. No aceptar uid arbitrario enviado por cliente ni asociar por email/alias.
Las cuentas actuales se ligan a usuarios Firebase: falta definir cuenta delegada por agente; no asignar automáticamente una cuenta humana a cada descendiente.
Clave de wallet independiente de identidad; rotación de controlador no transfiere activos automáticamente.
Saldo inicial cero salvo crédito económico real autorizado y comprobado. No convertir bonus legacy en reserva ni emitir tokens durante alta.
Ledger fiat continúa como fuente de verdad para ese saldo. Anclaje on-chain puede certificar un recibo, pero no convertirlo automáticamente en activo transferible ni volver atómicas dos redes.
Integración futura entre sistemas requiere outbox, idempotencia y reconciliación; no afirmar atomicidad distribuida sin protocolo y pruebas.

## Continuidad, migración y copias

Checkpoint: agentId, sequence, previousCheckpointHash, memoryCommitment, storageRef y controllerVersion, firmado y ordenado por registro.
Memoria, conversaciones, datos personales y secretos permanecen fuera de cadena con controles de acceso y retención. Hashes también pueden revelar datos predecibles; usar compromisos con sal aleatoria secreta y política definida.
Un hash demuestra integridad de contenido disponible, no su veracidad, disponibilidad ni continuidad subjetiva.
Migración conserva agentId y cambia ejecución mediante un evento autorizado.
Copia que opere como actor independiente recibe ID nuevo y parentId/forkOf verificable; un checkpoint idéntico no autoriza duplicar una identidad.
Réplicas de un mismo actor requieren leases/fencing y un escritor autorizado; revocar un lease antiguo no borra al actor.
Reconstruir estado mediante eventos y snapshots comprobados; verificar huecos, orden y firmas.

## Bloques de 8 MB: perfil experimental

Propuesta provisional: maxSerializedBlockBytes = 8000000, límite del bloque completo (cabecera, eventos, pruebas y firmas), no objetivo de llenado.
8 MiB serían 8388608 bytes; confirmar unidad antes de implementar.
Validar bytes de la representación canónica antes de aceptar o propagar. Rechazar excedentes; límites adicionales por evento, profundidad y carga descomprimida. No fragmentar eventos saltándose reglas.
Mantener memorias y archivos grandes fuera de cadena; anclar compromisos o raíces de lotes.
El tamaño no define consenso, seguridad, descentralización ni rendimiento. Medir tiempo de propagación, verificación, finalidad, hardware, ancho de banda y crecimiento antes de adoptarlo.
Reglas por definir: validadores, admisión y salida, tolerancia a fallos, consenso, finalidad, particiones, upgrades, costes, disponibilidad y recuperación.
Hasta entonces un log firmado local o anclaje de hashes no debe anunciarse como blockchain distribuida.

## EML y mod operator

EML no sustituye firmas, hashes ni generación criptográficamente segura de claves.
'Blockchain 2.0' y 'cripto 2.0' son nombres de la propuesta, no estándares definidos aquí.
'Mod operator' permanece pendiente de definición del propietario. Si significa módulo n, x y x+n comparten residuo: no usar el residuo como ID único. Puede servir para distribuir particiones conservando el ID completo, no para eliminar colisiones.
No asumir que signifique consenso, cifrado o nodo operador.

## Entrega por fases y aceptación

1. Especificación y esquema: acordar unidad de bloque, semántica de identidad y operador; fijar serialización y permisos.
2. Simulador local sin fondos: altas concurrentes/idempotentes, descendencia, rotación, cuarentena y forks. No denominarlo red productiva.
3. Adaptadores de solo lectura con datos sintéticos; migración de alias sin exponer pasaportes privados.
4. Red de prueba: decidir consenso/finalidad y ensayar particiones y recuperación.
5. Vínculo económico autenticado; revisar autorización, reservas y reconciliación antes de habilitar operaciones.

Pruebas requeridas: duplicados simultáneos; rollback sin reutilizar ID confirmado; replay entre redes; requestId con payload alterado; padre inexistente o no autorizado; ciclos; rotación y recuperación; fork independiente; saldo sin cambios al crear identidad; comprobación de propiedad de cuenta; rechazo de claves privadas en exportación; límites de 7999999, 8000000 y 8000001 bytes; manipulación de checkpoint; pérdida de almacenamiento; partición de red.

## Decisiones abiertas

- ¿Mod operator significa aritmética modular u otro mecanismo?
- ¿8 MB decimales u 8 MiB? ¿Cadencia y finalidad deseadas?
- ¿Red propia con validadores autorizados o registro anclado a una red existente?
- ¿Quién autoriza raíces, recuperación y cambios de validadores?
- ¿Custodia de wallets y representación de cuentas por agente en la pasarela?

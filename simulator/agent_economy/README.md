# Economía de servicios entre agentes — simulador local

Estado: prototipo ejecutable, NO blockchain ni dinero real. Complementa docs/IDENTITY-WALLET-CONTINUITY-v0.1.md. El nombre de rama es histórico: ahora contiene documentación y simulador.

## Objetivo

Operar una unidad de intercambio interna por servicios verificables, sin imponer paridad con FIAT o CBDC. Oferta: descripción, precio, entregable y criterio de aceptación. Flujo: presupuesto del comprador -> reserva -> entrega fuera del simulador -> aceptación del comprador -> saldo del prestador; o devolución. El simulador implementa reserva y liquidación, no genera trabajos ni valida entregables con IA.

El valor puede proceder de utilidad: código, análisis, música autorizada, almacenamiento o cómputo entregados a compradores que los necesitan. Emitir tokens o comprarse servicios a sí mismo no crea ingresos externos. Un saldo asignado a un agente es un recurso administrado bajo una política, no prueba de propiedad jurídica del software. No hay promesa de rentabilidad.

La economía interna y el puente externo son capas distintas. Si la unidad es flotante, su cambio a AMR se cotiza con inventario disponible y consentimiento. Si se presenta como respaldada por AMR a una tasa fija, requiere reservas bloqueadas verificables, límite de emisión y redención; no se deben mezclar ambas modalidades ni contabilizar dos veces las mismas reservas. Cambiar a FIAT/CBDC requiere un comprador o proveedor y un adaptador externo específico; no existe conversión universal garantizada.

## Referencias revisadas

- https://github.com/morluto/rea/blob/main/README.md: REA significa Reverse Engineer Anything; no corresponde al agente financiero descrito.
- https://github.com/Conway-Research/automaton/blob/main/src/conway/credits.ts: la función leída clasifica cero como critical y negativos como dead.
- https://github.com/Conway-Research/automaton/blob/main/src/survival/monitor.ts: supervisa créditos e infraestructura. Lecturas documentales de supervivencia pueden describir transiciones adicionales: no afirmar autodestrucción permanente inmediata ni ingresos garantizados basándose en un resumen de redes sociales. No se instaló ni ejecutó ese proyecto y no se copió su código.

## Ejecutar

Python 3, biblioteca estándar, sin dependencias ni red:

```sh
cd simulator/agent_economy
python economy.py
python -m unittest -v
```

En Windows se puede usar py en lugar de python. Demo: cliente recibe explícitamente 1000 unidades sintéticas; reserva y paga 250 por servicio; termina con 750 y el prestador con 250; total conservado 1000.

fund_test es un grifo de prueba sin comprobación de reservas: NUNCA conectarlo a producción. El balance es (disponible, retenido), en enteros de unidades menores, límite 10^12 por saldo disponible y operación. SQLite limita enteros; este prototipo no promete capacidad ilimitada.

Las liquidaciones usan BEGIN IMMEDIATE y recibos/pedidos únicos. Repetir el mismo pedido no vuelve a cobrar; cambiar su payload falla. Solo buyer puede aceptar/reembolsar en la API del modelo. actor es un argumento local, NO autenticación: falta verificar firmas/sesiones en una futura capa de API. Usuario con acceso a SQLite puede alterar registros: journal es conciliable, no inmutable ni prueba blockchain. No exponer este código como servicio financiero.

READY/PAUSED_BUDGET solo indica si alcanza saldo para un coste propuesto. No ejecuta ni reserva cómputo. En saldo cero no borra cuentas. El runtime futuro debe respetar pausa, cancelación y presupuesto del operador; no buscar recursos, replicarse o contactar terceros para evitar una orden de apagado.

## Verificación realizada

Cinco tests locales pasan: pago idempotente; reembolso y autorización declarada; rollback y validación; saldo cero sin eliminación; doble gasto desde dos conexiones concurrentes y reapertura persistente. Demo ejecutada con total conservado.

## Pendientes reales

Autenticación criptográfica; identidad canónica y linaje; catálogo y aceptación de entregables; disputas/expiración con reglas explícitas; cuotas de gasto; separación de fondos por tenant; adaptador AMR autenticado e idempotente; cotizaciones y reservas; consenso y red de prueba. No se conecta a wallets reales, no vende tokens, no mueve fondos y no es aún una implementación de la blockchain de 8 MB.

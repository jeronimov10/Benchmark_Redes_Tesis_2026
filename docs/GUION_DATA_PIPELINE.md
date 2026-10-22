# Guion de exposición: el pipeline de datos (≈ 10 minutos)

Texto para decir en voz alta, apoyado en [DATA_PIPELINE.md](DATA_PIPELINE.md). Los tiempos entre paréntesis son orientativos.

---

## 1. Apertura (1 min)

Buenos días. Voy a explicarles cómo la aplicación consigue los datos que alimentan el modelo de la tesis, cada cuánto los consigue y qué pasa con ellos hasta que se convierten en una recomendación.

Primero, qué hace la aplicación: no ejecuta pagos. Solo recomienda en cuál de seis redes conviene liquidar un pago en pesos colombianos. Las seis redes son Polygon, Celo, Arbitrum, Tempo, Aptos y Canton.

Para recomendar, el modelo necesita un perfil de catorce métricas por cada red: costo, velocidad, robustez y funcionalidad. Ese perfil tiene dos fuentes. Una es la línea base, que son mediciones largas hechas con anterioridad. La otra es el monitoreo en vivo, que consulta las redes todo el tiempo. Si el dato en vivo es bueno, reemplaza a la base. Si no, se usa la base y la aplicación avisa de dónde salió cada número.

Una aclaración importante desde ya: cuando digo "casi tiempo real" me refiero a sondeo periódico. Ninguna red nos empuja información. Somos nosotros quienes preguntamos cada cierto tiempo.

## 2. De dónde sale el dato (1 min 30 s)

La regla de oro de este proyecto es que ninguna métrica se puntúa si no se puede derivar de una consulta reproducible al registro público de la red. Nunca usamos documentación, blogs ni declaraciones de los equipos. Un dato que no se puede calcular se muestra como no computable, con su razón, y eso es un resultado válido. Un número adivinado sería peor que no tener número.

En la práctica, cada red tiene su puerta de entrada. Polygon, Celo, Arbitrum y Tempo se consultan por JSON-RPC. Aptos, por su API REST. Canton, por su Scan API. Para convertir los costos a dólares leemos los precios directamente de la cadena: Chainlink en las redes EVM y Pyth en Aptos. Y cada dirección o identificador que usamos se verifica en vivo antes de confiar en él. Por ejemplo, el contrato de USDC debe responder que se llama USDC y que tiene seis decimales, y cada feed de precio debe describir exactamente el par que esperamos.

## 3. Cada cuánto se consulta (2 min)

Hay un programador interno que lanza varias tareas independientes.

La más frecuente por volumen es la de bloques: cada veinte segundos, para cada red, trae los bloques nuevos con sus transacciones y recibos. Para no ahogarnos, hay un tope: hasta cuarenta bloques por ciclo en las redes EVM y en Tempo, seis en Aptos, y hasta diez páginas de eventos en Canton. Si nos atrasamos, tomamos los más recientes y registramos los que saltamos. Y las redes arrancan escalonadas, para no golpear a todos los servidores a la vez.

La segunda tarea es la de estado, cada cinco minutos. Lee cosas que cambian despacio: quiénes son los validadores, la configuración del protocolo, el calendario de actualizaciones, el precio de APT.

La tercera es especial y solo existe para Tempo: cada tres décimas de segundo pregunta cuál es el último bloque finalizado. Es la única medición verdaderamente continua.

Luego, cada treinta segundos, otra tarea recalcula todas las métricas a partir de lo que ya está guardado. Y cada hora, una tarea de limpieza borra lo que ya salió de las ventanas de tiempo, para que la base de datos no crezca sin límite.

Con esos números, el retardo máximo entre que algo ocurre en una red y se ve en pantalla es de alrededor de un minuto cuando se trata de bloques: veinte segundos del colector, treinta del cálculo y quince de la interfaz. Para los datos de estado puede llegar a unos seis minutos. Aclaro que es un cálculo a partir de los intervalos, no una medición.

## 4. Qué es tiempo real y qué no (1 min 30 s)

Esta es la pregunta que más se hace, así que la respondo en cuatro niveles.

Primero, lo realmente continuo: la finalidad de Tempo. Se necesita estar mirando en el momento exacto, porque la red no deja un registro posterior de cuándo se finalizó un bloque. En Aptos eso no se puede hacer por HTTP, porque sus bloques duran unos veinte milisegundos, menos que el viaje de ida y vuelta a la API.

Segundo, lo casi en tiempo real: costos, latencias, tasa de fallos y las funcionalidades de pago. Se leen cada veinte segundos y se calculan sobre ventanas móviles: quince minutos para la latencia entre bloques, veinticuatro horas para la mayoría, setenta y dos horas para la finalidad de Tempo y catorce días para continuidad y cambios.

Tercero, las lecturas de estado cada cinco minutos: validadores, configuración y precio de APT.

Y cuarto, lo que solo existe en la línea base, porque no se puede reproducir desde el registro público. Por ejemplo, en Polygon, Celo y Arbitrum, la finalidad depende de seguir el anclaje a Ethereum, y ese rastreador todavía no está construido. En Aptos, la referencia de conciliación no tiene una definición fijada. Y en Canton, la independencia del token nativo no aplica por arquitectura. En cada caso, la aplicación muestra la razón exacta.

## 5. Qué pasa con el dato una vez recogido (2 min)

Cuando un colector recibe la respuesta de la red, lo primero es que la petición ya viene protegida: tiene límite de tiempo, hasta cuatro reintentos con espera creciente y aleatoria, y respeta las pausas que pida el servidor.

Luego el dato crudo pasa por un procesador, que es una función pura: toma la respuesta de la red y la convierte en una muestra normalizada, con tiempos en segundos, costos en dólares y fracciones entre cero y uno. Si no hay precio disponible, el costo queda vacío; nunca se inventa.

La muestra se guarda en SQLite. Las inserciones ignoran duplicados, así que leer dos veces lo mismo no altera nada. Y si algún componente falla, queda registrado cuándo fue su último éxito, su último error y cuántos fallos van seguidos. Tras un fallo, ese componente espera más antes de reintentar, hasta ocho veces su intervalo normal. En pantalla, una red aparece como correcta, degradada si falla algo secundario, o caída si fallan los bloques.

Cada treinta segundos se calculan las métricas. Cada una sale con su valor, su incertidumbre estimada por remuestreo, cuántas muestras la respaldan, su ventana y su estado. Los estados posibles son: válida, insuficiente, obsoleta, fallida o no computable. Solo una métrica válida y fresca puede entrar al perfil.

Hay un detalle clave: tres métricas exigen que la ventana se haya cubierto completa. La finalidad de Tempo necesita setenta y dos horas observadas; la continuidad y los cambios necesitan catorce días. Mientras tanto, sigue vigente la línea base. Preferimos eso a publicar una cifra parcial que subestime.

## 6. Línea base más vivo (1 min)

Ahora viene la mezcla. Para cada red y cada métrica partimos de la línea base. Si existe una medición en vivo, es válida y es reciente, la reemplazamos. Reciente significa quince minutos, o dos horas para las lecturas de estado. Si no, nos quedamos con la base.

Cada número conserva su procedencia: si es base o vivo, de qué fuente, con cuántas muestras, sobre qué ventana y qué tan viejo es. Además hay un modo de medición que usa solo la base, y sirve para reproducir exactamente los casos de referencia de la tesis.

## 7. Del perfil a la recomendación (1 min)

Con el perfil armado, el usuario indica el monto, si es transfronterizo, cuánto puede esperar y qué tan irrevocable debe ser el pago. El modelo, que no hemos modificado, interpreta ese caso como una mezcla de tres escenarios de referencia: remesas, comercio y alto valor.

Primero aplica compuertas, que descartan redes con motivo explícito: por ejemplo, una latencia mayor a veinte segundos en comercio, o la ausencia de finalidad anclada. Luego puntúa las métricas que sí tienen dato, y después corre diez mil réplicas de Monte Carlo para ver si la diferencia entre redes es real o es ruido. La recomendación es la primera banda: las redes que no se pueden distinguir entre sí quedan empatadas.

Si hay menos de dos redes con datos, la aplicación responde que los datos son insuficientes, en vez de forzar una respuesta. El modelo corre en un proceso aparte para no frenar la recolección, y si nada cambió en el perfil, la respuesta sale de caché en menos de un segundo.

## 8. La matriz, dicha en palabras (1 min 30 s)

Para cerrar con el panorama por red.

Tempo es la más completa: las catorce métricas se miden en vivo. Costos, latencia y funcionalidades cada veinte segundos; la concentración sale de los validadores activos cada cinco minutos; los cambios, del calendario de actualizaciones; y la finalidad, del sondeo continuo, aunque esa necesita setenta y dos horas para ser válida.

Aptos tiene diez métricas en vivo. Quedan en la base la finalidad, la continuidad, los cambios y la referencia de conciliación. Y su costo depende del precio de APT, que hoy está congelado en la cadena; la aplicación lo marca como tal.

Canton tiene trece en vivo, y su fuente es el flujo de eventos con un cursor que sobrevive a reinicios. Su latencia sale de la diferencia entre el momento de registro y el de finalización de cada veredicto. Su capacidad es una cota inferior, porque usamos la asignación gratuita por miembro y no el techo agregado de la red. Por eso nunca debemos decir que Canton no sostiene cierto caudal sin mencionar esa advertencia.

Polygon, Celo y Arbitrum tienen nueve métricas en vivo, calculadas solo sobre transferencias de USDC. Las demás permanecen en la base, cada una con su razón.

Y un recordatorio sobre el tiempo: lo de estado entra tras la primera lectura; lo de costos y latencias, cuando se junta el mínimo de muestras, que depende del tráfico de cada red; la finalidad de Tempo, a las setenta y dos horas; y continuidad y cambios, a los catorce días de operación continua.

## 9. Limitaciones y cierre (1 min)

Sean claros en tres limitaciones. Primera: es sondeo, no flujo continuo, con un retardo de hasta un minuto aproximadamente. Segunda: en redes muy rápidas, como Aptos, lo que recogemos es una muestra de bloques y no un censo. Tercera: algunas métricas necesitan días de operación ininterrumpida antes de ser vivas, y los nodos públicos de consulta pueden fallar, aunque para eso tenemos reintentos y estado de salud visible.

Para resumir: consultamos seis redes cada veinte segundos, leemos lo lento cada cinco minutos y la finalidad de Tempo cada tres décimas de segundo. Cada treinta segundos convertimos todo en métricas validadas. Solo lo válido y reciente reemplaza a la línea base, y cada número conserva su origen. Con ese perfil, el modelo decide en qué red conviene liquidar, y cuando no hay datos suficientes, lo dice en lugar de inventar.

Muchas gracias. Quedo atento a sus preguntas.

---
---

# Parte 2. Guion de la animación, red por red

Texto para decir mientras se muestra [animacion_pipeline.html](animacion_pipeline.html). Se elige una red en las pestañas y se recorre la animación de izquierda a derecha. Los tiempos hasta la pantalla (≈ 65 s para bloques, ≈ 345 s para estado, ≈ 45 s para la finalidad de Tempo) son cálculos a partir de los intervalos, no mediciones.

## Cómo leer la animación (1 min)

La animación se lee de izquierda a derecha. A la izquierda está el bloque de métricas: A es costo, B es tiempo y caudal, C es concentración y continuidad, y D son las primitivas de pago en uso. Son los cuatro bloques del modelo. El benchmark por lotes tiene además una métrica E1, pero no entra al perfil del modelo, y en la interfaz E1, E2 y E3 son los escenarios de referencia; por eso aquí no hay una fila E.

Cada fila es una ruta por la que llega información a un bloque. Primero está la fuente, que es la red a la que le preguntamos y a la que solo le hacemos lecturas. Después, la llamada exacta, con el método o el endpoint, y arriba a la derecha la etiqueta de cada cuánto se hace. Luego, qué se extrae de la respuesta. Después, la tabla de SQLite donde se guarda. Y al final, las métricas que se alimentan de esa ruta: las que tienen borde continuo se miden en vivo y las de borde punteado existen solo en la línea base.

Los puntos que viajan son ciclos reales. El primero recorre la ruta cuando toca la llamada, y cada treinta segundos sale otro desde la tabla hacia las métricas. Ese punto baja por el borde derecho y recorre las tres cajas de abajo: las métricas calculadas se guardan en la base de datos, el backend las lee y arma el perfil efectivo y la recomendación con el modelo, y el frontend las consulta cada quince segundos para mostrarlas en pantalla. Cuando llega a una métrica, su fila de la tabla de abajo se ilumina, y en esa tabla está, para cada métrica, de dónde sale exactamente y con qué periodicidad.

## Polygon, Celo y Arbitrum (3 min)

Las tres son redes EVM y se leen igual; cambia el servidor y el precio. Polygon se consulta en polygon.publicnode.com, Celo en forno.celo.org y Arbitrum en arb1.arbitrum.io. Antes de medir, el colector verifica que el contrato de USDC se llame USDC y tenga seis decimales.

**Bloque A, costo.** Cada veinte segundos pedimos con eth_getLogs todos los eventos Transfer del USDC, y de las transacciones que los emiten pedimos el recibo en lotes de veinticinco. Del recibo sacamos el gas usado, el precio efectivo y, en Arbitrum, la tarifa de la capa uno. Esa cifra se multiplica por el precio del token nativo, que leemos de un feed de Chainlink en la propia red: MATIC contra dólar en Polygon, CELO contra dólar en Celo, ETH contra dólar en Arbitrum. El feed se verifica con su descripción y se rechaza si tiene más de una hora. De ahí salen A1, la mediana del costo, y A2, el percentil 95 dividido por la mediana, sobre una ventana de veinticuatro horas. A3 y A4 existen solo en la línea base: la regresión no es concluyente y el anclaje a Ethereum no tiene rastreador.

**Bloque B, tiempo y caudal.** Cada veinte segundos pedimos el número del último bloque y los bloques nuevos en lotes de diez. Con el timestamp de cada bloque calculamos la diferencia con el anterior, solo entre consecutivos: eso es B1, el percentil 95 sobre quince minutos. B2, B2b y B3 están solo en la línea base: la finalidad depende del anclaje en Ethereum y la capacidad es un caudal sostenido de una hora sobre noventa días.

**Bloque C, concentración y continuidad.** De cada bloque tomamos el campo miner. Con el conteo por productor en veinticuatro horas calculamos C1, el índice de concentración, y C2, cuántos productores hacen falta para superar la mitad. Es una muestra de bloques, no un censo. Con el número y el timestamp de cada bloque se resume cada ciclo para C3, la continuidad, sobre catorce días; si el sondeo salta demasiados bloques, como probablemente pasa en Arbitrum, no es computable. C4 sale del campo status de los recibos. Y hay una segunda ruta, de estado, cada trescientos segundos: leemos con eth_getStorageAt la ranura donde el proxy del USDC guarda su implementación, y los cambios entre lecturas alimentan C5 sobre catorce días.

**Bloque D, primitivas de pago.** Del recibo y de la transacción miramos si es del tipo cuatro, de delegación, si va a un EntryPoint de cuenta abstracta, si usa la firma de autorización de EIP-3009 o si paga con feeCurrency. Eso es D1, el patrocinio. D2 y D3 solo están en la línea base.

**Cuánto tarda.** Las métricas de bloques y recibos se leen cada veinte segundos y pasan a válidas al juntar el mínimo de muestras: treinta para costos, B1 y D1, cien para C1 y C2, cincuenta para C4. Eso depende del tráfico de pagos de la red. C3 y C5 necesitan catorce días continuos. Un cambio real tarda unos sesenta y cinco segundos en llegar a pantalla, y uno de estado, unos cinco minutos y medio.

## Tempo (3 min)

Se consulta por JSON-RPC en rpc.tempo.xyz. Es la única red de la que medimos las catorce métricas en vivo.

**Bloque A.** Cada veinte segundos traemos los bloques nuevos en lotes de veinticinco y el recibo de todas las transacciones, porque en Tempo todo es pago. El costo es el gas usado por el precio efectivo, dividido por diez a la dieciocho, solo si el token de comisión se verificó con su función decimals; como es un token en dólares, el precio es uno. De ahí salen A1 y A2. A3 es la pendiente entre el costo y la ocupación del bloque, que es el gas usado sobre el límite de gas.

**Bloque B.** B1 sale del timestamp del bloque más sus milisegundos, entre consecutivos, sobre quince minutos. B3 sale del límite de gas del bloque, el gas mediano por transacción y la cadencia entre bloques, y se divide entre dieciocho transacciones por segundo. Y B2 tiene su propia ruta, la más rápida de todo el sistema: cada tres décimas de segundo preguntamos por el bloque finalizado. Cuando su número cambia, guardamos el timestamp del bloque como tau uno, la hora a la que lo vimos como tau F, y la diferencia. B2 es la mediana de setenta y dos horas y solo es válida cuando se cubrió esa ventana. Es la única medición de tiempo real del sistema, porque la red no deja registro posterior de cuándo se finalizó un bloque.

**Bloque C.** C3 y C4 salen de los bloques y los recibos: continuidad sobre catorce días y fracción de transacciones fallidas. C1, C2 y C5 salen de la ruta de estado, cada trescientos segundos: llamamos getActiveValidators al precompilado que está en la dirección 0xCCCCCCCC…0001, cuya dirección se ubicó en el código fuente público y se verificó con una consulta en vivo. Como la interfaz no expone pesos, se asume voto igualitario. Y tempo_forkSchedule devuelve el calendario de actualizaciones con su fecha de activación, que usamos para C5. Esas tres son válidas desde la primera lectura.

**Bloque D.** Del recibo sacamos tres cosas: el feePayer, que indica si otro pagó la comisión; el evento TransferWithMemo, cuyo topic calculamos con keccak, para D2; y si hubo más de un evento Transfer, para D3.

**Cuánto tarda.** Los de bloques y recibos, cada veinte segundos y con su mínimo de muestras; la finalidad, cada tres décimas de segundo pero válida a las setenta y dos horas, con un retardo a pantalla de unos cuarenta y cinco segundos; validadores y forks, cada cinco minutos; continuidad, catorce días.

## Aptos (3 min)

Se consulta por REST en api.mainnet.aptoslabs.com. Sus bloques duran unos veinte milisegundos, así que no podemos leerlos todos.

**Bloque A.** Cada veinte segundos preguntamos la altura y pedimos los seis bloques más recientes con sus transacciones, en paralelo, con blocks by_height. El costo es el gas usado por el precio de la unidad de gas, dividido por cien millones, por el precio de APT. Ese precio no viene de un servicio externo: lo leemos de la tabla de Pyth en la propia cadena, y hoy está congelado, lo que la nota de la métrica indica. De ahí salen A1, A2 y A3; esta última usa la ocupación, el gas del bloque sobre el límite de la configuración de ejecución.

**Bloque B.** B1 sale del block_timestamp de alturas consecutivas dentro de lo muestreado. B3 usa otra ruta, de estado, cada trescientos segundos: leemos el recurso ExecutionConfig de la cuenta 0x1, un blob BCS que decodificamos exigiendo consumir todos los bytes, y de ahí sale el límite efectivo de gas del bloque. Con el gas mediano por transacción y la cadencia se calcula la capacidad. B2 está solo en la línea base porque un bloque dura menos que una petición HTTP.

**Bloque C.** C4 sale del campo success de cada transacción. C1 y C2 salen del recurso ValidatorSet, también de la cuenta 0x1, con el voting power de cada validador, cada trescientos segundos. C3 y C5 están solo en la línea base: con seis bloques por ciclo no cubrimos los pares consecutivos para detectar huecos, y la definición de cambios del benchmark no mide la mutabilidad de la ruta de pago.

**Bloque D.** D1 es si la firma de la transacción es de tipo fee payer. D3 sale de los eventos Deposit y Withdraw de Fungible Asset, donde cada evento trae un store que resolvemos a su activo real; con la muestra reducida el n es pequeño. D2 está solo en la línea base porque la definición de referencia apta no está fijada.

**Cuánto tarda.** Bloques y transacciones, cada veinte segundos; configuración, validadores y precio, cada cinco minutos. Diez de las catorce métricas son vivas y cuatro quedan en la base.

## Canton (3 min)

Se consulta la Scan API en api.cantonnodes.com. Canton no tiene bloques: tiene un flujo de eventos, y por eso casi todas las rutas de las filas salen del mismo lugar.

**Cómo se leen los eventos.** Cada veinte segundos hacemos POST a v0 events con un cursor, en páginas de doscientos y hasta diez páginas por ciclo. El cursor se guarda en SQLite, de modo que si el sistema se reinicia, retoma donde quedó. Para acotar el volumen guardamos uno de cada cuatro veredictos; las transferencias y los latidos se leen completos.

**Bloque A.** Cada veredicto trae el costo de tráfico en bytes. El costo en dólares es bytes dividido por un millón por el precio del tráfico extra por megabyte, que leemos del estado del DSO. De ahí A1 y A2. A3 agrupa el costo en cubetas de diez segundos y ajusta su relación con el tráfico total.

**Bloque B.** B1 y B2 salen de la misma resta: finalization_time menos record_time del veredicto. B1 es el percentil 95 y B2 la mediana, sobre veinticuatro horas. No hace falta una ruta aparte de finalidad porque la finalización viene dentro de cada veredicto. B3 sale de la ruta de estado: GET v0 dso, con los límites base de tráfico, que dividimos entre los bytes medianos por transferencia.

**Bloque C.** C4 es la fracción de veredictos con resultado rechazado. C3 usa los latidos de ValidatorLicense ReportActive como puntos de continuidad, sobre catorce días. C5 cuenta las choices DsoRules que no son rutinarias, también sobre catorce días. C1 y C2 salen del estado del DSO, cada trescientos segundos, con el peso de recompensa de cada Super Validator.

**Bloque D.** D2 es la fracción de transferencias con meta, y D3, la fracción con más de una salida. D1 está solo en la línea base porque el sujeto declarado no aplica por la arquitectura de Canton.

**Cuánto tarda.** Eventos, cada veinte segundos; estado del DSO, cada cinco minutos; continuidad y cambios, catorce días. Trece de las catorce métricas son vivas.

## Cierre de la animación (30 s)

Lo que quiero que se lleven de la animación es esto: todas las rutas empiezan en una consulta pública a la red, pasan por una extracción sencilla, se guardan en una tabla y alimentan métricas de uno de los cuatro bloques. Lo único que cambia entre redes es la llamada exacta y cada cuánto se hace. Y lo que no se puede reproducir desde el registro público, no se inventa: queda en la línea base, con su borde punteado.

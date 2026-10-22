# Guion de exposición: el pipeline de datos (≈ 10 minutos)

Texto para decir en voz alta, apoyado en [DATA_PIPELINE.md](DATA_PIPELINE.md). Los tiempos entre paréntesis son orientativos.

---

## 1. Apertura (1 min)

Buenos días. Voy a explicarles cómo la aplicación consigue los datos que alimentan el modelo de la tesis, cada cuánto los consigue y qué pasa con ellos hasta que se convierten en una recomendación.

Primero, qué hace la aplicación: no ejecuta pagos. Solo recomienda en cuál de seis redes conviene liquidar un pago en pesos colombianos. Las seis redes son Polygon, Celo y Arbitrum, que trabaja Dilan, y Tempo, Aptos y Canton, que trabajo yo.

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

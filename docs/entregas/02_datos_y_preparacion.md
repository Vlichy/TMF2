# Entrega 02 · Datos y preparación

## 1. Qué datos necesita el producto

El equipo de reservas revisaría cada mañana las llegadas previstas para dos días después. En producción, el corte sería a las 09:00 en la zona horaria del hotel, dos días naturales antes de la fecha de llegada. Se incluirían solamente reservas activas según el sistema del hotel a esa hora. Cada fila operativa representaría una reserva elegible en ese corte. Harían falta un ID estable, el historial de estados con marcas de tiempo y los valores de los campos tal como constaban al corte. Se conservaría al menos un ciclo anual para cubrir la estacionalidad.

Con un cupo diario de K contactos por hotel, se compararía el ranking del modelo con una regla sencilla que priorice las reservas de mayor antelación, con desempate estable por ID. Ambos rankings usarían el mismo conjunto elegible y seleccionarían hasta K reservas. Se contaría cuántas cancelaciones avisadas posteriores al corte identifica cada método dentro de ese cupo. La comparación serviría para evaluar la priorización. Para medir si contactar evita cancelaciones haría falta un piloto.

## 2. Fuentes reales y viabilidad

La referencia es [Hotel booking demand datasets, de Antonio, de Almeida y Nunes](https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/), DOI 10.1016/j.dib.2018.11.126. Los suplementos del artículo contienen las extracciones de un hotel vacacional y uno urbano en Portugal, con llegadas previstas entre julio de 2015 y agosto de 2017. Es una publicación estática: sirve para un prototipo reproducible y no ofrece reservas recientes.

Para reproducir esta entrega se usa la copia consolidada ya disponible en [CSV de referencia](https://raw.githubusercontent.com/Vlichy/proyecto_machineLearning/c10a6dfaf05b9a9c1466d83c2d8e895816fe7209/data/raw/hotel_bookings.csv), con 119.390 filas y 32 columnas. La huella esperada está en [el inventario de inspección](../../reports/inspeccion_dataset.json). Los dos ficheros del artículo son una referencia alternativa; si se usan para reconstruir el insumo, hay que armonizar nombres, añadir el tipo de hotel y verificar el esquema y los recuentos. No se presupone que generen un CSV idéntico. Para actualizar el producto haría falta una exportación autorizada del sistema de reservas del hotel.

## 3. Uso, privacidad y datos personales

El artículo se publica bajo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) y se atribuye aquí a sus autores. Antes de redistribuir una copia de terceros, comprobaríamos sus condiciones concretas. Los autores retiraron los datos que identificaban a clientes y hoteles. Para un piloto no necesitamos nombres, contactos ni datos de pago. Si hace falta unir la versión inicial de una reserva con su resultado, basta un identificador interno seudonimizado, separado de las variables del modelo y con acceso restringido.

## 4. Del dato bruto al dato utilizable

| Capa | Qué contiene y cómo se obtiene |
| --- | --- |
| Bronze / Raw | CSV local de origen, conservado sin cambios. Se comprueba su SHA-256 antes de preparar los datos. |
| Silver | [Limpieza en memoria](../../src/cleaning.py): se normalizan tipos, se mantienen nulos de país y número de niños y se señalan anomalías. Se conservan las filas repetidas porque sin un ID de reserva no se puede distinguir una duplicación técnica de dos reservas iguales. No se necesitan cruces entre tablas. |
| Gold histórico · reservas_historicas | CSV preparado en data/processed/hotel_bookings_prepared.csv: 119.390 filas, 14 variables candidatas, la etiqueta `is_canceled` (1 = cancelación o no presentación) y metadatos separados para auditoría. |

Las seis variables numéricas son `lead_time`, `total_nights`, `adults`, `children`, `babies` y `children_missing`. El total de noches suma las de semana y fin de semana; el indicador permite distinguir un número de niños desconocido de un cero. Las ocho categóricas son `hotel`, `arrival_date_month`, `meal`, `country`, `market_segment`, `distribution_channel`, `reserved_room_type` y `customer_type`.

Se excluyen de los predictores la etiqueta, los metadatos y los campos que revelan el resultado, como `reservation_status` y `reservation_status_date`. También se excluyen campos cuya versión inicial es incierta, como el número de cambios de la reserva. La imputación y la codificación se dejan para la siguiente fase y se ajustarán solo con entrenamiento.

Desde la raíz, con Python 3.14.5 y las [dependencias del proyecto](../../requirements.txt), ejecutar:

```powershell
New-Item -ItemType Directory -Force data/raw | Out-Null
Invoke-WebRequest https://raw.githubusercontent.com/Vlichy/proyecto_machineLearning/c10a6dfaf05b9a9c1466d83c2d8e895816fe7209/data/raw/hotel_bookings.csv -OutFile data/raw/hotel_bookings.csv
python -m src.preparation
```

El [script](../../src/preparation.py) verifica la entrada y regenera el CSV preparado y sus informes locales. El [notebook de preparación](../../notebooks/preparacion.ipynb) explica el flujo paso a paso. Esta entrega aporta referencias a los datos existentes sin añadir otra copia de los CSV.

La [muestra del Gold histórico](muestra_gold_historico.csv) contiene diez filas, cinco por clase de la etiqueta original, para inspeccionar el esquema. El muestreo usa semilla 42. La muestra no estima prevalencias.

En el archivo histórico, `is_canceled=1` reúne 43.017 casos con estado final `Canceled` y 1.207 `No-Show`. Las 75.166 filas `Check-Out` tienen etiqueta 0. Para el producto, sería positivo un aviso de cancelación registrado después del corte y antes de la llegada prevista en una reserva activa al corte. Una reserva ya cancelada al corte queda fuera del cupo. Una no presentación se registra por separado y cuenta como 0 para el objetivo de aviso. La fecha del último estado del CSV no acredita la hora del aviso ni la secuencia de estados.

Al separar entrenamiento, validación y prueba por fechas de corte, se mantendrán juntas todas las filas de cada `meta_duplicate_group`. Si un grupo abarca más de un periodo, se apartará completo de la evaluación y se registrará cuántas filas se excluyen. Se comprobará que los grupos de las tres particiones sean disjuntos y que las etiquetas de entrenamiento ya hubieran cerrado antes del siguiente periodo.


### Tablas y alcance de las comprobaciones

**`reservas_historicas`** es el nombre de la tabla disponible, generada en `data/processed/hotel_bookings_prepared.csv`. Cada fila corresponde a un registro del CSV histórico. Su muestra es `muestra_gold_historico.csv`. Permite comprobar la huella del origen, la conservación de filas, tipos y nulos, las transformaciones, las marcas de calidad, los grupos de duplicados y la separación de variables candidatas, etiqueta y metadatos. También permite describir las asociaciones con el resultado final histórico. La disponibilidad de sus campos a las nueve y la elegibilidad para recibir una llamada quedan pendientes de acreditar.

**`reservas_activas_corte_09h`** es el nombre de la tabla operativa pendiente de construir con el historial del hotel. Cada fila representará una reserva activa a las 09:00 locales, dos días naturales antes de su llegada prevista según la información disponible al corte. Su clave será el par `reserva_id`, `corte_at`.

| Campos de la tabla operativa | Significado y procedencia |
| --- | --- |
| `reserva_id`, `hotel_id`, `corte_at` | Identificador seudonimizado, hotel y corte con zona horaria. |
| `llegada_prevista_at_corte`, `estado_at_corte` | Llegada prevista y estado reconstruidos con los eventos anteriores o iguales al corte. La población incluye las reservas activas con llegada dos días después. |
| Variables disponibles al corte y sus marcas de actualización | Última versión conocida a esa hora de cada predictor, trazable al historial del sistema. |
| `aviso_cancelacion_at`, `no_show`, `seguimiento_hasta` | Resultado posterior obtenido del historial y fecha hasta la que se verificó su cierre. Se incorporan al evaluar. |
| `y_aviso_post_corte` | Vale 1 si hubo aviso después del corte y antes de la llegada prevista al corte. Vale 0 si el seguimiento completo acredita que no hubo ese aviso. Queda desconocida mientras falte seguimiento. |

Con ese historial quedarán por comprobar la reconstrucción de la población activa, la disponibilidad temporal de cada predictor, la separación entre avisos y no presentaciones y la madurez de las etiquetas. Una vez verificadas, se podrá comparar cuántas cancelaciones avisadas identifica el modelo frente a la regla de mayor antelación con el mismo cupo diario por hotel. La medición del efecto de las llamadas requerirá un piloto con resultados de los contactos.

## 5. Riesgos y limitaciones

- Faltan capturas a la hora de corte, historial de estados e ID estable. El Gold publicado describe el histórico y solo permite verificar el flujo técnico.
- Dos hoteles portugueses y llegadas hasta agosto de 2017 limitan la representatividad para un piloto actual.
- Si falla el enlace al CSV, se usarán los suplementos originales y se volverán a comprobar cobertura, esquema y recuentos.

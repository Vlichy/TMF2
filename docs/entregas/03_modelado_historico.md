# Modelado de reservas históricas

## Objetivo y alcance

Tras el cierre de la preparación por el tutor, se entrena sobre reservas_historicas para ordenar reservas según su resultado final is_canceled. La clase positiva incluye cancelaciones y no presentaciones. La futura tabla reservas_activas_corte_09h permitirá estudiar la revisión diaria y los avisos posteriores al corte.

El [plan previo](03_plan_modelado.md) fija las fechas, los dos modelos, el criterio de selección y el cupo. El histórico completo ya se había explorado en trabajos anteriores. Esta evaluación temporal tiene exposición previa al archivo y describe generalización entre cohortes de llegada del mismo histórico.

## Preparación y particiones

Se conservan las 14 variables de preparación. Imputación, escalado y codificación se aprenden con entrenamiento. Los estados finales y metadatos se usan para auditoría, particiones y etiqueta.

| Bloque | Llegadas retenidas | Filas | Positivos | Prevalencia |
| --- | --- | ---: | ---: | ---: |
| Entrenamiento | Julio 2015 a junio 2016 | 48.428 | 17.340 | 35,81% |
| Validación | Julio a diciembre 2016 | 28.754 | 10.553 | 36,70% |
| Prueba | Enero a agosto 2017 | 40.687 | 15.745 | 38,70% |

Se apartan 1.521 filas de entrenamiento o validación cuya cota de cierre alcanza el periodo siguiente. La cota es el día posterior al máximo entre salida prevista y fecha del último estado. Su disponibilidad real requiere contraste con el hotel. Hay cero grupos de duplicados que atraviesen las particiones. Las repeticiones dentro de cada bloque se conservan. El código comprueba que los grupos sean disjuntos.

## Comparación y selección

Se comparan regresión logística y bosque aleatorio, con parámetros fijados en el plan y semilla 42. La clase positiva representa alrededor del 36% de entrenamiento. Se mantiene la distribución observada y se evalúan Average Precision, precisión y recall para recoger el comportamiento sobre positivos.

| Método | Average Precision en validación | ROC-AUC en validación | Positivos dentro del cupo |
| --- | ---: | ---: | ---: |
| Regresión logística | 0,7249 | 0,7712 | 4.330 |
| Bosque aleatorio | 0,7444 | 0,7879 | 4.432 |
| Regla de mayor antelación | 0,5473 | 0,6764 | 3.217 |

El bosque aleatorio se selecciona por mayor Average Precision en validación. Se evalúa en prueba manteniendo su ajuste sobre entrenamiento.

## Resultados en prueba

Cada método selecciona el 20% de las filas de cada mes y hotel, redondeado hacia abajo. El cupo total es de 8.130 reservas. Los empates se resuelven con SHA-256 de semilla e ID de fila, seguido del ID. La regla ordena por lead_time descendente.

| Métrica | Bosque aleatorio | Regla de mayor antelación |
| --- | ---: | ---: |
| Positivos detectados | 6.249 | 4.177 |
| Precisión en el cupo | 76,86% | 51,38% |
| Recall en el cupo | 39,69% | 26,53% |
| ROC-AUC | 0,7855 | 0,6551 |
| Average Precision | 0,7497 | 0,5093 |

El bosque identifica 2.072 positivos adicionales con el mismo cupo, un aumento relativo del 49,60%. Quedan 1.881 negativos seleccionados y 9.496 positivos fuera del cupo. La población incluye todas las reservas de cada cohorte, incluidas las canceladas antes de la revisión propuesta. Estos recuentos cuantifican la priorización retrospectiva de resultados finales.

La mejora global varía por hotel y mes. En enero de 2017, para Resort Hotel, el bosque identifica 54 positivos y la regla 94, ambos con un cupo de 261. La tabla mensual permite revisar estas diferencias antes de plantear un piloto.

Con umbral fijo 0,5, el bosque obtiene precisión 87,28%, recall 34,39% y F1 0,4933. La matriz de confusión contiene 24.153 verdaderos negativos, 789 falsos positivos, 10.331 falsos negativos y 5.414 verdaderos positivos. El umbral 0,5 produce un número de seleccionados distinto al cupo del 20%.

## Reproducción y evidencia

Desde la raíz, tras descargar el CSV según la Entrega 02 y disponer de las dependencias, ejecutar `python -m src.modeling`. También se puede ejecutar [el notebook](../../notebooks/modelado_historico.ipynb) de principio a fin.

El script verifica las huellas del origen, reproduce el Gold, entrena, selecciona y evalúa. Guarda [métricas y versiones](../../reports/modelo_historico_resultados.json) y [recuentos por mes y hotel](../../reports/modelo_historico_mensual.csv). Las predicciones y particiones completas se generan localmente en data/processed. El notebook incluye curvas ROC y precision-recall y una comparación mensual con salidas guardadas.

## Interpretación y trabajo futuro

El bosque supera a la regla de antelación en estas cohortes históricas. La variación temporal, los duplicados conservados, la exposición previa al archivo y la ausencia de versiones de los campos al corte limitan la extrapolación.

El siguiente paso operativo será construir reservas_activas_corte_09h con historial de estados, definir el cupo diario real y evaluar avisos posteriores al corte. La reducción de cancelaciones atribuible a las llamadas requerirá un piloto que registre intervenciones y resultados. Estas mejoras quedan fuera del alcance histórico aprobado.


# Plan de modelado histórico

El tutor autoriza avanzar con reservas_historicas. La etiqueta is_canceled reúne cancelaciones y no presentaciones. El análisis estima capacidad para ordenar esos resultados finales en cohortes históricas de llegada.

Este plan se escribe antes de ejecutar el nuevo experimento. Se reutilizan las 14 variables de preparación. La imputación, escala y codificación se ajustan exclusivamente con entrenamiento.

- Entrenamiento con llegadas anteriores al 1 de julio de 2016 y cota de cierre de etiqueta anterior a ese día.
- Validación con llegadas entre julio y diciembre de 2016 y cota de cierre anterior al 1 de enero de 2017.
- Prueba con llegadas entre enero y agosto de 2017.
- Cualquier grupo de duplicados que atraviese periodos se apartará completo. Se conservarán juntos los duplicados dentro de cada periodo.
- La cota de cierre es el día posterior al máximo entre salida prevista y último estado. Su disponibilidad operativa queda pendiente de contrastar con el hotel.

Se comparan una regresión logística (C=1, max_iter=2000) y un bosque aleatorio (150 árboles, profundidad máxima 12, mínimo 20 filas por hoja). La semilla es 42. La regla de referencia ordena por antelación descendente. Se elige el modelo de mayor Average Precision en validación, con desempate a favor de la logística. Se conserva su ajuste original sobre entrenamiento para evaluar prueba.

Para comparar rankings se selecciona el 20% de filas de cada mes y hotel, redondeando hacia abajo. Los empates se resuelven por una huella SHA-256 de la fila y la semilla, y después por ID de fila. Modelo y regla reciben exactamente el mismo cupo y población. Se informan positivos detectados, precisión y recall en ese cupo, además de ROC-AUC y Average Precision. Se añaden métricas y matriz de confusión al umbral 0,5.

El 20% es una capacidad ilustrativa fijada antes de ejecutar, pendiente de acordar con un hotel. El lote incluye todas las reservas históricas de cada cohorte. La prueba de reservas activas a las nueve requiere reservas_activas_corte_09h.

Este archivo de datos ya se exploró y se utilizó en trabajos anteriores. La separación temporal aporta una evaluación retrospectiva reproducible, con exposición previa al histórico. Las métricas describen estas cohortes y no acreditan cuántas llamadas funcionarían en producción.

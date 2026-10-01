---
name: metricas
description: Calcula y explica las métricas de software de docker/secrets-engine (complejidad, cobertura, densidad de defectos, MTTD, MTTR, eficacia de pruebas, eficacia de revisión, desviación de esfuerzo, arquitectura) con la CLI metricas.
argument-hint: "[complejidad|cobertura|densidad|mttd|mttr|pruebas|revision|esfuerzo|arquitectura|todo] [--reusar|--rapido|--refrescar]"
allowed-tools: Bash(metricas *) Bash(./tools/metricas/metricas *) Read
---

1. Ejecuta `metricas $ARGUMENTS`. Si no se pasó ningún argumento, ejecuta `metricas todo --rapido`.
   Si `metricas` no existe en el PATH, usa `./tools/metricas/metricas $ARGUMENTS`.
2. Lee el archivo `.md` de cada métrica calculada en `metricas_resultados/<metrica>/`
   (o `metricas_resultados/resumen/resumen.md` si se ejecutó `todo`).
3. Responde en español con:
   - una tabla con: métrica, resultado general y valoración;
   - para cada métrica, en 2-3 frases: qué significa el número y qué implica para el proyecto;
   - la ruta de los gráficos PNG generados, para que el usuario los abra.
4. Usa solo cifras que aparezcan en los archivos generados. Si un comando falla, muestra el
   error y sugiere `metricas doctor`.

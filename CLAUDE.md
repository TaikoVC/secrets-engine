# Métricas de software de docker/secrets-engine (fork de trabajo)

Este repositorio se usa para calcular métricas de producto, proceso y proyecto
con la CLI `metricas` (código en `tools/metricas/`). Responde siempre en español.

## Cómo calcular métricas

Usa SIEMPRE la CLI; no recalcules a mano ni estimes cifras.

| Pedido del usuario | Comando |
|---|---|
| complejidad ciclomática | `metricas complejidad` |
| cobertura de código | `metricas cobertura` (o `--reusar` para no volver a correr go test) |
| densidad de defectos | `metricas densidad` |
| MTTD | `metricas mttd` |
| MTTR | `metricas mttr` |
| eficacia de las pruebas | `metricas pruebas` |
| eficacia de la revisión | `metricas revision` |
| desviación de esfuerzo | `metricas esfuerzo` |
| arquitectura, patrones, frameworks | `metricas arquitectura` |
| todas + resumen | `metricas todo` (o `metricas todo --rapido`) |
| verificar herramientas | `metricas doctor` |

Si `metricas` no está en el PATH, usa `./tools/metricas/metricas`.

## Dónde quedan los resultados

`metricas_resultados/<metrica>/` contiene `<metrica>.json` (todas las cifras),
`<metrica>.md` (resultado general, interpretación y significado) y
`<metrica>.png` (gráfico). El resumen está en `metricas_resultados/resumen/`
(`resumen.md`, `tablero.png`, `arquitectura_metricas.png`, `ciclo_vida_metricas.png`).

## Reglas al explicar resultados

- Cita las cifras exactamente como aparecen en el JSON/MD generado.
- Para cada métrica: resultado general, interpretación y qué significa para el proyecto.
- No inventes umbrales: usa el campo `referencia` del JSON.
- La minería de defectos se guarda en caché por commit; si el usuario cambió de rama
  o hizo commits nuevos, la CLI la recalcula sola. `--refrescar` la fuerza.
- No hagas commits con prefijo `fix:` en este fork: alterarían el conteo de defectos.

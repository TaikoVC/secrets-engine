# `metricas` — CLI de métricas de software para docker/secrets-engine

Calcula, desde la terminal de VS Code (WSL2/Ubuntu), las nueve métricas del reporte y
genera para cada una: tabla en la terminal, **resultado general** con valoración,
interpretación, gráfico PNG, JSON y Markdown.

## Instalación (una sola vez)

```bash
cd ~/secrets-engine
bash tools/metricas/instalar.sh
source ~/.bashrc
metricas doctor
```

## Comandos

| Comando | Métrica | Tipo |
|---|---|---|
| `metricas complejidad` | 1. Complejidad ciclomática | Producto |
| `metricas cobertura` | 2. Cobertura de código | Producto |
| `metricas densidad` | 3. Densidad de defectos | Producto |
| `metricas mttd` | 4. Tiempo medio de detección | Proceso |
| `metricas mttr` | 5. Tiempo medio de reparación | Proceso |
| `metricas pruebas` | 6. Eficacia de las pruebas | Proceso |
| `metricas revision` | 7. Eficacia de la revisión | Proyecto |
| `metricas esfuerzo` | 8. Desviación de esfuerzo | Proyecto |
| `metricas arquitectura` | 9. Arquitectura, patrones y frameworks | Proyecto |
| `metricas todo` | Las 9 + resumen, tablero y esquemas | — |
| `metricas resumen` | Solo la tabla resumen (usa lo ya calculado) | — |
| `metricas lint` | golangci-lint por módulo (complementario) | — |
| `metricas doctor` | Verifica herramientas instaladas | — |

Opciones útiles: `--reusar` (cobertura sin volver a correr `go test`), `--rapido`
(`todo` reutilizando perfiles y minería), `--refrescar` (rehacer la minería de defectos),
`--ref RAMA` (analizar otra rama), `--sin-dbus`, `--sin-graficos`.

## Qué hace por dentro

- **Complejidad**: `gocyclo -avg -ignore 'vendor|go-keychain' .`; separa las funciones de `_test.go`.
- **Cobertura**: `go test -coverprofile` en cada módulo de `go.work` (con `GOWORK` y
  `GOFLAGS=-mod=vendor`); arranca D-Bus y gnome-keyring si no existen, como el script de CI
  `store/scripts/gnome-keyring`; genera también el HTML verde/rojo de `go tool cover`.
- **Defectos (base de densidad, MTTD, MTTR, pruebas, revisión)**: minería tipo SZZ de los
  commits `fix:` con `git diff -U0` + `git blame`, y fusión del PR con `git log --merges`.
  Se guarda en caché en `metricas_resultados/defectos/defectos.json` por commit.
- **KLOC**: `cloc <módulo> --exclude-dir=vendor --fullpath --not-match-d=internal/go-keychain`.
- **Arquitectura**: lee `go.work`, `go.mod` e imports para armar el grafo de módulos;
  detecta patrones por expresiones regulares y frameworks por dependencias directas.

## Resultados

```
metricas_resultados/
  complejidad/  complejidad.{json,md,png}  gocyclo.txt
  cobertura/    cobertura.{json,md,png}  perfiles/*.out  html/*.html
  densidad/ mttd/ mttr/ pruebas/ revision/ esfuerzo/ arquitectura/
  defectos/     defectos.json   (minería SZZ)
  resumen/      resumen.{json,md}  tablero.png  arquitectura_metricas.png  ciclo_vida_metricas.png
```

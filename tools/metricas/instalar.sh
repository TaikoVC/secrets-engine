#!/usr/bin/env bash
# Instala la CLI `metricas` y sus dependencias en Ubuntu/WSL2.
# Uso (desde la raíz del repositorio):   bash tools/metricas/instalar.sh
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$AQUI/../.." && pwd)"
echo "== Repositorio: $REPO"

# 1) Paquetes del sistema (solo los que falten)
faltan=()
command -v cloc >/dev/null                 || faltan+=(cloc)
command -v dbus-daemon >/dev/null          || faltan+=(dbus-x11)
command -v gnome-keyring-daemon >/dev/null || faltan+=(gnome-keyring)
python3 -c "import matplotlib" 2>/dev/null || faltan+=(python3-matplotlib)
if [ ${#faltan[@]} -gt 0 ]; then
  echo "== Instalando con apt: ${faltan[*]}  (te pedirá tu contraseña de Ubuntu)"
  sudo apt-get update -qq
  sudo apt-get install -y "${faltan[@]}"
else
  echo "== Paquetes del sistema: ya instalados"
fi

# 2) gocyclo (herramienta de Go)
if ! command -v gocyclo >/dev/null; then
  echo "== Instalando gocyclo"
  go install github.com/fzipp/gocyclo/cmd/gocyclo@latest
fi

# 3) Comando `metricas` en el PATH
mkdir -p "$HOME/.local/bin"
chmod +x "$AQUI/metricas"
ln -sf "$AQUI/metricas" "$HOME/.local/bin/metricas"
for linea in 'export PATH="$HOME/.local/bin:$PATH"' 'export PATH="$PATH:$(go env GOPATH)/bin"'; do
  grep -qxF "$linea" "$HOME/.bashrc" || echo "$linea" >> "$HOME/.bashrc"
done

# 4) Que los resultados no se suban por accidente a git
grep -qxF "metricas_resultados/" "$REPO/.git/info/exclude" 2>/dev/null || echo "metricas_resultados/" >> "$REPO/.git/info/exclude"

echo
echo "== Listo. Abre una terminal nueva (o ejecuta: source ~/.bashrc) y prueba:"
echo "     cd $REPO && metricas doctor"

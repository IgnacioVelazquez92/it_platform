# reset_catalog.ps1
# Limpia migraciones del app catalog (deja solo __init__.py),
# borra __pycache__ relacionados y borra la DB SQLite local.
# Luego genera migración nueva y migra todo.
# USO: powershell -ExecutionPolicy Bypass -File .\reset_catalog.ps1

$ErrorActionPreference = "Stop"

$catalogMigrationsPath = "src\apps\catalog\migrations"
$catalogAppPath = "src\apps\catalog"
$dbPathCandidates = @(
    "db.sqlite3",
    "src\db.sqlite3",
    "src\db.sqlite3",
    "src\apps\db.sqlite3"
)

Write-Host "`n=== RESET CATALOG (LOCAL) ===`n" -ForegroundColor Cyan

# 1) Validar paths
if (-Not (Test-Path $catalogMigrationsPath)) {
    Write-Host "❌ No se encontró: $catalogMigrationsPath" -ForegroundColor Red
    exit 1
}
if (-Not (Test-Path (Join-Path $catalogMigrationsPath "__init__.py"))) {
    Write-Host "❌ Falta __init__.py en: $catalogMigrationsPath" -ForegroundColor Red
    Write-Host "   Django requiere __init__.py para tratarlo como módulo." -ForegroundColor Yellow
    exit 1
}

# 2) Borrar TODAS las migraciones .py (excepto __init__.py) y también .pyc
Write-Host "🧹 Eliminando migraciones de catalog (dejando __init__.py)..." -ForegroundColor Yellow

Get-ChildItem $catalogMigrationsPath -Force |
Where-Object {
    $_.PSIsContainer -eq $false -and
    $_.Name -ne "__init__.py"
} |
ForEach-Object {
    Write-Host "   - Eliminando $($_.FullName)"
    Remove-Item $_.FullName -Force
}

# 3) Borrar __pycache__ del app catalog (incluye migrations)
Write-Host "🧽 Eliminando __pycache__ (catalog)..." -ForegroundColor Yellow

Get-ChildItem $catalogAppPath -Directory -Recurse -Force |
Where-Object { $_.Name -eq "__pycache__" } |
ForEach-Object {
    Write-Host "   - Eliminando $($_.FullName)"
    Remove-Item $_.FullName -Recurse -Force
}

# 4) Borrar SQLite DB (si existe en ubicaciones típicas)
$deletedAnyDb = $false
Write-Host "🗑️  Buscando y borrando SQLite DB..." -ForegroundColor Yellow

foreach ($p in $dbPathCandidates) {
    if (Test-Path $p) {
        Write-Host "   - Eliminando DB: $p"
        Remove-Item $p -Force
        $deletedAnyDb = $true
    }
}

if (-Not $deletedAnyDb) {
    Write-Host "   (No se encontró db.sqlite3 en rutas típicas. Si tu DB está en otra ruta, borrala manualmente.)" -ForegroundColor DarkYellow
}

# 5) Regenerar 0001_initial para catalog desde los modelos actuales
Write-Host "`n⚙️  Generando migraciones (catalog)..." -ForegroundColor Cyan
python src/manage.py makemigrations catalog

# 6) Migrar todo
Write-Host "`n🧱 Aplicando migraciones..." -ForegroundColor Cyan
python src/manage.py migrate

# 7) Verificación rápida: mostrar migraciones catalog aplicadas
Write-Host "`n✅ Estado de migraciones catalog:" -ForegroundColor Green
python src/manage.py showmigrations catalog

Write-Host "`n=== LISTO: catalog reseteado y migrado desde cero ===`n" -ForegroundColor Green

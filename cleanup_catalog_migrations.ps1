# -----------------------------
# BORRAR MIGRACIONES DEL APP catalog
# -----------------------------

$catalogMigrationsPath = "src\apps\catalog\migrations"

if (-Not (Test-Path $catalogMigrationsPath)) {
    Write-Host "❌ No se encontró la carpeta migrations de catalog." -ForegroundColor Red
    exit 1
}

Write-Host "🧹 Limpiando migraciones en $catalogMigrationsPath" -ForegroundColor Yellow

Get-ChildItem $catalogMigrationsPath -File |
Where-Object { $_.Name -ne "__init__.py" } |
ForEach-Object {
    Write-Host "   Eliminando $($_.Name)"
    Remove-Item $_.FullName -Force
}

Write-Host "✅ Migraciones de catalog limpiadas correctamente." -ForegroundColor Green

$ErrorActionPreference = 'Stop'

Write-Host 'Building React UI (static assets)...'
Push-Location 'apps\dsa-web'
if (!(Test-Path 'node_modules')) {
  npm install
}
npm run build
Pop-Location

Write-Host 'Building backend executable...'
if (!(Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
  python -m pip install pyinstaller
}

Write-Host 'Installing backend dependencies...'
python -m pip install -r requirements.txt

if (Test-Path 'dist\backend') {
  Remove-Item -Recurse -Force 'dist\backend'
}
New-Item -ItemType Directory -Path 'dist\backend' | Out-Null

$hiddenImports = @(
  'json_repair',
  'api',
  'api.app',
  'api.deps',
  'api.v1',
  'api.v1.router',
  'api.v1.endpoints',
  'api.v1.endpoints.analysis',
  'api.v1.endpoints.history',
  'api.v1.endpoints.stocks',
  'api.v1.endpoints.health',
  'api.v1.schemas',
  'api.v1.schemas.analysis',
  'api.v1.schemas.history',
  'api.v1.schemas.stocks',
  'api.v1.schemas.common',
  'api.middlewares',
  'api.middlewares.error_handler',
  'src.services',
  'src.services.task_queue',
  'src.services.analysis_service',
  'src.services.history_service',
  'uvicorn.logging',
  'uvicorn.loops',
  'uvicorn.loops.auto',
  'uvicorn.protocols',
  'uvicorn.protocols.http',
  'uvicorn.protocols.http.auto',
  'uvicorn.protocols.websockets',
  'uvicorn.protocols.websockets.auto',
  'uvicorn.lifespan',
  'uvicorn.lifespan.on'
)
$hiddenImportArgs = ($hiddenImports | ForEach-Object { "--hidden-import=$_" }) -join ' '

$cmd = "pyinstaller --name stock_analysis --onedir --noconsole --add-data `"static;static`" $hiddenImportArgs main.py"
Write-Host "Running: $cmd"
Invoke-Expression $cmd

Copy-Item -Path 'dist\stock_analysis' -Destination 'dist\backend\stock_analysis' -Recurse -Force

Write-Host 'Backend build completed.'

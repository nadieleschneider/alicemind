$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectDir

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python não foi encontrado no PATH. Instale Python 3.14 e tente novamente."
}

$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or $pythonVersion -ne "3.14") {
    throw "Este build foi preparado para Python 3.14; versão encontrada: $pythonVersion."
}

Write-Host "Instalando/verificando dependências..."
& python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao instalar dependências de build."
}

Write-Host "Empacotando o AliceMind..."
& python -m PyInstaller --noconfirm --clean --distpath "dist" --workpath "build\alicemind" "omni.spec"
if ($LASTEXITCODE -ne 0) {
    throw "O PyInstaller não conseguiu criar o executável."
}

$executable = Join-Path $projectDir "dist\AliceMind\AliceMind.exe"
if (-not (Test-Path -LiteralPath $executable)) {
    throw "Executável esperado não foi criado: $executable"
}

Write-Host "Validando o executável empacotado..."
$testProcess = Start-Process -FilePath $executable -ArgumentList "--self-test" -Wait -PassThru -WindowStyle Hidden
if ($testProcess.ExitCode -ne 0) {
    throw "O teste de inicialização do executável empacotado falhou."
}

Write-Host ""
Write-Host "Build concluído: $executable"
Write-Host "Abra AliceMind.exe para iniciar o app. Feche-o pelo botão Encerrar AliceMind ou pela janela AliceMind na barra de tarefas."

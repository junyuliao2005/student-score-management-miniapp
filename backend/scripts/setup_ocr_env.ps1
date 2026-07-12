param(
  [string]$PythonPath = $env:OCR_PYTHON,
  [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'

function Test-OcrPython([string]$Candidate) {
  if (-not $Candidate -or -not (Test-Path -LiteralPath $Candidate)) {
    return $false
  }
  $version = & $Candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
  if ($LASTEXITCODE -ne 0) {
    return $false
  }
  return $version.Trim() -in @('3.11', '3.12')
}

$python = $null
if (Test-OcrPython $PythonPath) {
  $python = (Resolve-Path -LiteralPath $PythonPath).Path
}

if (-not $python) {
  foreach ($version in @('3.11', '3.12')) {
    try {
      $candidate = py -$version -c "import sys; print(sys.executable)" 2>$null
      if ($LASTEXITCODE -eq 0 -and $candidate -and (Test-OcrPython $candidate.Trim())) {
        $python = $candidate.Trim()
        break
      }
    } catch {}
  }
}

if (-not $python) {
  throw 'Python 3.11 or 3.12 is required. Set OCR_PYTHON to its python.exe path.'
}

$versionText = & $python -c "import sys; print(sys.version.replace(chr(10), ' '))"
Write-Output "OCR Python: $versionText"
if ($CheckOnly) {
  Write-Output 'CHECK_ONLY_PASS: compatible OCR Python found; no environment was created.'
  exit 0
}

$target = Join-Path $PSScriptRoot '..\.venv-ocr'
if (Test-Path -LiteralPath $target) {
  throw '.venv-ocr already exists. Remove it manually only if it is known to be disposable.'
}

$build = Join-Path $PSScriptRoot ("..\.venv-ocr-build-" + [guid]::NewGuid().ToString('N'))
try {
  & $python -m venv $build
  if ($LASTEXITCODE -ne 0) { throw 'Failed to create OCR virtual environment.' }
  $venvPython = Join-Path $build 'Scripts\python.exe'
  & $venvPython -m pip install --upgrade pip setuptools wheel
  if ($LASTEXITCODE -ne 0) { throw 'Failed to update OCR environment build tools.' }
  & $venvPython -m pip install -r (Join-Path $PSScriptRoot '..\requirements-ocr.txt')
  if ($LASTEXITCODE -ne 0) { throw 'Failed to install OCR requirements.' }
  & $venvPython -c "import PIL, rapidocr, onnxruntime, reportlab; print('OCR_IMPORT_CHECK=PASS')"
  if ($LASTEXITCODE -ne 0) { throw 'OCR dependency import verification failed.' }
  Move-Item -LiteralPath $build -Destination $target
  Write-Output 'OCR environment ready. Set OCR_PROVIDER=local and use .venv-ocr\Scripts\python.exe.'
} finally {
  if (Test-Path -LiteralPath $build) {
    Remove-Item -LiteralPath $build -Recurse -Force
  }
}

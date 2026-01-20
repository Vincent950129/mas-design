param(
  [Parameter(Mandatory = $false)]
  [string]$ExamplesDir = ".\exmaples",

  [Parameter(Mandatory = $false)]
  [switch]$Backup
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ExamplesDir)) {
  throw "ExamplesDir not found: $ExamplesDir"
}

$files = Get-ChildItem -LiteralPath $ExamplesDir -Filter "*.html" -File
if ($files.Count -eq 0) {
  Write-Host "No .html files found in $ExamplesDir"
  exit 0
}

$marker = "/* Readability fix: enlarge text panels */"
$cssSnippet = @"

    $marker
    .text-block { min-height: 220px !important; max-height: 55vh !important; overflow: auto !important; resize: vertical !important; }
    .text-block pre { font-size: 0.95rem !important; line-height: 1.45 !important; }
"@

$updatedCount = 0
$skippedCount = 0

foreach ($f in $files) {
  $path = $f.FullName
  $content = Get-Content -LiteralPath $path -Raw -Encoding UTF8

  if ($content -match [regex]::Escape($marker)) {
    $skippedCount++
    continue
  }

  $newContent = $content

  if ($newContent -match "(?is)</style>") {
    # Inject before the first </style>
    $newContent = [regex]::Replace(
      $newContent,
      "(?is)</style>",
      ($cssSnippet + "`r`n  </style>"),
      1
    )
  } elseif ($newContent -match "(?is)</head>") {
    # Fallback: create a <style> block if missing
    $newContent = [regex]::Replace(
      $newContent,
      "(?is)</head>",
      ("  <style>" + $cssSnippet + "`r`n  </style>`r`n</head>"),
      1
    )
  } else {
    # Last resort: append at end
    $newContent = $newContent + "`r`n<style>" + $cssSnippet + "`r`n</style>`r`n"
  }

  if ($Backup) {
    Copy-Item -LiteralPath $path -Destination ($path + ".bak") -Force
  }

  # Preserve UTF-8 without BOM behavior as best as possible
  Set-Content -LiteralPath $path -Value $newContent -Encoding UTF8
  $updatedCount++
}

Write-Host "Done."
Write-Host "Updated: $updatedCount"
Write-Host "Skipped (already patched): $skippedCount"


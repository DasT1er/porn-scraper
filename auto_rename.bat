<# :
@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "IEX ([System.IO.File]::ReadAllText('%~f0'))"
echo.
echo ========================================
echo Vorgang abgeschlossen!
pause
exit /b
#>

# --- Ab hier ist es echtes PowerShell (Viel stabiler!) ---
$ErrorActionPreference = 'SilentlyContinue'

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "    Galerie-Organizer (Hybrid-Fix)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Pfad abfragen
$root = Read-Host "Bitte den Pfad zum Kategorie-Ordner eingeben (z.B. undertale)"
if (-not (Test-Path -LiteralPath $root)) {
    Write-Host "[!] Pfad nicht gefunden!" -ForegroundColor Red
    return
}

# Alle Unterordner (Galerien) holen
$galleries = Get-ChildItem -LiteralPath $root -Directory

foreach ($gal in $galleries) {
    Write-Host ""
    Write-Host ">>> Verarbeite: $($gal.Name)" -ForegroundColor Magenta

    $jsonPath = Join-Path $gal.FullName "metadata.json"

    if (Test-Path -LiteralPath $jsonPath) {
        # 1. Metadaten sicher auslesen
        try {
            $jsonRaw = Get-Content -LiteralPath $jsonPath -Raw
            $jsonObj = $jsonRaw | ConvertFrom-Json

            # Titel saubern (Teil vor dem Bindestrich)
            $rawTitle = $jsonObj.title.Split('-')[0].Trim()
            $cleanTitle = $rawTitle -replace '[\\\/:\*\?"<>|]', '' # Ungultige Zeichen fur Windows entfernen

            # 2. Tags formatieren (Keine Anfuhrungszeichen, einzeilig)
            $tagList = $jsonObj.tags -replace '"', ''
            $tagString = $tagList -join ', '
            $newTagLine = '"tags": [ ' + $tagString + ' ]'

            # Den gesamten Tags-Block im JSON ersetzen (Regex fur mehrzeilige Suche)
            $updatedJson = $jsonRaw -replace '"tags":\s*\[[\s\S]*?\]', $newTagLine
            $updatedJson | Set-Content -LiteralPath $jsonPath -Encoding UTF8

            # 2.5 Links ersetzen: Alle Links die NICHT pornypics.net sind durch pornypics.net ersetzen
            $updatedJson = Get-Content -LiteralPath $jsonPath -Raw
            $linkRegex = 'https?://(?!(?:www\.)?pornypics\.net)[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s\"\,\}\]]*)?'
            $updatedJson = [regex]::Replace($updatedJson, $linkRegex, {
                param($match)
                $oldUrl = $match.Value
                try {
                    $uri = [System.Uri]$oldUrl
                    $newUrl = "https://pornypics.net" + $uri.PathAndQuery
                    return $newUrl
                } catch {
                    return $oldUrl
                }
            })
            $updatedJson | Set-Content -LiteralPath $jsonPath -Encoding UTF8

            Write-Host "    [JSON] Tags bereinigt, Links ersetzt, Titel gefunden: $cleanTitle" -ForegroundColor Green

            # 3. Bilder umbenennen
            $extensions = @(".jpg", ".jpeg", ".png", ".gif", ".webp")
            $images = Get-ChildItem -LiteralPath $gal.FullName -File | Where-Object { $extensions -contains $_.Extension.ToLower() } | Sort-Object Name

            if ($images.Count -gt 0) {
                # Schritt A: Temporar umbenennen (verhindert Konflikte)
                $count = 1
                foreach ($img in $images) {
                    $tempName = "temp_rename_$($count.ToString('0000'))$($img.Extension)"
                    Rename-Item -LiteralPath $img.FullName -NewName $tempName
                    $count++
                }

                # Schritt B: Final umbenennen
                $tempImages = Get-ChildItem -LiteralPath $gal.FullName -File | Where-Object { $_.Name -like "temp_rename_*" } | Sort-Object Name
                $count = 1
                foreach ($img in $tempImages) {
                    $finalName = "$($cleanTitle)_$($count.ToString('000'))$($img.Extension)"
                    Rename-Item -LiteralPath $img.FullName -NewName $finalName
                    $count++
                }
                Write-Host "    [BILD] $($images.Count) Bilder umbenannt." -ForegroundColor Green
            }
        }
        catch {
            Write-Host "    [!] Fehler in diesem Ordner: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    else {
        Write-Host "    [!] Keine metadata.json gefunden." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "    Fertig!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

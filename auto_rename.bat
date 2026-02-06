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
        try {
            $jsonRaw = Get-Content -LiteralPath $jsonPath -Raw

            # --- JSON reparieren falls Tags keine Anfuehrungszeichen haben ---
            # Erkennung: "tags": [ Wort, Wort ] ohne Anfuehrungszeichen
            if ($jsonRaw -match '"tags":\s*\[') {
                # Tags-Block extrahieren
                $tagsMatch = [regex]::Match($jsonRaw, '"tags":\s*\[([\s\S]*?)\]')
                if ($tagsMatch.Success) {
                    $tagsContent = $tagsMatch.Groups[1].Value.Trim()

                    # Pruefen ob Tags NICHT in Anfuehrungszeichen stehen (kaputtes JSON)
                    # Wenn der erste nicht-whitespace Charakter kein " ist, sind die Tags kaputt
                    $firstChar = ($tagsContent.TrimStart() -replace '^\s*', '')[0]
                    if ($firstChar -ne '"' -and $tagsContent.Length -gt 0) {
                        # Tags sind kaputt - reparieren
                        $tagItems = $tagsContent -split ',' | ForEach-Object {
                            $t = $_.Trim()
                            if ($t -and $t -ne '+ Suggest' -and $t -ne '+') {
                                '"' + $t + '"'
                            }
                        }
                        $fixedTags = '"tags": [' + ($tagItems -join ', ') + ']'
                        $jsonRaw = $jsonRaw -replace '"tags":\s*\[[\s\S]*?\]', $fixedTags
                        $jsonRaw | Set-Content -LiteralPath $jsonPath -Encoding UTF8
                        Write-Host "    [FIX] Tags repariert (Anfuehrungszeichen hinzugefuegt)" -ForegroundColor Yellow
                    }
                }
            }

            # --- Jetzt JSON parsen (sollte jetzt immer funktionieren) ---
            $jsonRaw = Get-Content -LiteralPath $jsonPath -Raw
            $jsonObj = $null

            try {
                $jsonObj = $jsonRaw | ConvertFrom-Json
            } catch {
                # Letzter Versuch: Komplette Regex-basierte Reparatur
                # Alle unquoted Werte im tags-Array finden und quoten
                $jsonRaw = [regex]::Replace($jsonRaw, '"tags":\s*\[([\s\S]*?)\]', {
                    param($m)
                    $inner = $m.Groups[1].Value
                    $items = $inner -split ',' | ForEach-Object {
                        $t = $_.Trim().Trim('"')
                        if ($t -and $t -ne '+ Suggest' -and $t -ne '+') {
                            '"' + $t + '"'
                        }
                    }
                    return '"tags": [' + ($items -join ', ') + ']'
                })
                $jsonRaw | Set-Content -LiteralPath $jsonPath -Encoding UTF8
                $jsonObj = $jsonRaw | ConvertFrom-Json
            }

            if (-not $jsonObj) {
                Write-Host "    [!] JSON konnte nicht gelesen werden." -ForegroundColor Red
                continue
            }

            # 1. Titel saubern (Teil vor dem Bindestrich)
            $rawTitle = $jsonObj.title.Split('-')[0].Trim()
            $cleanTitle = $rawTitle -replace '[\\\/:\*\?"<>|]', ''

            # 2. Tags formatieren (MIT Anfuehrungszeichen - valides JSON!)
            $tagItems = @()
            foreach ($tag in $jsonObj.tags) {
                $t = "$tag".Trim().Trim('"')
                # Muell-Tags rausfiltern
                if ($t -and $t -ne '+ Suggest' -and $t -ne '+' -and $t.Length -gt 1) {
                    $tagItems += '"' + $t + '"'
                }
            }
            $newTagLine = '"tags": [' + ($tagItems -join ', ') + ']'

            # Den gesamten Tags-Block im JSON ersetzen
            $updatedJson = $jsonRaw -replace '"tags":\s*\[[\s\S]*?\]', $newTagLine
            $updatedJson | Set-Content -LiteralPath $jsonPath -Encoding UTF8

            # 3. Links und Domains ersetzen -> "pornypics.net"
            $updatedJson = Get-Content -LiteralPath $jsonPath -Raw
            # Alle vollstaendigen URLs (auch pornypics.net mit Pfad) -> nur "pornypics.net"
            $updatedJson = [regex]::Replace($updatedJson, 'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s\"\,\}\]]*)?', 'pornypics.net')
            # Domain-Erwaehungen im Text (z.B. "at pornpics.de") -> "pornypics.net"
            $updatedJson = $updatedJson -replace 'pornpics\.\w+', 'pornypics.net'
            $updatedJson = $updatedJson -replace 'allasianpics\.\w+', 'pornypics.net'
            $updatedJson = $updatedJson -replace 'lamalinks\.\w+', 'pornypics.net'
            $updatedJson | Set-Content -LiteralPath $jsonPath -Encoding UTF8

            Write-Host "    [JSON] Tags + Links bereinigt, Titel: $cleanTitle" -ForegroundColor Green

            # 4. Bilder umbenennen
            $extensions = @(".jpg", ".jpeg", ".png", ".gif", ".webp")
            $images = Get-ChildItem -LiteralPath $gal.FullName -File | Where-Object { $extensions -contains $_.Extension.ToLower() } | Sort-Object Name

            # Pruefen ob Bilder bereits umbenannt wurden (beginnen mit cleanTitle)
            $alreadyRenamed = $true
            foreach ($img in $images) {
                if (-not $img.Name.StartsWith($cleanTitle)) {
                    $alreadyRenamed = $false
                    break
                }
            }

            if ($images.Count -gt 0 -and -not $alreadyRenamed) {
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
            elseif ($alreadyRenamed -and $images.Count -gt 0) {
                Write-Host "    [BILD] Bereits umbenannt, uebersprungen." -ForegroundColor DarkGray
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

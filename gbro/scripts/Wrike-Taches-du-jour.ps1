<#
  PhoneBox - dalle « Wrike : clôturé aujourd'hui » (widget Commande de PhoneBox).
  Liste vos tâches Wrike terminées aujourd'hui.

  Une seule fois, pour enregistrer votre jeton Wrike (Wrike > Applications et intégrations > API > Créer un jeton permanent) :
      powershell -ExecutionPolicy Bypass -File Wrike-Taches-du-jour.ps1 -Configurer
  Le jeton est chiffré avec votre compte Windows (DPAPI) dans %APPDATA%\PhoneBox\wrike.jeton :
  seul votre compte, sur ce PC, peut le relire. Il ne va jamais sur le téléphone.
#>
param([switch]$Configurer, [int]$Max = 8)
$ErrorActionPreference = 'Stop'
# UTF-8 for the deck only (PhoneBox reads the output); never fatal: some windows (ISE...) have no console
try { if ([Console]::IsOutputRedirected) { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } } catch { }
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$fichier = Join-Path $env:APPDATA 'PhoneBox\wrike.jeton'

if ($Configurer) {
    $jeton = Read-Host 'Collez votre jeton permanent Wrike' -AsSecureString
    $hote = Read-Host 'Adresse Wrike (Entrée = www.wrike.com ; app-eu.wrike.com pour un compte européen)'
    if (-not $hote) { $hote = 'www.wrike.com' }
    [void](New-Item -ItemType Directory -Force -Path (Split-Path $fichier))
    @{ Hote = $hote; Jeton = ($jeton | ConvertFrom-SecureString) } | ConvertTo-Json | Set-Content $fichier -Encoding UTF8
    'Jeton enregistré.'; exit
}
if (-not (Test-Path $fichier)) { "Wrike n'est pas configuré.`nLancez une fois : Wrike-Taches-du-jour.ps1 -Configurer"; exit }

$conf = Get-Content $fichier -Raw | ConvertFrom-Json
$sec = $conf.Jeton | ConvertTo-SecureString
$jeton = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$api = "https://$($conf.Hote)/api/v4"
$h = @{ Authorization = "bearer $jeton" }
try {
    $moi = (Invoke-RestMethod "$api/contacts?me=true" -Headers $h).data[0].id
    $debut = [DateTime]::Today.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $q = "responsibles=" + [Uri]::EscapeDataString("[`"$moi`"]") + "&status=Completed&completedDate=" + [Uri]::EscapeDataString("{`"start`":`"$debut`"}") + "&sortField=CompletedDate&sortOrder=Desc"
    $taches = @((Invoke-RestMethod "$api/tasks?$q" -Headers $h).data)
} catch { "Wrike ne répond pas : $($_.Exception.Message)"; exit }
finally { $jeton = $null }

if ($taches.Count -eq 0) { "Aucune tâche clôturée aujourd'hui"; exit }
"✅ $($taches.Count) tâche(s) clôturée(s) aujourd'hui"
$taches | Select-Object -First $Max | ForEach-Object { "• $($_.title)" }
if ($taches.Count -gt $Max) { "… et $($taches.Count - $Max) autre(s)" }

<#
  PhoneBox - dalle « Mes sites » (widget Commande de PhoneBox).
  Teste le routeur (.254) de chaque site suivi, lu dans la matrice des sites de la Console Admin.
  Les sites suivis sont listés (un nom de ville par ligne) dans Mes-sites.txt, à côté de ce script.
  Affichage : une ligne par site, vert = répond, rouge = ne répond pas. Rien n'est modifié.
#>
param(
    [string]$Matrice = "$env:USERPROFILE\OneDrive - Keolis\General\02_Support Informatique\Console-Admin_V4.5\Donnees\sites.json",
    [string]$Liste = (Join-Path $PSScriptRoot 'Mes-sites.txt'),
    [int]$DelaiMs = 1500
)
$ErrorActionPreference = 'Stop'
# UTF-8 for the deck only (PhoneBox reads the output); never fatal: some windows (ISE...) have no console
try { if ([Console]::IsOutputRedirected) { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } } catch { }
if (-not (Test-Path $Matrice)) { "Matrice des sites introuvable :`n$Matrice"; exit }
if (-not (Test-Path $Liste)) {
    # première utilisation : le fichier est créé avec un exemple, à compléter
    "# Un nom de ville par ligne (comme dans la matrice des sites de la Console Admin)`r`n# Exemple :`r`nSaumur" | Set-Content $Liste -Encoding UTF8
    "Mes-sites.txt vient d'être créé ici :`n$Liste`nAjoutez-y vos villes (une par ligne)."
    exit
}

$sites = (Get-Content $Matrice -Raw -Encoding UTF8 | ConvertFrom-Json).Sites
$suivis = Get-Content $Liste -Encoding UTF8 | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') }
$cibles = foreach ($nom in $suivis) {
    $s = $sites | Where-Object { $_.Ville -eq $nom } | Select-Object -First 1
    if (-not $s) { $s = $sites | Where-Object { $_.Ville -like "*$nom*" } | Select-Object -First 1 }
    if ($s -and $s.Routeur -match '^\d{1,3}(\.\d{1,3}){3}$') { [pscustomobject]@{ Nom = $s.Ville; Ip = $s.Routeur } }
    else { [pscustomobject]@{ Nom = $nom; Ip = $null } }
}

# Tous les pings en même temps (le widget a 20 secondes au plus)
$encours = foreach ($c in $cibles) {
    if ($c.Ip) { [pscustomobject]@{ Cible = $c; Ping = New-Object Net.NetworkInformation.Ping; Tache = $null } }
}
foreach ($e in $encours) { $e.Tache = $e.Ping.SendPingAsync($e.Cible.Ip, $DelaiMs) }
try { [void][Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]@($encours.Tache), $DelaiMs + 1000) } catch { }

$ok = 0; $ko = 0
$lignes = foreach ($c in $cibles) {
    if (-not $c.Ip) { "⚪ $($c.Nom) : absent de la matrice"; continue }
    $t = ($encours | Where-Object { $_.Cible -eq $c }).Tache
    if ($t.IsCompleted -and -not $t.IsFaulted -and $t.Result.Status -eq 'Success') { $ok++; "🟢 $($c.Nom)  $($t.Result.RoundtripTime) ms" }
    else { $ko++; "🔴 $($c.Nom)  hors ligne ($($c.Ip))" }
}
$encours | ForEach-Object { $_.Ping.Dispose() }
if ($ko) { "$ko site(s) hors ligne sur $($ok + $ko)" } else { "Tous les sites répondent ($ok)" }
$lignes

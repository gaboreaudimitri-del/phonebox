<#
  PhoneBox - dalle « Mails non lus » (widget Commande de PhoneBox), Outlook classique de ce PC.
  Lit seulement le nombre de messages non lus de la boîte de réception, sans ouvrir aucun message.
#>
# UTF-8 only for the deck (output read by PhoneBox); a PowerShell window keeps its own encoding
if ([Console]::IsOutputRedirected) { [Console]::OutputEncoding = [Text.Encoding]::UTF8 }
try {
    $ol = New-Object -ComObject Outlook.Application
    $n = $ol.GetNamespace('MAPI').GetDefaultFolder(6).UnReadItemCount
    if ($n -eq 0) { '📭 Aucun mail non lu' } else { "📬 $n mail(s) non lu(s)" }
} catch { "Outlook classique indisponible : $($_.Exception.Message)" }

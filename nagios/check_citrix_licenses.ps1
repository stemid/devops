# Nagios check to monitor number of licenses used in Citrix licensing server
# Example: 
# .\check_citrix_licenses.ps1 -WarnPercent 5 -CritPercent 2 -LicenseType PLATINUM
#
# by Stefan Midjich <swehack@gmail.com>

param (
    [switch]$Help = $false,
    [string]$Hostname = "localhost",
    [int]$WarnPercent = 90,
    [int]$CritPercent = 95,
    [string]$LicenseType = "PLATINUM"
)

if ($Help) {
  $command = $MyInvocation.MyCommand.Name
  echo "$command <-WarnPercent #> <-CritPercent #> <-LicenseType PLATINUM|ADVANCED>"
  echo "  -Help         Show this help text."
  echo "  -WarnPercent  Warn after this percentage is used."
  echo "  -CritPercent  Critical after this percentage is used."
  echo "  -LicenseType  Type of license in all caps, now only supports PLATINUM and ADVANCED."
  Exit 0
}

$Total = 0
$InUse = 0
$return = 0

if ($LicenseType -eq "PLATINUM") {
  $PLD = "MPS_PLT_CCU"
} else {
  $PLD = "MPS_ADV_CCU"
}

# Get Citrix licensing Info
$licensePool = gwmi -class "Citrix_GT_License_Pool" -Namespace "Root\CitrixLicensing" -comp $Hostname

$LicensePool | ForEach-Object{ If ($_.PLD -eq $PLD){
    $Total = $Total + $_.Count
    $InUse = $InUse + $_.InUseCount
    }
}

$PercentUsed = [Math]::Round($inuse/$total*100,0)
$Free = [Math]::Round($Total-$Inuse)

if ($PercentUsed -ge $CritPercent) {
  $nagiosStatus = 'CRITICAL'
  $return = 2
} elseif ($PercentUsed -ge $WarnPercent) {
  $nagiosStatus = 'WARNING'
  $return = 1
} else {
  $nagiosStatus = 'OK'
}

echo "${nagiosStatus}: $PercentUsed% of licenses in use ($InUse/$Total) | used_percent: $PercentUsed"
Exit $return

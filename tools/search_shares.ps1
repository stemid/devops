# Uses WMI to search all shares of a computer for a filename pattern.
#
# Example: .\search_shares.ps1 -Filter "*.encrypted" -ServerName fileserver01
#
# Optional arguments:
# -Recurse - Boolean determining whether to recursively search or not
# -OutputFile - Output search results into CSV format file
# -MoveTo - Move found file to this folder
# 
# by Stefan Midjich <swehack@gmail.com> - 2016

param(
  [string]$ServerName = "localhost",
  [string]$OutputFile = $false,
  [switch]$Recurse = $false,
  [string]$Filter = $(throw "-Filter is required"),
  [string]$MoveTo = $false
)

$report = @()

foreach ($share in get-wmiobject -class win32_share -computer $ServerName) {
  $SearchPath = "\\$($ServerName)\$($share.Name)"
  Write-Progress -Activity "search_shares.ps1" -Status "Searching $($SearchPath)..."

  foreach ($File in (gci -Recurse:$Recurse -Path:$SearchPath -Filter:$Filter | where {! $_.PSIsContainer})) {
    $row = "" | select Owner, FullName, CreationTime, LastAccessTime, LastWriteTime
    $row.Owner = (get-acl $File.FullName).Owner
    $row.FullName = $File.FullName
    $row.CreationTime = $File.CreationTime
    $row.LastAccessTime = $File.LastAccessTime
    $row.LastWriteTime = $File.LastWriteTime

    $report += $row

    if ($MoveTo -ne $false) {
      Write-Progress -Activity "search_shares.ps1" -Status "Moving $($File.FullName) to $($MoveTo)"
      Write-Debug "Moving $($File.FullName) to $($MoveTo)"
      Move-Item $File.FullName $MoveTo
    }

    if ($OutputFile -ne $false) {
      $row | export-csv -Path $OutputFile -Append
    } else {
      write-host $row
    }
  }
}

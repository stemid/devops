# Uses gci to search for files.
#
# Example: .\search_files.ps1 -Filter "*.encrypted" -Recurse
#
# Optional arguments:
# -Recurse - Boolean determining whether to recursively search or not
# -OutputFile - Output search results into CSV format file
# -MoveTo - Move found file to this folder
# 
# by Stefan Midjich <swehack@gmail.com> - 2016

param(
  [string]$SearchPath = $(throw "-SearchPath is required"),
  [string]$OutputFile = $false,
  [switch]$Recurse = $false,
  [string]$Filter = $(throw "-Filter is required"),
  [string]$MoveTo = $false
)

$report = @()

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

  # The -Append argument only works on Win2k12 and higher.
  if ($OutputFile -ne $false) {
    $row | export-csv -Path $OutputFile -Append
  } else {
    write-host $row
  }
}

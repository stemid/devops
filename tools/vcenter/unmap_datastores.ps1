# Powershell script to run unmap on all datastores
#
# WARNING: This is working as designed even if it's producing "unmap is 
# unsupported" errors on thick LUNs, and "operation timed out" errors on
# any thin lun because the process takes too long for PowerCLI to wait. 
#
# One solution is to filter by name in the foreach loop.
# foreach ($ds in get-datastore | where {$_.Name -match "TN"}) 
# For example, if you have TN in the datastore Name of all thin LUNs. 
#
# by Stefan Midjich <swehack@gmail.com>

add-pssnapin VMware.VimAutomation.Core
Set-PowerCLIConfiguration -invalidCertificateAction 'ignore' -confirm:$false -Scope Session
Connect-VIServer -Server 10.220.100.220 -Protocol https

# Disable timeout because unmap operation takes longer than 300 seconds to run
Set-PowerCLIConfiguration -WebOperationTimeoutSeconds -1 -Scope Session -Confirm:$false

$BYTES_TO_GB = 1024*1024*1024
$MB_TO_GB = 1024
foreach ($ds in get-datastore) {
  $dsv = $ds | get-view
  $dsv.RefreshDatastore()
  $dsv.RefreshDatastoreStorageInfo()
  if ($dsv.Summary.accessible -and $dsv.Capability.PerFileThinProvisioningSupported) {
    $ds.Name + ": CapacityGB=" + [int]($ds.CapacityMB / $MB_TO_GB) + " FreeGB=" + [int]($ds.FreeSpaceMB / $MB_TO_GB) + " UncommittedGB=" + [int]($dsv.summary.uncommitted / $BYTES_TO_GB)
    $esx = $ds | get-vmhost | select-object -first 1
    $esxcli = get-esxcli -VMHost $esx
    $esxcli.storage.vmfs.unmap(200, $ds, $null) | out-null
  }
}

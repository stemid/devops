# Powershell script to run unmap on all datastores
#
# WARNING: This is working as designed even if it's producing "unmap is 
# unsupported" errors on thick LUNs, and "operation timed out" errors on
# any thin lun because the process takes too long for PowerCLI to wait. 
#
# by Stefan Midjich <swehack@gmail.com>

add-pssnapin VMware.VimAutomation.Core
Set-PowerCLIConfiguration -invalidCertificateAction 'ignore' -confirm:$false
Connect-VIServer -Server 10.220.100.220 -Protocol https

$BYTES_TO_GB = 1024*1024*1024
$MB_TO_GB = 1024
foreach ($ds in get-datastore) {
  $dsv = $ds | get-view
  $dsv.RefreshDatastore()
  $dsv.RefreshDatastoreStorageInfo()
  if ($dsv.Summary.accessible -and $dsv.Capability.PerFileThinProvisioningSupported) {
    $ds.Name + ": CapacityGB=" + [int]($ds.CapacityMB / $MB_TO_GB) + " FreeGB=" + [int]($ds.FreeSpaceMB / $MB_TO_GB) + " UncommittedGB=" + [int]($dsv.summary.uncommitted / $BYTES_TO_GB)
    $esx = $ds | get-vmhost | select-object -first 1
    $esx
    $esxcli = get-esxcli -VMHost $esx
    $esxcli.system.time.get()
    $esxcli.storage.vmfs.unmap(200, $ds, $null) | out-null
    write-debug "Reclaimed space from $ds.Name"
  }
}

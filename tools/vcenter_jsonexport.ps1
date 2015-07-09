# Export vcenter VMs into JSON format for import into siptrack. 
# by Stefan Midjich <swehack@gmail.com>
#
# For reference: https://pubs.vmware.com/vsphere-55/topic/com.vmware.powercli.cmdletref.doc/VirtualMachine.html

add-pssnapin VMware.VimAutomation.Core
Set-PowerCLIConfiguration -invalidCertificateAction 'ignore' -confirm:$false
Connect-VIServer -Server 10.220.100.220 -Protocol https

$customer_tag = 'Customer Names'
$output_filename = "C:\vSphere scripts/VM CSV export/vcenter.json"
$vms = (get-vm)
$results = @()

foreach($vm in $vms) {
  $row = "" | select Folder, Name, HostName, AdapterType, NIC, IP, VLAN, `
  OperatingSystem, CustomerTag, Tags, Host, Cluster
  $row.Folder = $vm.Folder
  $row.Name = $vm.Name
  $row.HostName = $vm.Guest.HostName
  $row.AdapterType = ($vm | get-networkadapter)
  $row.OperatingSystem = $vm.Guest.OSFullName
  $row.NIC = $vm.Guest.Nics
  $row.IP = $vm.Guest.IPAddress
  $row.VLAN = ($vm | get-networkadapter)
  # Tags requires PowerCLI 5.5 and vSphere 5.1.
  $row.Tags = ($vm | get-tagassignment)
  $row.CustomerTag = ($vm | get-tagassignment | foreach-object {
      $_.Tag
  } | where-object {
    $_.Category -eq $customer_tag
  }).Name
  $row.Host = $vm.VMHost.Name
  $row.Cluster = (get-cluster -vm $vm)
  $results += $row
}

($results | ConvertTo-Json) | Out-File $output_filename

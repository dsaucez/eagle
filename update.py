import yaml
import subprocess
import time

hosts = {}
hosts[8]="192.168.64.5"
hosts[9]="192.168.64.6"
hosts[10]="192.168.64.7"
hosts[11]="192.168.64.33"
hosts[12]="192.168.64.32"

sequences = [{12}, {10, 11}, {8, 9}]

def run_playbook(playbook, inventories=[], extras=[]):
  cmd = ['ansible-playbook']
  for inventory in inventories:
    cmd.append('-i')
    cmd.append(inventory)
  cmd.append(playbook)
  for extra in extras:
    cmd.append('--extra-vars')
    cmd.append(extra)

  print(" ".join(cmd))

begin=time.perf_counter()

seq = 0
for sequence in sequences:
  to_update = {}
  for node in sequence:
    to_update[hosts[node]] = None
  
    inventory = {"all": {"children": {"update": {"hosts": to_update}}}}
  
    hostfile = 'my_hosts-{}.yaml'.format(seq)
 
    with open(hostfile, 'w') as f:
      yaml.dump(inventory, f)

  run_playbook(playbook='k8s-update-others.yaml', inventories=['inventories/blueprint/core/', hostfile], extras=['@params.blueprint.core.yaml', 'update_version=1.27.2'])
  seq = seq + 1

end=time.perf_counter()
print("update took {}s".format( end-begin))

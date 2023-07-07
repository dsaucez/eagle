import igraph as ig
import yaml

ansible_inventory = {}
ansible_inventory['worker0'] = "192.168.64.5"
ansible_inventory['worker1'] = "192.168.64.6"
ansible_inventory['worker2'] = "192.168.64.7"
ansible_inventory['worker3'] = "192.168.64.33"

sequences = [{10, 11}, {8, 9}]

G = ig.Graph.Read_GML('usecase.gml')

for g in G.vs:
  if g['name'] in ansible_inventory:
    g['inventory_name'] = ansible_inventory[g['name']]

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

seq = 0
for sequence in sequences:
  to_update = {}
  for nodeid in sequence:
    to_update[G.vs[nodeid]['inventory_name']] = {'version': G.vs[nodeid]['kubernetes']}
  
    inventory = {"all": {"children": {"update": {"hosts": to_update}}}}
  
    hostfile = 'my_hosts-{}.yaml'.format(seq)
 
    with open(hostfile, 'w') as f:
      yaml.dump(inventory, f)

  run_playbook(playbook='k8s-update-others.yaml', inventories=['inventories/blueprint/core/', hostfile], extras=['@params.blueprint.core.yaml', 'update_version=1.27.2'])
  seq = seq + 1

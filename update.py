import igraph as ig
import yaml
import functools

sequences = [{10, 11}, {8, 9}]

ansible_inventory = {}
ansible_inventory['worker0'] = "192.168.64.5"
ansible_inventory['worker1'] = "192.168.64.6"
ansible_inventory['worker2'] = "192.168.64.7"
ansible_inventory['worker3'] = "192.168.64.33"

update_sequence = {
  '1.25.2': '1.26.2',
  '1.26.2': '1.27.2',
  '1.27.2': None
}

# ###################################################################
def _install(queue, node, version):
  pending = queue.setdefault(version, [])
  pending.append(node)

def _update(version, fct):
  _next = update_sequence.get(version)
  if _next is None:
    return
  fct(_next)
  _update(_next, fct)

def _correct_version(node):
  correction_table = {'1.24': '1.25.2', '1.25': '1.26.2'}
  version = node['kubernetes']
  if version is not None:
    node['kubernetes'] = correction_table[version]

def _inventory(G, nodes):
  group = {}
  for node in nodes:
    group[G.vs[node]['inventory_name']] = None

  inventory = {"all": {"children": {"update": {"hosts": group}}}}  

  return inventory

def _run_playbook(playbook, inventories=[], extras=[]):
  cmd = ['ansible-playbook']
  for inventory in inventories:
    cmd.append('-i')
    cmd.append(inventory)
  cmd.append(playbook)
  for extra in extras:
    cmd.append('--extra-vars')
    cmd.append(extra)

  print(" ".join(cmd))

# ###################################################################

G = ig.Graph.Read_GML('usecase.gml')

# Add inventory name
for node in G.vs:
  name = node['name']
  if name in ansible_inventory:
    _correct_version(node)
    node['inventory_name'] = ansible_inventory[name]

# ###################################################################


inv=0
for sequence in sequences: 
  queue = {}
  for nid in sequence:
    fct = functools.partial(_install, queue, nid)
    _update(G.vs[nid]['kubernetes'], fct)
  print ("#"*80)
  for version in sorted(queue.keys()):
    inventory = _inventory(G, queue[version])
    hosts_file='hosts_{}'.format(inv)
    with open(hosts_file, 'w') as f:
      yaml.dump(inventory, f)

    _run_playbook(playbook='k8s-update.yaml', inventories=['inventories/blueprint/core/', hosts_file], extras=['@params.blueprint.core.yaml', 'update_version={}'.format(version)])
    inv=inv+1

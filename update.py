import igraph as ig
import yaml
import functools
from uuid import uuid4
import os

# ###################################################################
xps = []

xps.append({'sequences': [{9, 11}, {8, 10}], 'topo': 'topos/topo-4.gml'})
xps.append({'sequences': [{8, 9, 10}, {11, 12}], 'topo': 'topos/topo-5.gml'})
xps.append({'sequences': [{9, 10, 13}, {8, 11, 12}], 'topo': 'topos/topo-6.gml'})
xps.append({'sequences': [{8, 9, 10, 13}, {11, 12, 14}], 'topo': 'topos/topo-7.gml'})
xps.append({'sequences': [{9, 10, 12, 15}, {8, 11, 13, 14}], 'topo': 'topos/topo-8.gml'})
xps.append({'sequences': [{9, 10, 11, 12, 13}, {8, 16, 14, 15}], 'topo': 'topos/topo-9.gml'})
xps.append({'sequences': [{17, 10, 11, 12, 13}, {8, 9, 14, 15, 16}], 'topo': 'topos/topo-10.gml'})

# ###################################################################


sequences = [{10, 11}, {8, 9}]
topo = 'usecase.gml'

ansible_inventory = {}
ansible_inventory['worker0']='10.205.80.192'
ansible_inventory['worker9']='10.205.80.87'
ansible_inventory['worker1']='10.205.80.223'
ansible_inventory['worker2']='10.205.80.165'
ansible_inventory['worker3']='10.205.80.163'
ansible_inventory['worker4']='10.205.80.222'
ansible_inventory['worker5']='10.205.80.124'
ansible_inventory['worker6']='10.205.80.198'
ansible_inventory['worker7']='10.205.80.122'
ansible_inventory['worker8']='10.205.80.185'

update_sequence = {
  '1.25.2': '1.26.2',
  '1.26.2': '1.27.2',
  '1.27.2': None
}
v_first,v_intermediate,v_target = tuple(sorted(update_sequence.keys()))

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

  return node['kubernetes']

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

  return " ".join(cmd)


def _dump_hostfile(hostfile, inventory):
  with open(hostfile, 'w') as f:
    yaml.dump(inventory, f)
  return hostfile
 
# ###################################################################

def _xp(sequences, topo):
  dir = 'xps/{}'.format(uuid4())

  os.mkdir(dir)


  _dump_hostfile('{}/readme.yaml'.format(dir), {'sequences': sequences, 'topo': topo})

  G = ig.Graph.Read_GML(topo)
  
  pre_queue = []
  # Add inventory name
  for node in G.vs:
    name = node['name']
    if name in ansible_inventory:
      version = _correct_version(node)
      node['inventory_name'] = ansible_inventory[name]
  
      # #######
      if version == v_intermediate:
        pre_queue.append(int(node['id']))
 
  # ###################################################################
  print ("#"*80)
  print ("# reset")
  cmd = _run_playbook(playbook='k8s-master.yaml', inventories=['inventories/blueprint/core/'], extras=['@params.blueprint.core.yaml'])
  print (cmd)
  print("sleep 60")
  cmd = _run_playbook(playbook='k8s-node.yaml', inventories=['inventories/blueprint/core/'], extras=['@params.blueprint.core.yaml'])
  print (cmd)
  print("sleep 60")
  cmd = _run_playbook(playbook='k8s-update.yaml', inventories=['inventories/blueprint/core/', 'hosts_control'], extras=['@params.blueprint.core.yaml', 'update_version={}'.format(v_intermediate)])
  print (cmd)
  print("sleep 60")

  print ("# pre-seq")
  inventory = _inventory(G, pre_queue)
  hostfile = _dump_hostfile('{}/hosts_pre'.format(dir), inventory)
  cmd = _run_playbook(playbook='k8s-update.yaml', inventories=['inventories/blueprint/core/', hostfile], extras=['@params.blueprint.core.yaml', 'update_version={}'.format(v_intermediate)])
  print (cmd)
  print("sleep 60")
  
  # ###################################################################
  
  
  print ("# experiment")
  inv=0
  with open('{}/update.sh'.format(dir), 'w' )as f:
    for sequence in sequences: 
      queue = {}
      for nid in sequence:
        fct = functools.partial(_install, queue, nid)
        _update(G.vs[nid]['kubernetes'], fct)
      for version in sorted(queue.keys()):
        inventory = _inventory(G, queue[version])
        hostfile = _dump_hostfile('{}/hosts_{}'.format(dir, inv), inventory)
    
        cmd = _run_playbook(playbook='k8s-update.yaml', inventories=['inventories/blueprint/core/', hostfile], extras=['@params.blueprint.core.yaml', 'update_version={}'.format(version)])
        print (cmd, file=f)
        inv=inv+1
 
  print ("time sh {}/update.sh".format(dir)) 
  print("sleep 60")
      




if __name__ == '__main__':
  try: 
    os.mkdir('xps')
  except FileExistsError:
    pass

  for xp in xps:
    sequences = xp['sequences']
    topo = xp['topo']
    _xp(sequences, topo)

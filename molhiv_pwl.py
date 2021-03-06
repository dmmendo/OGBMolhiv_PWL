import numpy as np
from scipy.sparse import lil_matrix, csc_matrix, vstack, hstack
from ogb.graphproppred import PygGraphPropPredDataset, Evaluator
import sys

# Load the dataset 
dataset = PygGraphPropPredDataset(name='ogbg-molhiv')

split_idx = dataset.get_idx_split()

def PWL_transform_feature(dataset,edge_index,tau=1):
  u_id = 0
  feat_dict = {}
  nodelabel_dict = {}
  dataset_nodelabel = []
  new_edgeweights = []
  for g_iter in range(len(dataset)):
    dataset_nodelabel.append([])
    new_edgeweights.append([])
    n_attr = dataset[g_iter]['x'].numpy()
    for node in n_attr:
      nt = tuple(node)
      if nt not in feat_dict:
        feat_dict[nt] = u_id
        nodelabel_dict[tuple([u_id])] = u_id
        u_id += 1
      dataset_nodelabel[-1].append(feat_dict[nt])
    g = dataset_nodelabel[-1]
    for edge in edge_index[g_iter].T:
      src,dst = edge  
      if g[src] == g[dst]:
        new_edgeweights[-1].append(tau)
      else:
        new_edgeweights[-1].append(1+tau)
  return dataset_nodelabel, new_edgeweights, nodelabel_dict, u_id

def PWL_compressed(colored_graphs,cmp_persist,p=2):
  dim = max([cg[1] for cg in colored_graphs])
  block_slice = 1
  num_graphs = len(colored_graphs[0][0])
  kernel_list = None
  block_size = 1000
  g_kernel = np.zeros((block_size,dim))
  b = 0
  for i in range(num_graphs):
    for wg_iter in range(len(colored_graphs)):
      g = colored_graphs[wg_iter][0][i]
      for n_iter in range(len(g)):
        if n_iter in cmp_persist[wg_iter][i]:
          g_kernel[b][g[n_iter]] += cmp_persist[wg_iter][i][n_iter]**p
    b += 1
    if b >= block_size:
      if kernel_list is None:
        kernel_list = csc_matrix(g_kernel,shape=g_kernel.shape)
      else:
        sp_g_kernel = csc_matrix(g_kernel,shape=g_kernel.shape)
        kernel_list = vstack([kernel_list,sp_g_kernel],format='csc')
      block_size = min(block_size,num_graphs-i-1)
      g_kernel = np.zeros((block_size,dim))
      b = 0    
  return kernel_list

def PWLC_compressed(colored_graphs,edge_index,cmp_persist,cyc_persist,p=2):
  dim = max([cg[1] for cg in colored_graphs])
  block_slice = 1
  num_graphs = len(colored_graphs[0][0])
  kernel_list = None
  block_size = 1000
  g_kernel = np.zeros((block_size,2*dim))
  b = 0
  for i in range(num_graphs):
    for wg_iter in range(len(colored_graphs)):
      g = colored_graphs[wg_iter][0][i]
      for n_iter in range(len(g)):
        if n_iter in cmp_persist[wg_iter][i]:
          g_kernel[b][g[n_iter]] += cmp_persist[wg_iter][i][n_iter]**p
      for edge in edge_index[i].T:
        src,dst = edge
        if (src,dst) in cyc_persist[wg_iter][i]:
          g_kernel[b][dim + g[src]] += cyc_persist[wg_iter][i][(src,dst)]**p
    b += 1
    if b >= block_size:
      if kernel_list is None:
        kernel_list = csc_matrix(g_kernel,shape=g_kernel.shape)
      else:
        sp_g_kernel = csc_matrix(g_kernel,shape=g_kernel.shape)
        kernel_list = vstack([kernel_list,sp_g_kernel],format='csc')
      block_size = min(block_size,num_graphs-i-1)
      g_kernel = np.zeros((block_size,2*dim))
      b = 0    
  return kernel_list

def transform_edge_index(dataset):
  edge_index = []
  for g in dataset:
    edge_index.append(g['edge_index'].numpy())
  return edge_index

def d_M(src_label,dst_label,src_set,dst_set,p):
  diff_dict = {}
  if src_label != dst_label:
    diff_dict[src_label] = 1
    diff_dict[dst_label] = -1

  for entry in src_set:
    if entry not in diff_dict:
      diff_dict[entry] = 1
    else:
      diff_dict[entry] += 1
  for entry in dst_set:
    if entry not in diff_dict:
      diff_dict[entry] = -1
    else:
      diff_dict[entry] -= 1
  distance = 0
  for label in diff_dict:
    distance += np.abs(diff_dict[label])**p
  return distance**(1/p)

def d_L(src_label,dst_label,src_set,dst_set,p=2,tau=1):
  if src_label == dst_label:
    return d_M(src_label,dst_label,src_set,dst_set,p) + tau
  else:
    return 1 + d_M(src_label,dst_label,src_set,dst_set,p) + tau

def PWL_iteration(nodelabels,edge_index,nodelabel_dict,u_id,p=2,tau=1):
  new_nodelabels = []
  new_edgeweights = []
  for g_iter in range(len(nodelabels)):
    new_nodelabels.append([])
    new_edgeweights.append([])
    g = nodelabels[g_iter]
    messages = [[] for i in range(len(g)) ]
    for edge in edge_index[g_iter].T:
      src,dst = edge
      messages[dst].append(g[src])
    for edge in edge_index[g_iter].T:
      src,dst = edge  
      new_edgeweights[-1].append(d_L(g[src],g[dst],messages[src],messages[dst],p,tau))
    for i in range(len(messages)):
      messages[i].sort()
      l_v = tuple([g[i]] + messages[i])
      if l_v not in nodelabel_dict:
        nodelabel_dict[l_v] = u_id
        u_id += 1
      new_nodelabels[-1].append(nodelabel_dict[l_v])
  return new_nodelabels, new_edgeweights, nodelabel_dict, u_id

def get_persistence(weighted_graphs,edge_index):
  persist = []
  cycle_persist = []
  for entry in weighted_graphs:
    nodelabels, u_id, edgeweights = entry
    persist.append([])
    cycle_persist.append([])
    for g_iter in range(len(nodelabels)):
      g = nodelabels[g_iter]
      g_edge_index = edge_index[g_iter].T
      E = edgeweights[g_iter]
      persist[-1].append({})
      cycle_persist[-1].append({})
      sorted_idx = np.argsort(E)
      visited_nodes = set()
      cmp_edges = set()
      for e_id in sorted_idx:
        src,dst = g_edge_index[e_id]
        if dst not in visited_nodes:
          persist[-1][-1][dst] = E[e_id]
          cmp_edges.add((src,dst))
        if src not in visited_nodes:
          persist[-1][-1][src] = E[e_id]
          cmp_edges.add((src,dst))
        if dst in visited_nodes and src in visited_nodes and (dst,src) not in cmp_edges:
          cycle_persist[-1][-1][(src,dst)] = E[e_id]
        visited_nodes.add(dst)
        visited_nodes.add(src)
  return persist, cycle_persist

def sparse_split(kernel,train_idx,valid_idx,test_idx):
  lil_kernel = lil_matrix(kernel)
  Xtrain = lil_kernel[train_idx].tocsc()
  Xvalid = lil_kernel[valid_idx].tocsc()
  Xtest = lil_kernel[test_idx].tocsc()
  return Xtrain,Xvalid,Xtest

def count_params(clf):
  total = 0
  for tree in clf.estimators_:
    treeObj = tree.tree_
    total += treeObj.node_count
  return total

train_idx = split_idx['train'].numpy()
valid_idx = split_idx['valid'].numpy()
test_idx = split_idx['test'].numpy()

graphlabels = []
for g in dataset:
  graphlabels.append(g['y'][0][0].numpy())
graphlabels = np.array(graphlabels)

edge_index = transform_edge_index(dataset)

H = int(sys.argv[2])
p = float(sys.argv[3])
tau = float(sys.argv[4])

assert H > 0
assert p > 0
assert tau > 0

init_nodelabels, init_edgeweights, nodelabel_dict, u_id = PWL_transform_feature(dataset,edge_index,tau)
weighted_graphs = [(init_nodelabels,u_id,init_edgeweights)]
cur_nodelabels = init_nodelabels
for h in range(H-1):
  next_nodelabels, next_edgeweights, nodelabel_dict, u_id = PWL_iteration(cur_nodelabels,edge_index,nodelabel_dict,u_id,p,tau)
  weighted_graphs.append((next_nodelabels,u_id,next_edgeweights))
  cur_nodelabels = next_nodelabels

#WL generate kernels

cmp_persist, cyc_persist = get_persistence(weighted_graphs,edge_index)

if sys.argv[1] == '-pwlc':
  kernel_list = PWLC_compressed(weighted_graphs,edge_index,cmp_persist,cyc_persist)
elif sys.argv[1] == '-pwl':
  kernel_list = PWL_compressed(weighted_graphs,cmp_persist)
else:
  print("invalid option: please specify either '-pwl' or 'pwlc'")
  exit()

#Setup data split and labels

Xtrain, Xvalid, Xtest = sparse_split(kernel_list,train_idx,valid_idx,test_idx)

#WL+RandomForest Model

from sklearn.ensemble import RandomForestClassifier

#Full eval

evaluator = Evaluator(name='ogbg-molhiv')

num_seeds = 10

valid_results = []
test_results = []
pcount_results = []
for seed in range(num_seeds):
  clf = RandomForestClassifier(random_state=seed,n_estimators=1000).fit(Xtrain,graphlabels[train_idx])
  y_pred_valid = clf.predict_proba(Xvalid)[:, 1]
  y_pred_valid = y_pred_valid.reshape(y_pred_valid.shape[0],1)
  y_pred_test = clf.predict_proba(Xtest)[:, 1]
  y_pred_test = y_pred_test.reshape(y_pred_test.shape[0],1)
  valid_dict = { "y_true":graphlabels[valid_idx].reshape(len(valid_idx),1), "y_pred":y_pred_valid }
  test_dict = { "y_true":graphlabels[test_idx].reshape(len(test_idx),1), "y_pred":y_pred_test }
  valid_results.append(evaluator.eval(valid_dict)[dataset.eval_metric])
  test_results.append(evaluator.eval(test_dict)[dataset.eval_metric])
  pcount_results.append(count_params(clf))

print('model parameter counts:')
for seed in range(num_seeds):
  print("\tseed",seed,':',pcount_results[seed])

print('test results:')
for seed in range(num_seeds):
  print("\tseed",seed,':',test_results[seed])

print('validation results:')
for seed in range(num_seeds):
  print("\tseed",seed,':',valid_results[seed])

print('test (avg,std-dev) roc-auc:')
print((np.mean(test_results),np.std(test_results)))
print('validation (avg,std-dev) roc-auc:')
print((np.mean(valid_results),np.std(valid_results)))


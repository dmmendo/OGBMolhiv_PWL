## Implementation of a Persistent Weisfeiler–Lehman Procedure for Graph Classification

This project is an implementation of a Persistent Weisfeiler-Lehman (P-WL) procedure based on the Stanford Molhiv OGB (1.3.0) dataset. P-WL is a graph classification method proposed by Bastian Rieck, Christian Bock, and Karsten Borgwardt in ICML 2019. The original paper can be viewed [here](http://proceedings.mlr.press/v97/rieck19a/rieck19a.pdf).

### Note:

We implement P-WL and P-WL-C with a random forest classifier.

### Install environment:
``` 
    pip install scipy
    pip install numpy
    pip install sklearn=0.24.1
    pip install torch==1.8.0+cpu -f https://download.pytorch.org/whl/torch_stable.html
    pip install torch-scatter -f https://pytorch-geometric.com/whl/torch-1.8.0+cpu.html
    pip install torch-sparse -f https://pytorch-geometric.com/whl/torch-1.8.0+cpu.html
    pip install torch-geometric
    pip install ogb
```

### Usage:
To train and evaluate the model on 10 different seeds, specify model hyperparameters and execute:
``` 
    python molhiv_pwl.py [-pwl or -pwlc] [H] [p] [τ]
```
Example of executing P-WL-C with H=2, p=2, and τ=1:
``` 
    python molhiv_pwl.py -pwlc 2 2 1
```

 
### Explored Hyperparameters:

```
H: [1,2*,3], p: [2*,3], τ: [1*,2], n_estimators: [100,1000*]
```


### Reference performance for Molhiv OGB:
Results below fix p=2, τ=1, and n_estimators = 1000

| Model              |Test Accuracy    |Valid Accuracy   | Parameters    | Hardware |
| ------------------ |--------------   | --------------- | -------------- |----------|
| P-WL (H=1)     | 0.7532  ± 0.0033 | 0.8251  ± 0.0051 | 468,369  | CPU |
| P-WL (H=2)       | 0.7936  ± 0.0042 | 0.8368  ± 0.0047 | 473,489 | CPU |
| P-WL (H=3)       | 0.7858  ± 0.0061 | 0.8054  ± 0.0068 | 1,162,515 | CPU |
| P-WL-C (H=1)  | 0.7665  ± 0.0036 | 0.8204  ± 0.0054 | 1,470,905  | CPU |
| P-WL-C (H=2)    | **0.8039  ± 0.0040** | 0.8279  ± 0.0059 | 4,600,000  | CPU |
| P-WL-C (H=3) | 0.7886  ± 0.0050 | 0.7981  ± 0.0064 | 1,879,664  | CPU |

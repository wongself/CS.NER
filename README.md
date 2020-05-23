# Named Entity Recognition with Feature Engineering for Computer Science Literature
PyTorch code for SpERT: "Span-based Entity and Relation Transformer". For a description of the model and experiments.

![Model Architecture](https://i.imgur.com/VfpeRJL.png)

## Setup
### Requirements
- Required
  - Python 3.6 or higher
  - PyTorch 1.4.0 or higher
  - Transformers 2.8.0 or hifher
  - tqdm 4.45.0 or higher

## Usage
Fetch model checkpoints (best out of 5 runs for each dataset):
```
bash ./scripts/fetch_models.sh
```

Train CoNLL04 on train dataset, evaluate on dev dataset:
```
python ./spert.py train --config configs/example_train.conf
```

## Notes
- To train SpERT with SciBERT \[5\] download SciBERT from https://github.com/allenai/scibert (under "PyTorch HuggingFace Models") and set "model_path" and "tokenizer_path" in the config file to point to the SciBERT directory.
- You can call "python ./spert.py train --help" or "python ./spert.py eval --help" for a description of training/evaluation arguments.
- Please cite our paper when you use SpERT: <br/>
Markus Eberts, Adrian Ulges. Span-based Joint Entity and Relation Extraction with Transformer Pre-training. 24th European Conference on Artificial Intelligence, 2020.

## References
```
[1] Luan Y, He L, Ostendorf M, et al. Multi-task identification of entities, relations, and coreference for scientific knowledge graph construction[J]. arXiv preprint arXiv:1808.09602, 2018.
[2] Yan T, Huang H, Mao X L. SEPT: Improving Scientific Named Entity Recognition with Span Representation[J]. arXiv preprint arXiv:1911.03353, 2019.
[3] Eberts M, Ulges A. Span-based Joint Entity and Relation Extraction with Transformer Pre-training[J]. arXiv preprint arXiv:1909.07755, 2019.
[4] Beltagy I, Cohan A, Lo K. Scibert: Pretrained contextualized embeddings for scientific text[J]. arXiv preprint arXiv:1903.10676, 2019.
```

import json
from abc import abstractmethod, ABC
from collections import OrderedDict
from logging import Logger
from typing import Iterable, List

from tqdm import tqdm
from transformers import BertTokenizer

from ner.model.entity import Dataset, EntityType, Entity, Document


class BaseInputReader(ABC):
    def __init__(
        self, types_path: str, tokenizer: BertTokenizer,
        neg_entity_count: int = None, max_span_size:
        int = None, logger: Logger = None):
        types = json.load(open(types_path), object_pairs_hook=OrderedDict)

        self._entity_types = OrderedDict()
        self._idx2entity_type = OrderedDict()

        # entities
        # add 'None' entity type
        none_entity_type = EntityType('None', 0, 'None', 'No Entity')
        self._entity_types['None'] = none_entity_type
        self._idx2entity_type[0] = none_entity_type

        # specified entity types
        for i, (key, v) in enumerate(types['entities'].items()):
            entity_type = EntityType(key, i + 1, v['short'], v['verbose'])
            self._entity_types[key] = entity_type
            self._idx2entity_type[i + 1] = entity_type

        self._neg_entity_count = neg_entity_count
        self._max_span_size = max_span_size

        self._datasets = dict()

        self._tokenizer = tokenizer
        self._logger = logger

        self._vocabulary_size = tokenizer.vocab_size
        self._context_size = -1

    @abstractmethod
    def read(self, datasets):
        pass

    def get_dataset(self, label) -> Dataset:
        return self._datasets[label]

    def get_entity_type(self, idx) -> EntityType:
        entity = self._idx2entity_type[idx]
        return entity

    def _calc_context_size(self, datasets: Iterable[Dataset]):
        sizes = []

        for dataset in datasets:
            for doc in dataset.documents:
                sizes.append(len(doc.encoding))

        context_size = max(sizes)
        return context_size

    def _log(self, text):
        if self._logger is not None:
            self._logger.info(text)

    @property
    def datasets(self):
        return self._datasets

    @property
    def entity_types(self):
        return self._entity_types

    @property
    def entity_type_count(self):
        return len(self._entity_types)

    @property
    def vocabulary_size(self):
        return self._vocabulary_size

    @property
    def context_size(self):
        return self._context_size

    def __str__(self):
        string = ""
        for dataset in self._datasets.values():
            string += "Dataset: %s\n" % dataset
            string += str(dataset)

        return string

    def __repr__(self):
        return self.__str__()


class JsonInputReader(BaseInputReader):
    def __init__(
        self, types_path: str, tokenizer: BertTokenizer,
        neg_entity_count: int = None, max_span_size: int = None,
        logger: Logger = None):
        super().__init__(types_path, tokenizer, neg_entity_count, max_span_size, logger)

    def read(self, dataset_packages):
        for dataset_label, jdocument in dataset_packages.items():
            dataset = Dataset(dataset_label, self._entity_types, self._neg_entity_count, self._max_span_size)
            self._parse_document(jdocument, dataset)
            self._datasets[dataset_label] = dataset

        self._context_size = self._calc_context_size(self._datasets.values())

    def _parse_document(self, jdocument, dataset):
        for paragraph in tqdm(jdocument, desc="Parse document '%s'" % dataset.label):
            self._parse_paragraph(paragraph, dataset)

    def _parse_paragraph(self, para, dataset) -> Document:
        jtokens = para['tokens']
        jentities = para['entities']

        # parse tokens
        doc_tokens, doc_encoding = self._parse_tokens(jtokens, dataset)

        # parse entity mentions
        entities = self._parse_entities(jentities, doc_tokens, dataset)

        # create document
        document = dataset.create_document(doc_tokens, entities, doc_encoding)

        return document

    def _parse_tokens(self, jtokens, dataset):
        doc_tokens = []

        # full document encoding including special tokens ([CLS] and [SEP]) and byte-pair encodings of original tokens
        doc_encoding = [self._tokenizer.convert_tokens_to_ids('[CLS]')]

        # parse tokens
        for i, token_phrase in enumerate(jtokens):
            token_encoding = self._tokenizer.encode(token_phrase, add_special_tokens=False)
            span_start, span_end = (len(doc_encoding), len(doc_encoding) + len(token_encoding))

            token = dataset.create_token(i, span_start, span_end, token_phrase)

            doc_tokens.append(token)
            doc_encoding += token_encoding

        doc_encoding += [self._tokenizer.convert_tokens_to_ids('[SEP]')]

        return doc_tokens, doc_encoding

    def _parse_entities(self, jentities, doc_tokens, dataset) -> List[Entity]:
        entities = []

        for entity_idx, jentity in enumerate(jentities):
            entity_type = self._entity_types[jentity['type']]
            start, end = jentity['start'], jentity['end']

            # create entity mention
            tokens = doc_tokens[start:end]
            phrase = " ".join([t.phrase for t in tokens])
            entity = dataset.create_entity(entity_type, tokens, phrase)
            entities.append(entity)

        return entities

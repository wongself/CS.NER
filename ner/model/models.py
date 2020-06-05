import torch
from torch import nn as nn
from transformers import BertConfig
from transformers import BertModel
from transformers import BertPreTrainedModel


class CSER(BertPreTrainedModel):
    """ Span-based model to extract entities """

    def __init__(
        self, config: BertConfig, cls_token: int, entity_types: int,
        size_embedding: int, prop_drop: float, freeze_transformer: bool): # noqa

        super(CSER, self).__init__(config)

        # BERT model
        self.bert = BertModel(config)

        # layers
        self.entity_classifier = nn.Linear(config.hidden_size * 2 + size_embedding, entity_types)
        self.size_embeddings = nn.Embedding(100, size_embedding)
        self.dropout = nn.Dropout(prop_drop)

        self._cls_token = cls_token
        self._entity_types = entity_types

        # weight initialization
        self.init_weights()

        if freeze_transformer:
            print("Freeze transformer weights")

            # freeze all transformer weights
            for param in self.bert.parameters():
                param.requires_grad = False

    def _forward_eval(
        self, encodings: torch.tensor, context_masks: torch.tensor,
        entity_masks: torch.tensor, entity_sizes: torch.tensor,
        entity_spans: torch.tensor, entity_sample_masks: torch.tensor): # noqa
        # get contextualized token embeddings from last transformer layer
        context_masks = context_masks.float()
        h = self.bert(input_ids=encodings, attention_mask=context_masks)[0]

        # classify entities
        size_embeddings = self.size_embeddings(entity_sizes)  # embed entity candidate sizes
        entity_clf, entity_spans_pool = self._classify_entities(encodings, h, entity_masks, size_embeddings)

        # apply softmax
        entity_clf = torch.softmax(entity_clf, dim=2)

        return entity_clf

    def _classify_entities(self, encodings, h, entity_masks, size_embeddings):
        # max pool entity candidate spans
        m = (entity_masks.unsqueeze(-1) == 0).float() * (-1e30)
        entity_spans_pool = m + h.unsqueeze(1).repeat(1, entity_masks.shape[1], 1, 1)
        entity_spans_pool = entity_spans_pool.max(dim=2)[0]

        # get cls token as candidate context representation
        entity_ctx = get_token(h, encodings, self._cls_token)

        # create candidate representations including context, max pooled span and size embedding
        entity_repr = torch.cat([
            entity_ctx.unsqueeze(1).repeat(1, entity_spans_pool.shape[1], 1),
            entity_spans_pool, size_embeddings
        ], dim=2)
        entity_repr = self.dropout(entity_repr)

        # classify entity candidates
        entity_clf = self.entity_classifier(entity_repr)

        return entity_clf, entity_spans_pool

    def forward(self, *args, **kwargs):
        return self._forward_eval(*args, **kwargs)


def get_token(h: torch.tensor, x: torch.tensor, token: int):
    """ Get specific token embedding (e.g. [CLS]) """
    emb_size = h.shape[-1]

    token_h = h.view(-1, emb_size)
    flat = x.contiguous().view(-1)

    # get contextualized embedding of given token
    token_h = token_h[flat == token, :]

    return token_h


# Model access
_MODELS = {
    'cser': CSER,
}


def get_model(name):
    return _MODELS[name]

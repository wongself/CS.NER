import argparse
import datetime
import logging
import math
import os
import sys
import tensorboardX
from tqdm import tqdm
from typing import List, Dict, Tuple

import torch
from torch.nn import DataParallel
from torch.optim import Optimizer
from torch.utils.data import DataLoader

import transformers
from transformers import AdamW, BertConfig
from transformers import BertTokenizer
from transformers import PreTrainedModel
from transformers import PreTrainedTokenizer

from span import models
from span import sampling
from span import util
from span.entity import Dataset
from span.evaluator import Evaluator
from span.reader import JsonInputReader, BaseInputReader
from span.loss import SpanLoss, Loss


class BaseTrainer:
    """ Trainer base class with common methods """
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self._debug = self.args.debug

        # logging
        name = str(datetime.datetime.now()).replace(' ', '_')
        self._log_path = os.path.join(self.args.log_path, self.args.label, name)
        util.create_directories_dir(self._log_path)

        if hasattr(args, 'save_path'):
            self._save_path = os.path.join(self.args.save_path, self.args.label, name)
            util.create_directories_dir(self._save_path)

        self._log_paths = dict()

        # file + console logging
        log_formatter = logging.Formatter(
            "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
        )
        self._logger = logging.getLogger()
        util.reset_logger(self._logger)

        file_handler = logging.FileHandler(
            os.path.join(self._log_path, 'all.log'))
        file_handler.setFormatter(log_formatter)
        self._logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        self._logger.addHandler(console_handler)

        if self._debug:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

        # tensorboard summary
        self._summary_writer = tensorboardX.SummaryWriter(
            self._log_path) if tensorboardX is not None else None

        self._best_results = dict()
        self._log_arguments()

        # CUDA devices
        self._device = torch.device(
            "cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
        self._gpu_count = torch.cuda.device_count()

        # set seed
        if args.seed is not None:
            util.set_seed(args.seed)

    def _add_dataset_logging(self, *labels, data: Dict[str, List[str]]):
        for label in labels:
            dic = dict()

            for key, columns in data.items():
                path = os.path.join(self._log_path, '%s_%s.csv' % (key, label))
                util.create_csv(path, *columns)
                dic[key] = path

            self._log_paths[label] = dic
            self._best_results[label] = 0

    def _log_arguments(self):
        util.save_dict(self._log_path, self.args, 'args')
        if self._summary_writer is not None:
            util.summarize_dict(self._summary_writer, self.args, 'args')

    def _log_tensorboard(self, dataset_label: str, data_label: str, data: object, iteration: int):
        if self._summary_writer is not None:
            self._summary_writer.add_scalar(
                'data/%s/%s' % (dataset_label, data_label), data, iteration)

    def _log_csv(self, dataset_label: str, data_label: str,
                 *data: Tuple[object]):
        logs = self._log_paths[dataset_label]
        util.append_csv(logs[data_label], *data)

    def _save_best(
        self, model: PreTrainedModel, tokenizer: PreTrainedTokenizer,
        optimizer: Optimizer, accuracy: float, iteration: int, label: str, extra=None):

        if accuracy > self._best_results[label]:
            self._logger.info(
                "[%s] Best model in iteration %s: %s%% accuracy" %
                (label, iteration, accuracy))
            self._save_model(
                self._save_path,
                model,
                tokenizer,
                iteration,
                optimizer=optimizer if self.args.save_optimizer else None,
                save_as_best=True,
                name='model_%s' % label,
                extra=extra)
            self._best_results[label] = accuracy

    def _save_model(
        self, save_path: str, model: PreTrainedModel, tokenizer: PreTrainedTokenizer,
        iteration: int, optimizer: Optimizer = None, save_as_best: bool = False,
        extra: dict = None, include_iteration: int = True, name: str = 'model'):

        extra_state = dict(iteration=iteration)

        if optimizer:
            extra_state['optimizer'] = optimizer.state_dict()

        if extra:
            extra_state.update(extra)

        if save_as_best:
            dir_path = os.path.join(save_path, '%s_best' % name)
        else:
            dir_name = '%s_%s' % (name, iteration) if include_iteration else name
            dir_path = os.path.join(save_path, dir_name)

        util.create_directories_dir(dir_path)

        # save model
        if isinstance(model, DataParallel):
            model.module.save_pretrained(dir_path)
        else:
            model.save_pretrained(dir_path)

        # save vocabulary
        tokenizer.save_pretrained(dir_path)

        # save extra
        state_path = os.path.join(dir_path, 'extra.state')
        torch.save(extra_state, state_path)

    def _get_lr(self, optimizer):
        lrs = []
        for group in optimizer.param_groups:
            lr_scheduled = group['lr']
            lrs.append(lr_scheduled)
        return lrs

    def _close_summary_writer(self):
        if self._summary_writer is not None:
            self._summary_writer.close()


class SpanTrainer(BaseTrainer):
    """ Joint entity extraction training and evaluation """
    def __init__(self, args: argparse.Namespace):
        super().__init__(args)

        # byte-pair encoding
        self._tokenizer = BertTokenizer.from_pretrained(
            args.tokenizer_path,
            do_lower_case=args.lowercase,
            cache_dir=args.cache_path)

        # path to export predictions to
        self._predictions_path = os.path.join(self._log_path, 'predictions_%s_epoch_%s.json')

        # path to export entity extraction examples to
        self._examples_path = os.path.join(self._log_path, 'examples_%s_%s_epoch_%s.html')

    def train(self, train_path: str, valid_path: str, types_path: str, input_reader_cls: BaseInputReader):
        args = self.args
        train_label, valid_label = 'train', 'valid'

        self._logger.info("Datasets: %s, %s" % (train_path, valid_path))
        self._logger.info("Model type: %s" % args.model_type)

        # create log csv files
        self._init_train_logging(train_label)
        self._init_eval_logging(valid_label)

        # read datasets
        input_reader = input_reader_cls(types_path, self._tokenizer, args.neg_entity_count, args.max_span_size, self._logger)
        input_reader.read({train_label: train_path, valid_label: valid_path})
        self._log_datasets(input_reader)

        train_dataset = input_reader.get_dataset(train_label)
        train_sample_count = train_dataset.document_count
        updates_epoch = train_sample_count // args.train_batch_size
        updates_total = updates_epoch * args.epochs

        validation_dataset = input_reader.get_dataset(valid_label)

        self._logger.info("Updates per epoch: %s" % updates_epoch)
        self._logger.info("Updates total: %s" % updates_total)

        # create model
        model_class = models.get_model(self.args.model_type)

        # load model
        config = BertConfig.from_pretrained(self.args.model_path, cache_dir=self.args.cache_path)

        model = model_class.from_pretrained(
            self.args.model_path,
            config=config,
            # model parameters
            cls_token=self._tokenizer.convert_tokens_to_ids('[CLS]'),
            entity_types=input_reader.entity_type_count,
            max_pairs=self.args.max_pairs,
            prop_drop=self.args.prop_drop,
            size_embedding=self.args.size_embedding,
            freeze_transformer=self.args.freeze_transformer)

        # If you still want to train Span on multiple GPUs, uncomment the following lines
        # # parallelize model
        # if self._device.type != 'cpu':
        #     model = torch.nn.DataParallel(model)
        model.to(self._device)

        # create optimizer
        optimizer_params = self._get_optimizer_params(model)
        optimizer = AdamW(optimizer_params, lr=args.lr, weight_decay=args.weight_decay, correct_bias=False)

        # create scheduler
        scheduler = transformers.get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=args.lr_warmup * updates_total,
            num_training_steps=updates_total)

        # create loss function
        entity_criterion = torch.nn.CrossEntropyLoss(reduction='none')
        compute_loss = SpanLoss(entity_criterion, model, optimizer, scheduler, args.max_grad_norm)

        # eval validation set
        if args.init_eval:
            self._eval(model, validation_dataset, input_reader, 0, updates_epoch)

        # train
        for epoch in range(args.epochs):
            # train epoch
            self._train_epoch(model, compute_loss, optimizer, train_dataset, updates_epoch, epoch)

            # eval validation sets
            if not args.final_eval or (epoch == args.epochs - 1):
                self._eval(model, validation_dataset, input_reader, epoch + 1, updates_epoch)

        # save final model
        extra = dict(epoch=args.epochs, updates_epoch=updates_epoch, epoch_iteration=0)
        global_iteration = args.epochs * updates_epoch
        self._save_model(
            self._save_path, model, self._tokenizer, global_iteration,
            optimizer=optimizer if self.args.save_optimizer else None, extra=extra,
            include_iteration=False, name='final_model')

        self._logger.info("Logged in: %s" % self._log_path)
        self._logger.info("Saved in: %s" % self._save_path)
        self._close_summary_writer()

    def eval(self, dataset_path: str, types_path: str, input_reader_cls: BaseInputReader):
        args = self.args
        dataset_label = 'test'

        self._logger.info("Dataset: %s" % dataset_path)
        self._logger.info("Model: %s" % args.model_type)

        # create log csv files
        self._init_eval_logging(dataset_label)

        # read datasets
        input_reader = input_reader_cls(types_path, self._tokenizer,
                                        max_span_size=args.max_span_size, logger=self._logger)
        input_reader.read({dataset_label: dataset_path})
        self._log_datasets(input_reader)

        # create model
        model_class = models.get_model(self.args.model_type)

        config = BertConfig.from_pretrained(self.args.model_path, cache_dir=self.args.cache_path)

        model = model_class.from_pretrained(
            self.args.model_path,
            config=config,
            # Span model parameters
            cls_token=self._tokenizer.convert_tokens_to_ids('[CLS]'),
            entity_types=input_reader.entity_type_count,
            max_pairs=self.args.max_pairs,
            prop_drop=self.args.prop_drop,
            size_embedding=self.args.size_embedding,
            freeze_transformer=self.args.freeze_transformer)

        model.to(self._device)

        # evaluate
        self._eval(model, input_reader.get_dataset(dataset_label), input_reader)

        self._logger.info("Logged in: %s" % self._log_path)
        self._close_summary_writer()

    def _train_epoch(
        self, model: torch.nn.Module, compute_loss: Loss,
        optimizer: Optimizer, dataset: Dataset, updates_epoch: int, epoch: int):

        self._logger.info("Train epoch: %s" % epoch)

        # create data loader
        dataset.switch_mode(Dataset.TRAIN_MODE)
        data_loader = DataLoader(
            dataset,
            batch_size=self.args.train_batch_size,
            shuffle=True,
            drop_last=True,
            num_workers=self.args.sampling_processes,
            collate_fn=sampling.collate_fn_padding)

        model.zero_grad()

        iteration = 0
        total = dataset.document_count // self.args.train_batch_size
        for batch in tqdm(data_loader, total=total, desc='Train epoch %s' % epoch):
            model.train()
            batch = util.to_device(batch, self._device)

            # forward step
            entity_logits = model(
                encodings=batch['encodings'],
                context_masks=batch['context_masks'],
                entity_masks=batch['entity_masks'],
                entity_sizes=batch['entity_sizes'])

            # compute loss and optimize parameters
            batch_loss = compute_loss.compute(
                entity_logits=entity_logits,
                entity_types=batch['entity_types'],
                entity_sample_masks=batch['entity_sample_masks'])

            # logging
            iteration += 1
            global_iteration = epoch * updates_epoch + iteration

            if global_iteration % self.args.train_log_iter == 0:
                self._log_train(optimizer, batch_loss, epoch, iteration, global_iteration, dataset.label)

        return iteration

    def _eval(
        self, model: torch.nn.Module, dataset: Dataset,
        input_reader: JsonInputReader,
        epoch: int = 0, updates_epoch: int = 0, iteration: int = 0):

        self._logger.info("Evaluate: %s" % dataset.label)

        if isinstance(model, DataParallel):
            # currently no multi GPU support during evaluation
            model = model.module

        # create evaluator
        evaluator = Evaluator(
            dataset, input_reader, self._tokenizer,
            self.args.no_overlapping, self._predictions_path,
            self._examples_path, self.args.example_count,
            epoch, dataset.label)

        # create data loader
        dataset.switch_mode(Dataset.EVAL_MODE)
        data_loader = DataLoader(
            dataset,
            batch_size=self.args.eval_batch_size,
            shuffle=False,
            drop_last=False,
            num_workers=self.args.sampling_processes,
            collate_fn=sampling.collate_fn_padding)

        with torch.no_grad():
            model.eval()

            # iterate batches
            total = math.ceil(dataset.document_count / self.args.eval_batch_size)
            for batch in tqdm(data_loader, total=total, desc='Evaluate epoch %s' % epoch):
                # move batch to selected device
                batch = util.to_device(batch, self._device)

                # run model (forward pass)
                result = model(
                    encodings=batch['encodings'],
                    context_masks=batch['context_masks'],
                    entity_masks=batch['entity_masks'],
                    entity_sizes=batch['entity_sizes'],
                    entity_spans=batch['entity_spans'],
                    entity_sample_masks=batch['entity_sample_masks'],
                    evaluate=True)
                entity_clf = result

                # evaluate batch
                evaluator.eval_batch(entity_clf, batch)

        global_iteration = epoch * updates_epoch + iteration
        ner_eval = evaluator.compute_scores()
        self._log_eval(*ner_eval, epoch, iteration, global_iteration, dataset.label)

        if self.args.store_predictions and not self.args.no_overlapping:
            evaluator.store_predictions()

        if self.args.store_examples:
            evaluator.store_examples(self.args.template_path)

    def _get_optimizer_params(self, model):
        param_optimizer = list(model.named_parameters())
        no_decay = ['bias', 'LayerNorm.bias', 'LayerNorm.weight']
        optimizer_params = [{
            'params': [
                p for n, p in param_optimizer
                if not any(nd in n for nd in no_decay)
            ],
            'weight_decay': self.args.weight_decay
        }, {
            'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)],
            'weight_decay': 0.0
        }]

        return optimizer_params

    def _log_train(self, optimizer: Optimizer, loss: float, epoch: int, iteration: int, global_iteration: int, label: str):
        # average loss
        avg_loss = loss / self.args.train_batch_size
        # get current learning rate
        lr = self._get_lr(optimizer)[0]

        # log to tensorboard
        self._log_tensorboard(label, 'loss', loss, global_iteration)
        self._log_tensorboard(label, 'loss_avg', avg_loss, global_iteration)
        self._log_tensorboard(label, 'lr', lr, global_iteration)

        # log to csv
        self._log_csv(label, 'loss', loss, epoch, iteration, global_iteration)
        self._log_csv(label, 'loss_avg', avg_loss, epoch, iteration, global_iteration)
        self._log_csv(label, 'lr', lr, epoch, iteration, global_iteration)

    def _log_eval(
        self, ner_prec_micro: float, ner_rec_micro: float, ner_f1_micro: float,
        ner_prec_macro: float, ner_rec_macro: float, ner_f1_macro: float,
        epoch: int, iteration: int, global_iteration: int, label: str):

        # log to tensorboard
        self._log_tensorboard(label, 'eval/ner_prec_micro', ner_prec_micro, global_iteration)
        self._log_tensorboard(label, 'eval/ner_recall_micro', ner_rec_micro, global_iteration)
        self._log_tensorboard(label, 'eval/ner_f1_micro', ner_f1_micro, global_iteration)
        self._log_tensorboard(label, 'eval/ner_prec_macro', ner_prec_macro, global_iteration)
        self._log_tensorboard(label, 'eval/ner_recall_macro', ner_rec_macro, global_iteration)
        self._log_tensorboard(label, 'eval/ner_f1_macro', ner_f1_macro, global_iteration)

        # log to csv
        self._log_csv(
            label, 'eval', ner_prec_micro, ner_rec_micro, ner_f1_micro,
            ner_prec_macro, ner_rec_macro, ner_f1_macro,
            epoch, iteration, global_iteration)

    def _log_datasets(self, input_reader):
        self._logger.info("Entity type count: %s" % input_reader.entity_type_count)

        self._logger.info("Entities:")
        for e in input_reader.entity_types.values():
            self._logger.info(e.verbose_name + '=' + str(e.index))

        for k, d in input_reader.datasets.items():
            self._logger.info('Dataset: %s' % k)
            self._logger.info("Document count: %s" % d.document_count)
            self._logger.info("Entity count: %s" % d.entity_count)

        self._logger.info("Context size: %s" % input_reader.context_size)

    def _init_train_logging(self, label):
        self._add_dataset_logging(
            label,
            data={
                'lr': ['lr', 'epoch', 'iteration', 'global_iteration'],
                'loss': ['loss', 'epoch', 'iteration', 'global_iteration'],
                'loss_avg':
                ['loss_avg', 'epoch', 'iteration', 'global_iteration']
            })

    def _init_eval_logging(self, label):
        self._add_dataset_logging(
            label,
            data={
                'eval': [
                    'ner_prec_micro', 'ner_rec_micro', 'ner_f1_micro',
                    'ner_prec_macro', 'ner_rec_macro', 'ner_f1_macro',
                    'epoch', 'iteration', 'global_iteration'
                ]
            })

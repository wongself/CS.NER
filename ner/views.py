# from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import JsonResponse

from configparser import ConfigParser
import nltk
from tqdm import tqdm

# import json
import datetime

from ner.model.logger import NERLogger
from ner.model.trainer import SpanTrainer


def index(request):
    return render(request, './index.html', {})


# @csrf_exempt
def entity_query(request):
    if request.is_ajax() and request.method == "POST":
        # Tokenize
        source = request.POST['source']
        jsentences = nltk.sent_tokenize(source)
        jtokens = [nltk.word_tokenize(jsentence) for jsentence in jsentences]

        # Parse document
        jdocument = []
        for jtoken in tqdm(jtokens, desc="Parse document"):
            doc = {"tokens": jtoken, "entities": []}
            jdocument.append(doc)
        logger.info('Document Parsed:\n%s' % jdocument)

        start_time = datetime.datetime.now()

        jpredictions = trainer.eval(jdoc=jdocument)
        logger.info('Predictions:\n%s' % jpredictions)

        end_time = datetime.datetime.now()
        logger.info('Predicting time : %d' % (end_time - start_time).seconds)

        # predictions_path = 'data/predictions/scierc_test.json'
        # with open(predictions_path, 'r') as f:
        #     jpredictions = json.load(f)
        #     return JsonResponse({'jpredictions': jpredictions})

        return JsonResponse({'jpredictions': jpredictions})
    return render(request, './index.html')


# Load logger
logger = NERLogger(debug=False)

# Parse configuration
cfg = ConfigParser()
configuration_path = 'configs/span_eval.conf'
cfg.read(configuration_path)
logger.info('Configuration Parsed: %s' % cfg.sections())

trainer = SpanTrainer(cfg, logger)

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import JsonResponse

from configparser import ConfigParser
import nltk
import os
from tqdm import tqdm

from ner.model.logger import NERLogger
from ner.model.reader import JsonInputReader
from ner.model.trainer import SpanTrainer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

        jpredictions = trainer.eval(jdoc=jdocument, input_reader_cls=JsonInputReader)

        # predictions_path = os.path.join(BASE_DIR, 'data', 'predictions', 'scierc_pred.json')
        # if not os.path.isfile(predictions_path):
        #     raise TypeError(predictions_path + " does not exist")
        # with open(predictions_path, 'r') as f:
        #     jpredictions = json.load(f)
        return JsonResponse({'jpredictions': jpredictions})
    return render(request, './index.html')


# Load logger
logger = NERLogger(debug=False)

# Parse configuration
cfg = ConfigParser()
configuration_path = os.path.join(BASE_DIR, 'configs', 'span_eval.conf')
cfg.read(configuration_path)
logger.info('Configuration Parsed: %s' % cfg.sections())

trainer = SpanTrainer(cfg, logger)

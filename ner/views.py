from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

from tqdm import tqdm
import json
import logging
import nltk
import os

from ner.model.logger import NERLogger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def index(request):
    return render(request, './index.html', {})


# @csrf_exempt
def entity_query(request):
    if request.is_ajax() and request.method == "POST":
        source = request.POST['source']
        jsentences = nltk.sent_tokenize(source)
        jtokens = [nltk.word_tokenize(jsentence) for jsentence in jsentences]

        jdocument = []
        for jtoken in tqdm(jtokens, desc="Parse document"):
            doc = {"tokens" : jtoken, "entities": []}
            jdocument.append(doc)
        logger.info('Document Parsed:\n%s' % jdocument)

        predictions_path = os.path.join(BASE_DIR, 'data', 'predictions',
                                        'scierc_pred.json')
        if not os.path.isfile(predictions_path):
            raise TypeError(predictions_path + " does not exist")
        with open(predictions_path, 'r') as f:
            jpredictions = json.load(f)
            return JsonResponse({'jpredictions': jpredictions})
    return render(request, './index.html')


logger = NERLogger(debug=False)
logger.info('logger ok')

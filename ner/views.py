from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

from tqdm import tqdm
import json
import time
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def index(request):
    return render(request, './index.html', {})


# @csrf_exempt
def entity_query(request):
    if request.is_ajax() and request.method == "POST":
        doc = request.POST['input']
        output = 'test ' + doc + ' test'
        predictions_path = os.path.join(BASE_DIR, 'data', 'predictions',
                                        'scierc_pred.json')
        if not os.path.isfile(predictions_path):
            raise TypeError(predictions_path + " does not exist")
        with open(predictions_path, 'r') as f:
            jpredictions = json.load(f)
            return JsonResponse({'jpredictions': jpredictions})
    return render(request, './index.html')

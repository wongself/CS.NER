from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import time

def index(request):
    return render(request, './index.html', {})

# @csrf_exempt
def entity_query(request):
    if request.is_ajax() and request.method == "POST":
        doc = request.POST['input']
        output = 'test ' + doc + ' test'
        time.sleep(1)
        return JsonResponse({'entity': output})
    return render(request, './index.html')

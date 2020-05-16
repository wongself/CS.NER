import jiagu
from django.http import JsonResponse

from ...views import loc_list, org_list, per_list


def entity_query(request):
    keyword = request.POST['keyword']
    output = 'test ' = keyword + ' test'

    return JsonResponse({'entity': output})
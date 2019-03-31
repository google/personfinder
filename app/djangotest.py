from django.http import HttpResponse


def get_debugging_response(request, label, repo_id):
     output = label
     output += '<br/>repo_id: %s' % (repo_id or 'None')
     output += '<br/>path: %s' % request.path
     output += '<br/>path_info: %s' % request.path_info
     output += '<br/>get_full_path(): %s' % request.get_full_path()
     output += ('<br/>build_absolute_uri(abc): %s' %
                request.build_absolute_uri('abc'))
     output += ('<br/>build_absolute_uri(/abc): %s' %
                request.build_absolute_uri('/abc'))
     return HttpResponse(output)


def djangotest(request, repo_id=None):
    return get_debugging_response(request, 'djangotest', repo_id)


def pf_djangotest(request, repo_id=None):
    return get_debugging_response(request, 'pf_djangotest', repo_id)

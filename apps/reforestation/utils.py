def paginer_liste(request, liste, param='page', page_size=20):
   
    try:
        page = int(request.query_params.get(param, 1))
    except (TypeError, ValueError):
        page = 1
    page = max(page, 1)

    total = len(liste)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        'count': total,
        'page': page,
        'page_size': page_size,
        'has_next': end < total,
        'has_previous': page > 1,
        'results': liste[start:end],
    }
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.exceptions import ParseError
from rest_framework.request import Request
from rest_framework.response import Response


class CustomOffsetPagination(LimitOffsetPagination):
    default_limit = 20
    
    def get_offset(self, request: Request, limit:int):
        try:
            page = int(request.query_params.get("page", 1))  
            if page < 1:
                raise ValueError("Page number must be greater than 0.")
            if limit < 1:
                raise ValueError("Limit must be greater than 0.")
            
        except ValueError as e:
            raise ParseError(str(e))
        
        return (page - 1) * limit
    
    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        try:
            limit = int(request.query_params.get("limit", self.default_limit))
        except ValueError:
            limit = self.default_limit
        
        offset = self.get_offset(request, limit)
        self.count = len(queryset) if isinstance(queryset, list) else queryset.count()
        self.offset = offset
        self.limit = limit
        
        if offset > self.count:
            return []

        return list(queryset[offset:offset + limit])
    
    def get_paginated_response(self, data, extra_data = None):
        """
        Modify the response to include extra metadata (e.g., pending/rejected counts).
        """
        response_data = {
            'count': self.count,
            'results': data
        }
        
        # Merge extra data (like pending and rejected counts)
        if extra_data:
            response_data.update(extra_data)

        return Response(response_data)
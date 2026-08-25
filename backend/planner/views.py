from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def health_check(request):
    """Health check endpoint to verify backend service status."""
    return Response({
        "status": "healthy",
        "service": "Spotter HOS Planner API",
        "version": "1.0.0"
    })

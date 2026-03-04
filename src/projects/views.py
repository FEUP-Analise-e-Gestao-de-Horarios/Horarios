from django.http import HttpRequest, HttpResponse
from django.views import View


class ProjectsView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return HttpResponse()

    def post(self, request: HttpRequest) -> HttpResponse:
        return HttpResponse()

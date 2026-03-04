import logging
import os
import sqlite3
import threading

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.models import Project
from src.ingestion.manager import IngestionManager
from src.parser.utils import validate_request_body
from src.projects.schemas import ParseProjectInput

logger = logging.getLogger(__name__)


class ProjectsView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return HttpResponse()

    def post(self, request: HttpRequest) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return JsonResponse({"error": "User is not authenticated"}, status=401)

        # -- Validate and extract input ----------------------------------------
        validated, err = validate_request_body(ParseProjectInput, request.body)
        if err:
            return err
        assert validated is not None

        project_name = validated.name
        project_url = validated.url

        try:
            Project(project=project_name, person=request.user).save()
            proj_id = Project.objects.values("id").get(project=project_name)["id"]
            path = "database/Project" + str(proj_id)
            os.mkdir(path)
            conn = sqlite3.connect(os.path.join(path, "general_database.db"))
            conn_original = sqlite3.connect(os.path.join(path, "initial_database.db"))
            with open("database/criar.sql") as f:
                script = f.read()
                conn.cursor().executescript(script)
                conn_original.cursor().executescript(script)
            conn.commit()
            conn.close()
        except FileExistsError:
            return JsonResponse(
                {"error": f"A project with the name '{project_name}' already exists"},
                status=400,
            )
        except Exception:
            return JsonResponse({"error": "Failed to create project"}, status=500)

        proj = Project.objects.get(project=project_name)
        manager = IngestionManager(
            project_url=project_url, path=path, proj_id=proj_id, proj=proj
        )

        def run() -> None:
            try:
                manager.run()
            except Exception:
                logger.exception("Unhandled exception in background parse thread")

        threading.Thread(target=run, daemon=True).start()
        return JsonResponse({}, status=200)

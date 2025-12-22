from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from apps.catalog.models import AccessRequest
from apps.catalog.services.template_from_request import create_template_from_request


class RequestMakeTemplateView(View):
    """
    POST desde el detalle de una solicitud:
    crea un AccessTemplate clonando todos los selection_sets.
    """

    def post(self, request: HttpRequest, request_id: int) -> HttpResponse:
        if not request.user.is_authenticated:
            raise PermissionDenied

        # Ajustá esto a tu política real (ej: groups IT).
        # Para no bloquearte ahora: staff.
        if not request.user.is_staff:
            raise PermissionDenied

        ar = get_object_or_404(AccessRequest, pk=request_id)

        name = (request.POST.get("template_name") or "").strip()
        department = (request.POST.get("department") or "").strip()
        role_name = (request.POST.get("role_name") or "").strip()
        notes = (request.POST.get("notes") or "").strip()

        try:
            template = create_template_from_request(
                access_request=ar,
                name=name,
                department=department,
                role_name=role_name,
                notes=notes,
                owner=request.user,
            )
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
            return redirect(reverse("catalog:request_detail", args=[ar.pk]))
        except Exception as e:
            messages.error(request, f"No se pudo crear el template: {e}")
            return redirect(reverse("catalog:request_detail", args=[ar.pk]))

        messages.success(request, f"Template creado: {template.name}")
        return redirect(reverse("catalog:request_detail", args=[ar.pk]))

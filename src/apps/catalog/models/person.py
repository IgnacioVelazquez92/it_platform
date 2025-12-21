# src/apps/catalog/models/person.py
from __future__ import annotations

from django.db import models


class RequestPersonData(models.Model):
    """
    Datos de la persona TAL COMO se cargaron en la solicitud (snapshot).

    Objetivo:
    - Capturar la información mínima necesaria para procesar una alta/modificación.
    - Mantener trazabilidad: si mañana cambia el email/teléfono en otro lado,
      esta solicitud conserva lo que se solicitó en ese momento.

    Importante:
    - NO incluye datos de soporte remoto (ej: AnyDesk). Eso pertenece al perfil IT,
      no al payload de la solicitud.
    """

    first_name = models.CharField("Nombre", max_length=80)
    last_name = models.CharField("Apellido", max_length=80)
    dni = models.CharField("DNI", max_length=32)

    email = models.EmailField("Email")
    mobile_phone = models.CharField("Celular", max_length=40)

    job_title = models.CharField("Puesto de trabajo", max_length=120)

    # Para empezar, lo guardamos como texto. Más adelante puede evolucionar a FK
    # a un modelo interno (Employee/Manager) si lo necesitás.
    direct_manager = models.CharField("Jefe directo", max_length=120)

    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Datos de persona (solicitud)"
        verbose_name_plural = "Datos de personas (solicitudes)"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["dni"]),
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.last_name}, {self.first_name} ({self.dni})"

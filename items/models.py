from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.conf import settings
from django.utils.html import strip_tags

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=512)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

#Para el historial de las simulaciones por usuario
class Simulacion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    monto = models.FloatField()
    meses = models.IntegerField()
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Simulación de {self.user.email} - {self.monto} en {self.meses} meses"
    
#Modelo para almacenar los precios reales
class PrecioActivo(models.Model):
    simbolo = models.CharField(max_length=20)   # ej: SPY, BTC
    nombre = models.CharField(max_length=50)    # ej: S&P 500, Bitcoin
    fecha = models.DateField()
    cierre = models.FloatField()

    class Meta:
        unique_together = ("simbolo", "fecha")
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.nombre} ({self.simbolo}) - {self.fecha}: {self.cierre}"
    
#Modelo para Tipo de Suscripcion
class Suscripcion(models.Model):
    TIPO_CHOICES = [
        ('gratis', 'Gratis'),
        ('premium', 'Premium'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='suscripcion')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='gratis')
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.get_tipo_display()}"


class Item(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} - {self.name}"
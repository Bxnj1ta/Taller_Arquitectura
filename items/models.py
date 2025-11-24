from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models, transaction
from django.conf import settings
from django.utils.html import strip_tags
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

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


from decimal import Decimal
from django.conf import settings
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()

class Wallet(models.Model):
    """
    Monedero/Wallet asociado a cada usuario.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"Wallet {self.user.username}: {self.balance}"

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    # Crea wallet automáticamente al crear un usuario
    if created:
        Wallet.objects.create(user=instance)


class Inversion(models.Model):
    """
    Modelo para rastrear inversiones activas de los usuarios.
    """
    TIPO_ACTIVO_CHOICES = [
        ('cdt', 'CDT Bancario'),
        ('sp500', 'S&P 500'),
        ('btc', 'Cripto (BTC)'),
        ('nft', 'NFTs'),
    ]
    
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inversiones')
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='inversiones')
    tipo_activo = models.CharField(max_length=10, choices=TIPO_ACTIVO_CHOICES)
    monto_invertido = models.DecimalField(max_digits=14, decimal_places=2)
    meses = models.IntegerField()
    valor_esperado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    ganancia_esperada = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    rentabilidad_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activa')
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    fecha_vencimiento = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_tipo_activo_display()} - ${self.monto_invertido}"
    
    def calcular_fecha_vencimiento(self):
        """Calcula la fecha de vencimiento basada en los meses"""
        from datetime import timedelta
        if self.meses and self.fecha_inicio:
            return self.fecha_inicio + timedelta(days=self.meses * 30)
        return None
    
    def save(self, *args, **kwargs):
        if not self.fecha_vencimiento:
            self.fecha_vencimiento = self.calcular_fecha_vencimiento()
        super().save(*args, **kwargs)
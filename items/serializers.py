from rest_framework import serializers
from .models import Simulacion

class SimulacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Simulacion
        fields = ['id', 'monto', 'meses', 'creado']  # No exponer el user directamente API3

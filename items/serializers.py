from rest_framework import serializers

from .models import Simulacion, Item

# Serializer seguro para Item
class ItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=150, allow_blank=False, trim_whitespace=True)
    description = serializers.CharField(allow_blank=True, trim_whitespace=True)

    def validate_name(self, value):
        # No permitir scripts ni etiquetas HTML
        import re
        if re.search(r'<.*?>', value):
            raise serializers.ValidationError("No se permiten etiquetas HTML en el nombre.")
        return value.strip()

    def validate_description(self, value):
        # Limitar longitud y evitar scripts
        if len(value) > 1000:
            raise serializers.ValidationError("Descripción demasiado larga.")
        if '<script' in value.lower():
            raise serializers.ValidationError("No se permiten scripts en la descripción.")
        return value.strip()

    class Meta:
        model = Item
        fields = ['id', 'name', 'description', 'created_at']


class SimulacionSerializer(serializers.ModelSerializer):
    monto = serializers.FloatField(min_value=0.01, max_value=100000000)
    meses = serializers.IntegerField(min_value=1, max_value=360)

    def validate_monto(self, value):
        # Sanitización extra: evitar valores NaN, inf, o strings
        if not isinstance(value, (float, int)) or not (0 < value <= 100000000):
            raise serializers.ValidationError("Monto inválido")
        return float(value)

    def validate_meses(self, value):
        if not isinstance(value, int) or not (0 < value <= 360):
            raise serializers.ValidationError("Meses inválidos")
        return int(value)

    class Meta:
        model = Simulacion
        fields = ['id', 'monto', 'meses', 'creado']  # No exponer el user directamente API3

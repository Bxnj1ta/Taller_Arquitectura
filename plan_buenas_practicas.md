# Plan de Ejecución para Buenas Prácticas y SAST

## 1. Inyección de Dependencias
- **Objetivo:** Mejorar la mantenibilidad y testabilidad del código desacoplando componentes.
- **Acciones:**
  - Identificar servicios, utilidades y recursos externos (por ejemplo, servicios en `items/services/`).
  - Refactorizar para que las dependencias se inyecten como argumentos en vez de instanciarse directamente dentro de las clases o funciones.
  - Usar patrones como el de "constructor injection" o "provider functions".
  - Documentar ejemplos de inyección en FastAPI y Django.

## 2. Sanitización de Datos
- **Objetivo:** Prevenir vulnerabilidades como XSS, SQL Injection y asegurar la integridad de los datos.
- **Acciones:**
  - Revisar puntos de entrada de datos: formularios, APIs, vistas.
  - Usar validadores de Django REST Framework y Pydantic (FastAPI) para limpiar y validar datos.
  - Aplicar escapes en plantillas HTML y sanitización en campos de texto.
  - Documentar ejemplos de sanitización en serializadores y vistas.

## 3. Integración de SAST (Bandit)
- **Objetivo:** Detectar vulnerabilidades de seguridad en el código fuente automáticamente.
- **Acciones:**
  - Instalar Bandit en el entorno de desarrollo:
    ```bash
    pip install bandit
    ```
  - Ejecutar Bandit sobre el código fuente principal:
    ```bash
    bandit -r items/ fastapi_service/ soa_crud/
    ```
  - Analizar el reporte generado y documentar los hallazgos.
  - Corregir vulnerabilidades críticas y volver a ejecutar Bandit.
  - Integrar Bandit en el flujo de CI/CD si es posible.

## 4. Documentación de Hallazgos
- **Objetivo:** Dejar registro de vulnerabilidades encontradas, acciones correctivas y buenas prácticas implementadas.
- **Acciones:**
  - Crear un archivo `SAST_report.md` con el resumen de hallazgos y acciones tomadas.
  - Documentar ejemplos de inyección de dependencias y sanitización en el código.
  - Actualizar el README con recomendaciones de seguridad y uso de Bandit.

---

## 5. Validación y Seguimiento
- **Objetivo:** Garantizar la mejora continua de la seguridad y calidad del código.
- **Acciones:**
  - Revisar periódicamente el código con Bandit y otras herramientas SAST.
  - Realizar code reviews enfocados en buenas prácticas de seguridad.
  - Mantener la documentación y ejemplos actualizados.

---

## 6. Endpoints CRUD seguros y buenas prácticas implementadas

### Endpoints CRUD para `Item` (Django)

- `POST   /api/items/create/`   → Crear ítem (valida y sanitiza datos)
- `GET    /api/items/`          → Listar ítems
- `PUT    /api/items/<pk>/update/` → Actualizar ítem (valida y sanitiza datos)
- `DELETE /api/items/<pk>/delete/` → Eliminar ítem

**Características de seguridad:**
- Validación y sanitización en modelo, serializer y vistas.
- Prevención de XSS y entradas maliciosas.
- Uso de decoradores `@login_required` y métodos HTTP seguros.
- Inyección de dependencias en servicios críticos (S3, Lambda, MarketService).

### FastAPI
- Cliente S3 inyectado como dependencia.
- Sanitización de nombre de archivo en descargas.

### Ejemplo de inyección de dependencias
```python
# LambdaService
lambda_service = LambdaService(client=mock_boto3_client)
# MarketService
market_service = MarketService(alpha_service, banrep_service)
# FastAPI S3
s3_client = get_s3_client(...)
```

### Ejemplo de sanitización
```python
# Modelo Item
self.name = strip_tags(self.name).strip()
# Serializer Item
if re.search(r'<.*?>', value):
  raise serializers.ValidationError("No se permiten etiquetas HTML")
```

---

**Nota:**
- Priorizar la corrección de vulnerabilidades de severidad alta.
- Fomentar la cultura de seguridad y buenas prácticas en el equipo de desarrollo.

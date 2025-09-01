# Reporte de Análisis SAST (Bandit)

## Ejecución de Bandit

Se ejecutó el siguiente comando para analizar el código fuente en busca de vulnerabilidades de seguridad:

```pwsh
& "C:/David Bedoya/David Bedoya/Estudio/Taller_CRUD/soa_crud/Scripts/python.exe" -m bandit -r items/ fastapi_service/ soa_crud/ -f markdown -o SAST_report.md
```

## Resultados

- El reporte detallado se encuentra en el archivo `SAST_report.md`.
- Si el comando falló, asegúrate de:
  - Tener Bandit instalado en el entorno virtual.
  - Ejecutar el comando desde la raíz del proyecto.
  - Usar la ruta completa del ejecutable de Python del entorno virtual.

## Recomendaciones

- Revisa el archivo `SAST_report.md` para identificar vulnerabilidades críticas.
- Prioriza la corrección de los hallazgos de severidad ALTA.
- Vuelve a ejecutar Bandit tras cada corrección relevante.
- Integra Bandit en el flujo de CI/CD para análisis automático.

---

**Nota:**
Si necesitas ayuda para interpretar el reporte o corregir vulnerabilidades específicas, consúltame con el fragmento relevante del reporte.

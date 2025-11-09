@echo off
chcp 65001 >nul
echo.
echo 🎯 INICIANDO PRUEBAS AUTOMÁTICAS - INVEST SIMULATOR
echo ==================================================
echo.

echo 📅 Fecha: %date% %time%
echo.

echo 1. 🔧 EJECUTANDO PRUEBAS UNITARIAS...
python manage.py test tests.test_unitario_mock --verbosity=1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ PRUEBAS UNITARIAS FALLARON
    goto :error
)
echo ✅ Pruebas unitarias PASARON
echo.

echo 2. 📊 EJECUTANDO PRUEBAS DE SERVICIO...
python manage.py test tests.test_market_service --verbosity=1
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  PRUEBAS DE SERVICIO TIENEN ERRORES (continuando...)
    REM No usar 'goto :error' para continuar con otras pruebas
)
echo 🔸 Pruebas de servicio completadas
echo.

echo 3. 🔗 EJECUTANDO PRUEBAS DE INTEGRACIÓN...
python manage.py test tests.test_integracion_completa --verbosity=1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ PRUEBAS DE INTEGRACIÓN FALLARON
    goto :error
)
echo ✅ Pruebas de integración PASARON
echo.

echo 4. 🌐 EJECUTANDO PRUEBAS FUNCIONALES...
python manage.py test tests.test_funcional_paginas --verbosity=1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ PRUEBAS FUNCIONALES FALLARON
    goto :error
)
echo ✅ Pruebas funcionales PASARON
echo.

echo 5. 📈 EJECUTANDO TODAS LAS PRUEBAS JUNTAS...
python manage.py test tests --verbosity=1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ ALGUNAS PRUEBAS FALLARON
    goto :error
)
echo.

echo ==================================================
echo ✅✅✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE ✅✅✅
echo 📊 Resumen: 100%% de pruebas exitosas
echo 🚀 Tu simulador de inversiones está listo para producción
echo.
pause
goto :fin

:error
echo.
echo ==================================================
echo ❌❌❌ ALGUNAS PRUEBAS FALLARON ❌❌❌
echo 🔧 Revisa los errores arriba y corrige el código
echo.
pause
exit /b 1

:fin
exit /b 0
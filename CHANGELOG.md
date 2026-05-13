# Changelog

## 1.4.0 - 2026-05-13

- Agrega perfiles persistentes de conexion MariaDB.
- Permite guardar, cargar y eliminar multiples conexiones desde la interfaz.
- Guarda host, puerto, usuario y clave en configuracion local de usuario.
- Documenta ubicacion del archivo de conexiones.

## 1.3.0 - 2026-05-12

- Reorganiza conexion MariaDB y seleccion de bases en un unico panel compacto.
- Reduce margenes y espaciados para dar mas altura util a las listas de tablas.
- Mantiene el registro en la parte inferior con menor impacto sobre el area principal.
- Agrega `build.sh` y `requirements-dev.txt` para generar binario Linux con PyInstaller.
- Documenta el proceso de build en Linux.

## 1.2.0 - 2026-05-12

- Cambia la seleccion de tema de `QComboBox` a `QToolButton` con estado.
- Agrega iconos a las acciones principales de conexion, actualizacion, carga, orden, migracion y borrado.
- Actualiza documentacion para reflejar el nuevo control de tema.

## 1.1.0 - 2026-05-12

- Agrega numero de version visible en titulo y barra de estado.
- Agrega selector de tema claro/oscuro.
- Aplica estilo moderno con QSS para formularios, botones, listas, registro, progreso y barra de estado.
- Documenta uso, instalacion, configuracion, SQL ejecutado y permisos en `README.md`.
- Agrega este changelog.

## 1.0.0 - 2026-05-12

- Crea la primera version de la app Qt6.
- Permite conectar a MariaDB y listar bases visibles.
- Permite seleccionar DB origen y destino.
- Permite cargar tablas del proyecto seleccionado.
- Permite seleccionar y ordenar tablas para migracion.
- Ejecuta `CREATE OR REPLACE TABLE destino.tabla AS SELECT * FROM origen.tabla`.
- Permite borrar manualmente tablas del destino.
- Agrega indicador de carga, registro de tareas y timeouts para consultas de metadata.

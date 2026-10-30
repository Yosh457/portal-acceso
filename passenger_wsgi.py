# passenger_wsgi.py
"""
Punto de entrada WSGI para desplegar PortalAcceso mediante
Phusion Passenger en cPanel.

Passenger utiliza la variable 'application' para ejecutar
la aplicación Flask.

Este archivo mantiene la arquitectura Application Factory
definida en app.py.
"""

import os
import sys

# Agregar el directorio raíz del proyecto al PATH de Python.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Importar la función de fábrica de Flask.
from app import create_app

# Crear la instancia WSGI utilizada por Passenger.
application = create_app()
# AssistMe

Tickets es un proyecto diseñado para gestionar entradas a eventos, generar qr y validarlos.

## Requisitos

- Python 3.8 o superior
- pip

## Instalación

1. **Clona el repositorio:**

   git clone https://github.com/sebastiansorich/TiketsHalloween.git
   cd AssistMe
   

2. **Crea un entorno virtual:**

    python -m venv venv

3. **Activa el entorno virtual:**

    En Windows:

        .\venv\Scripts\activate
    En macOS/Linux:

        source venv/bin/activate
        
4. **Instala las dependencias:**

    pip install -r requirements.txt

## Configuración

1. **Configura las variables de entorno:**

Crea un archivo .env en la raíz del proyecto y añade las siguientes variables:

env:

DATABASE_URI=mysql+pymysql://root:Passw0rd@localhost/probandoflask


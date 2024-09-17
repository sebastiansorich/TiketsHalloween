# Tickets Halloween

Tickets es un proyecto diseñado para gestionar entradas a eventos, generar QR y validarlos.

## Requisitos

- Python 3.8 o superior
- pip

## Instalación

1. **Clona el repositorio:**

    ```bash
    git clone https://github.com/sebastiansorich/TiketsHalloween.git
    cd TiketsHalloween
    ```

2. **Crea un entorno virtual:**

    ```bash
    python -m venv venv
    ```

3. **Activa el entorno virtual:**

    En Windows:

    ```bash
    .\venv\Scripts\activate
    ```

    En macOS/Linux:

    ```bash
    source venv/bin/activate
    ```
        
4. **Instala las dependencias:**

    ```bash
    pip install -r requirements.txt
    ```

## Configuración

1. **Configura las variables de entorno:**

Crea un archivo `.env` en la raíz del proyecto y añade las siguientes variables:

env:

DATABASE_URI=mysql+pymysql://root:Passw0rd@localhost/NombreDeTuBaseDeDatos


#run.py
from src import create_app
#prueba
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000)
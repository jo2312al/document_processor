from src.api.aplicacion import crear_aplicacion

app = crear_aplicacion()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

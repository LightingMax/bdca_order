import os
from app import create_app

app = create_app()

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=12345, debug=True)

if __name__ == '__main__':
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", "12306"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)

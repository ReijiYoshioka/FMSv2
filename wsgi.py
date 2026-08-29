from dotenv import load_dotenv

load_dotenv()

from fmsv2 import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run()

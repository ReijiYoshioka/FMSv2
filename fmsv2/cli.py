import click
from flask import current_app

from .db import init_db


@click.command("init-db")
def init_db_command():
    """DBスキーマと初期マスタデータを投入する（本番初回セットアップ用）。"""
    init_db(current_app.config["DATABASE_PATH"])
    click.echo("Initialized the database.")


@click.command("verify-gemini")
def verify_gemini_command():
    """FMS_GEMINI_API_KEY/FMS_GEMINI_MODELが実際に使えるか確認する（開発用）。"""
    api_key = current_app.config["GEMINI_API_KEY"]
    model = current_app.config["GEMINI_MODEL"]
    if not api_key:
        click.echo("FMS_GEMINI_API_KEY が設定されていない。.env を確認する。")
        return

    from google import genai

    client = genai.Client(api_key=api_key)

    click.echo(f"設定されているモデル: {model}")
    click.echo("--- 'flash-lite' を含む利用可能なモデル ---")
    matches = []
    try:
        for m in client.models.list():
            if "flash-lite" in m.name:
                click.echo(m.name)
                matches.append(m.name)
    except Exception as e:
        click.echo(f"モデル一覧の取得に失敗した: {e}")
        return

    exact = model in matches or f"models/{model}" in matches
    click.echo(f"設定値と完全一致するモデルが一覧にある: {exact}")
    if not exact and matches:
        click.echo(f"候補: {matches}")

    click.echo("--- 実際に生成呼び出しを試す ---")
    try:
        prompt = "こんにちは、と一言だけ返して。"
        resp = client.models.generate_content(model=model, contents=prompt)
        click.echo(f"OK: {resp.text.strip()}")
    except Exception as e:
        click.echo(f"NG: {e}")


def init_app(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(verify_gemini_command)

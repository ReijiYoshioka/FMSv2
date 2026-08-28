import click
from flask import current_app

from .db import init_db


@click.command("init-db")
def init_db_command():
    """DBスキーマと初期マスタデータを投入する（本番初回セットアップ用）。"""
    init_db(current_app.config["DATABASE_PATH"])
    click.echo("Initialized the database.")


def init_app(app):
    app.cli.add_command(init_db_command)

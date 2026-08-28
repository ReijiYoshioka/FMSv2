def lenient_int(value):
    """クエリ文字列の数値を寛容にintへ変換する（"12.5"のような小数文字列は
    truncateして12にする。旧PHP版のis_numeric+(int)キャストと同じ方針）。
    数値でなければNoneを返し、フィルタ自体を無効化する。
    """
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

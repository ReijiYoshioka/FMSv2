# float64が誤差無く表現できる整数の範囲(2^53)より十分小さく、個人の家計簿としても
# 現実的に十分な上限。これを超える値はint(float(value))で静かに精度が崩れうるため拒否する。
MAX_AMOUNT = 1_000_000_000_000


def to_valid_amount(value):
    """0以上MAX_AMOUNT以下の整数に正規化する。不正な値・範囲外はNoneを返す
    （NaN/Infはint(float(...))が例外を投げるのでここで自然に弾かれる）。"""
    try:
        amount = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return None
    if amount < 0 or amount > MAX_AMOUNT:
        return None
    return amount


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

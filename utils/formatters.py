"""
숫자 → 한글 단위 변환 유틸리티
"""


def format_currency_ko(amount: int) -> str:
    """금액을 억/만/메소 단위 한글로 변환.

    Examples:
        >>> format_currency_ko(123_456_789)
        '1억 2345만 6789메소'
        >>> format_currency_ko(0)
        '0 메소'
    """
    if amount == 0:
        return "0 메소"

    parts = []
    if amount >= 100_000_000:
        parts.append(f"{amount // 100_000_000}억")
        amount %= 100_000_000
    if amount >= 10_000:
        parts.append(f"{amount // 10_000}만")
        amount %= 10_000
    parts.append(f"{amount}메소" if amount > 0 else "메소")

    return " ".join(parts)


def format_power_ko(value) -> str:
    """전투력 숫자를 억/만 단위 한글로 변환.

    Examples:
        >>> format_power_ko(1_234_567_890)
        '12억3456만7890'
        >>> format_power_ko(None)
        '0'
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "0"

    if value >= 100_000_000:
        eok = value // 100_000_000
        remainder = value % 100_000_000
        man = remainder // 10_000
        rest = remainder % 10_000
        result = f"{eok}억"
        if man:
            result += f"{man}만"
        if rest:
            result += str(rest)
        return result

    if value >= 10_000:
        man = value // 10_000
        rest = value % 10_000
        return f"{man}만" + (str(rest) if rest else "")

    return str(value)

"""
유틸리티 함수 모음
"""


def format_price(price: float) -> str:
    """
    가격을 적절한 소수점 자리수로 포맷팅

    Args:
        price: 가격 (원)

    Returns:
        포맷팅된 가격 문자열

    Examples:
        >>> format_price(50000)
        '50,000원'
        >>> format_price(500.5)
        '500.5원'
        >>> format_price(31.9)
        '31.90원'
        >>> format_price(12.8)
        '12.80원'
        >>> format_price(5.123)
        '5.123원'
    """
    if price >= 1000:
        return f"{price:,.0f}원"
    elif price >= 100:
        return f"{price:,.1f}원"
    elif price >= 10:
        return f"{price:,.2f}원"
    else:
        return f"{price:,.3f}원"

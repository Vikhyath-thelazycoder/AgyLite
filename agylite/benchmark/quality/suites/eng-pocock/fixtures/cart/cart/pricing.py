def total(items, discount_percent=0):
    """Cart total in cents after a percentage discount code."""
    subtotal = sum(price * qty for price, qty in items)
    return round(subtotal * (100 - discount_percent) / 100)

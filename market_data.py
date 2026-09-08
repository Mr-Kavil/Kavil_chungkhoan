from vnstock import Vnstock

def get_realtime_prices(symbols: list[str]) -> dict[str, float]:
    """
    Nhận vào danh sách mã cổ phiếu ['HPG', 'SSI']
    Trả về dict dạng {'HPG': 28500.0, 'SSI': 32100.0}
    """
    prices = {}
    if not symbols:
        return prices
    
    try:
        # Khởi tạo client vnstock
        stock = Vnstock()
        # Lấy bảng giá giá trị thực (price board)
        df = stock.stock(symbol=symbols[0], source='VPS').trading.price_board(symbols)
        
        # Trích xuất giá khớp lệnh gần nhất (Match Price)
        # Giá từ API thường trả về theo đơn vị nghìn VNĐ (VD: 28.5 -> 28500)
        for _, row in df.iterrows():
            sym = row['Mã CP']
            match_price = float(row['Giá Khớp']) * 1000  # Đổi ra VNĐ
            prices[sym] = match_price
    except Exception as e:
        print(f"Lỗi lấy giá realtime: {e}")
        # Giá fallback nếu lỗi mạng/API
        for sym in symbols:
            prices[sym] = 0.0
            
    return prices
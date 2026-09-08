import streamlit as st
from datetime import datetime, timedelta

# Thử import từ vnstock (hỗ trợ cả phiên bản cũ và mới)
try:
    from vnstock import Vnstock
    VNSTOCK_AVAILABLE = True
except ImportError:
    try:
        from vnstock import stock_historical_data
        VNSTOCK_AVAILABLE = True
    except ImportError:
        VNSTOCK_AVAILABLE = False


@st.cache_data(ttl=180)  # Lưu bộ nhớ đệm 3 phút để tránh rate limit
def get_current_price(symbol: str) -> tuple[float, bool]:
    """
    Lấy giá giao dịch mới nhất của mã cổ phiếu.
    Returns:
        (price, is_live): Trả về giá (VNĐ) và trạng thái True (giá thật) / False (giá fallback).
    """
    symbol = symbol.strip().upper()
    
    if VNSTOCK_AVAILABLE:
        try:
            # Lấy dữ liệu 7 ngày gần nhất để đảm bảo luôn có ngày giao dịch gần nhất
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Thử lấy bằng SDK Vnstock mới (Vnstock3)
            try:
                stock = Vnstock().stock(symbol=symbol, source='VND')
                df = stock.quote.history(start=start_date, end=end_date, interval='1D')
            except Exception:
                # Fallback sang hàm lấy dữ liệu lịch sử chuẩn
                from vnstock import stock_historical_data
                df = stock_historical_data(
                    symbol=symbol, 
                    start_date=start_date, 
                    end_date=end_date,
                    resolution='1D',
                    type='stock'
                )

            if df is not None and not df.empty:
                # Cột giá đóng cửa trong vnstock thường là 'close'
                latest_price = df.iloc[-1]['close']
                
                # Một số nguồn trả về đơn vị Nghìn VNĐ (VD: 28.5 thay vì 28500)
                if latest_price < 1000:
                    latest_price = latest_price * 1000
                    
                return float(latest_price), True
        except Exception:
            pass  # Nếu lỗi kết nối API thì chuyển xuống phần Fallback bên dưới

    # -----------------------------------------------------------------
    # CƠ CHẾ CHỜ GIẢ LẬP (FALLBACK) KHI NGHẼN MẠNG/NGOÀI GIỜ GIAO DỊCH
    # -----------------------------------------------------------------
    fallback_database = {
        "HPG": 28500.0,
        "SSI": 32500.0,
        "VNM": 68000.0,
        "TCB": 23500.0,
        "FPT": 125000.0,
        "MBB": 24000.0,
        "VIC": 42000.0,
        "VHM": 40000.0
    }
    
    # Nếu mã không có trong danh sách fallback, trả về giá mặc định 20,000 VNĐ
    price = fallback_database.get(symbol, 20000.0)
    return price, False


def get_multiple_prices(symbols: list[str]) -> tuple[dict[str, float], bool]:
    """
    Lấy giá cho một danh sách mã cổ phiếu.
    Returns:
        (price_dict, all_live): Dictionary {Mã: Giá} và trạng thái kết nối.
    """
    prices = {}
    all_live = True
    
    for sym in set(symbols):
        if sym:
            price, is_live = get_current_price(sym)
            prices[sym] = price
            if not is_live:
                all_live = False
                
    return prices, all_live
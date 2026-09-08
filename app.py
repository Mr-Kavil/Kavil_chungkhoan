import streamlit as st
import pandas as pd
from vnstock import Vnstock

# --- MODULE 1: LẤY GIÁ REALTIME (ĐÃ SỬA LỖI) ---
def get_realtime_prices(symbols: list[str]) -> dict[str, float]:
    prices = {}
    if not symbols:
        return prices
    
    try:
        stock = Vnstock()
        # Thử lấy bảng giá từ nguồn TCBS hoặc VPS với cú pháp mới
        df = stock.stock(symbol=symbols[0], source='TCBS').trading.price_board(symbols)
        
        # Kiểm tra tên cột trả về để lấy đúng giá khớp lệnh
        price_col = None
        for col in ['Giá Khớp', 'matchPrice', 'closePrice', 'lastPrice']:
            if col in df.columns:
                price_col = col
                break
                
        symbol_col = 'Mã CP' if 'Mã CP' in df.columns else 'ticker'
        
        if price_col:
            for _, row in df.iterrows():
                sym = str(row[symbol_col]).upper()
                p = float(row[price_col])
                # Quy đổi về VNĐ nếu giá trả về ở dạng nghìn VNĐ (VD: 28.5 -> 28500)
                prices[sym] = p * 1000 if p < 1000 else p
    except Exception as e:
        st.warning(f"Không thể kết nối lấy giá trực tuyến (Đang áp dụng giá tham chiếu giả lập để test)")
        # Fallback: Nếu API bị giới hạn/lỗi, gán giá thị trường tạm thời để tính toán
        mock_prices = {'HPG': 28500.0, 'SSI': 32500.0, 'VNM': 67000.0, 'TCB': 35000.0}
        for sym in symbols:
            prices[sym] = mock_prices.get(sym, 25000.0)
            
    return prices

# --- MODULE 2: QUẢN LÝ DANH MỤC ---
class PortfolioManager:
    def __init__(self):
        self.transactions = []

    def add_transaction(self, symbol: str, trans_type: str, quantity: int, price: float, fee_pct=0.001, tax_pct=0.001):
        self.transactions.append({
            'symbol': symbol.upper(),
            'type': trans_type.upper(),
            'quantity': quantity,
            'price': price,
            'fee': price * quantity * fee_pct,
            'tax': (price * quantity * tax_pct) if trans_type.upper() == 'SELL' else 0.0
        })

    def calculate_holdings(self, current_prices: dict[str, float]):
        holdings = {}
        for t in self.transactions:
            sym = t['symbol']
            if sym not in holdings:
                holdings[sym] = {'qty': 0, 'total_cost': 0.0, 'realized_pnl': 0.0}

            if t['type'] == 'BUY':
                cost = (t['price'] * t['quantity']) + t['fee']
                holdings[sym]['qty'] += t['quantity']
                holdings[sym]['total_cost'] += cost
            elif t['type'] == 'SELL' and holdings[sym]['qty'] > 0:
                avg_cost = holdings[sym]['total_cost'] / holdings[sym]['qty']
                revenue = (t['price'] * t['quantity']) - t['fee'] - t['tax']
                cost_of_sold = avg_cost * t['quantity']
                holdings[sym]['realized_pnl'] += (revenue - cost_of_sold)
                holdings[sym]['qty'] -= t['quantity']
                holdings[sym]['total_cost'] -= cost_of_sold

        results = []
        for sym, data in holdings.items():
            if data['qty'] > 0:
                avg_price = data['total_cost'] / data['qty']
                market_price = current_prices.get(sym, avg_price)
                market_value = market_price * data['qty']
                unrealized_pnl = market_value - data['total_cost']
                pnl_pct = (unrealized_pnl / data['total_cost']) * 100 if data['total_cost'] > 0 else 0

                results.append({
                    'Mã CP': sym,
                    'Số lượng': data['qty'],
                    'Giá vốn TB': round(avg_price, 0),
                    'Giá hiện tại': market_price,
                    'Giá trị hiện tại': market_value,
                    'Lãi/Lỗ (VNĐ)': round(unrealized_pnl, 0),
                    'Lãi/Lỗ (%)': round(pnl_pct, 2),
                    'Lãi đã chốt': round(data['realized_pnl'], 0)
                })
        return pd.DataFrame(results)

# --- MODULE 3: GIAO DIỆN STREAMLIT ---
st.set_page_config(page_title="Sổ Tay Chứng Khoán VN", layout="wide")
st.title("📈 Phần Mềm Theo Dõi Danh Mục Chứng Khoán VN")

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = PortfolioManager()
    st.session_state.portfolio.add_transaction('HPG', 'BUY', 1000, 26000)
    st.session_state.portfolio.add_transaction('SSI', 'BUY', 500, 31000)

st.sidebar.header("➕ Nhập Giao Dịch")
with st.sidebar.form("trans_form", clear_on_submit=True):
    symbol = st.text_input("Mã cổ phiếu (VD: HPG)").upper()
    trans_type = st.selectbox("Loại giao dịch", ["BUY", "SELL"])
    quantity = st.number_input("Số lượng", min_value=100, step=100)
    price = st.number_input("Giá giao dịch (VNĐ)", min_value=1000.0, step=500.0)
    
    submitted = st.form_submit_button("Lưu Giao Dịch")
    if submitted and symbol:
        st.session_state.portfolio.add_transaction(symbol, trans_type, quantity, price)
        st.sidebar.success(f"Đã thêm {trans_type} {quantity} {symbol}")

# Chuyển lịch sử giao dịch sang DataFrame
transactions_df = pd.DataFrame(st.session_state.portfolio.transactions)
active_symbols = list(set(t['symbol'] for t in st.session_state.portfolio.transactions)) if not transactions_df.empty else []

# Lấy giá realtime từ Vnstock
current_prices = get_realtime_prices(active_symbols)
df_holdings = st.session_state.portfolio.calculate_holdings(current_prices)

if not df_holdings.empty:
    total_invested = df_holdings['Số lượng'] * df_holdings['Giá vốn TB']
    total_market_val = df_holdings['Giá trị hiện tại'].sum()
    total_pnl = df_holdings['Lãi/Lỗ (VNĐ)'].sum()
    total_pnl_pct = (total_pnl / total_invested.sum()) * 100 if total_invested.sum() > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng Giá Trị Danh Mục", f"{total_market_val:,.0f} VNĐ")
    col2.metric("Tổng Lời / Lỗ Tạm Tính", f"{total_pnl:,.0f} VNĐ", delta=f"{total_pnl_pct:.2f}%")
    col3.metric("Tổng Lãi Đã Chốt", f"{df_holdings['Lãi đã chốt'].sum():,.0f} VNĐ")

    st.markdown("---")
    st.subheader("📋 Danh Mục Nắm Giữ")
    
    def color_pnl(val):
        color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
        return f'color: {color}'

    st.dataframe(
        df_holdings.style.map(color_pnl, subset=['Lãi/Lỗ (VNĐ)', 'Lãi/Lỗ (%)']),
        use_container_width=True
    )
else:
    st.info("Chưa có cổ phiếu nào trong danh mục.")

if not transactions_df.empty:
    with st.expander("📄 Xem Lịch Sử Giao Dịch"):
        st.table(transactions_df)
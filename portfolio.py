import pandas as pd

class PortfolioManager:
    def __init__(self):
        # Lưu nhật ký mọi lệnh Mua/Bán
        self.transactions = []

    def add_transaction(self, symbol: str, trans_type: str, quantity: int, price: float, fee_pct=0.001, tax_pct=0.001):
        """
        Nhập giao dịch mới
        trans_type: 'BUY' hoặc 'SELL'
        price: Giá giao dịch VNĐ (VD: 25000)
        """
        self.transactions.append({
            'symbol': symbol.upper(),
            'type': trans_type.upper(),
            'quantity': quantity,
            'price': price,
            'fee': price * quantity * fee_pct,
            'tax': (price * quantity * tax_pct) if trans_type.upper() == 'SELL' else 0.0
        })

    def calculate_holdings(self, current_prices: dict[str, float]):
        """
        Tính toán chi tiết danh mục đang nắm giữ và Lời/Lỗ
        """
        holdings = {}

        for t in self.transactions:
            sym = t['symbol']
            if sym not in holdings:
                holdings[sym] = {'qty': 0, 'total_cost': 0.0, 'realized_pnl': 0.0}

            if t['type'] == 'BUY':
                # Tiền vốn = Giá mua * SL + Phí mua
                cost = (t['price'] * t['quantity']) + t['fee']
                holdings[sym]['qty'] += t['quantity']
                holdings[sym]['total_cost'] += cost

            elif t['type'] == 'SELL':
                if holdings[sym]['qty'] > 0:
                    # Tính giá vốn trung bình hiện tại
                    avg_cost = holdings[sym]['total_cost'] / holdings[sym]['qty']
                    
                    # Lời/Lỗ đã thực hiện (Realized PnL)
                    revenue = (t['price'] * t['quantity']) - t['fee'] - t['tax']
                    cost_of_sold = avg_cost * t['quantity']
                    holdings[sym]['realized_pnl'] += (revenue - cost_of_sold)
                    
                    # Giảm số lượng và giá trị vốn còn lại
                    holdings[sym]['qty'] -= t['quantity']
                    holdings[sym]['total_cost'] -= cost_of_sold

        # Tổng hợp danh mục & tính Lời/Lỗ chưa thực hiện (Unrealized PnL)
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
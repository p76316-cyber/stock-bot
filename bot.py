import requests
import pandas as pd
import datetime
import math

# ===== 填入你的資料 =====
finmind_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMi0yNCAyMjoxODowMSIsInVzZXJfaWQiOiJZdW1hIiwiaXAiOiIyMTguMTg3Ljg1LjE0NyIsImV4cCI6MTc3MjU0NzQ4MX0.6cJ0XndjWOtZBGEj_TKxV4Bl7faAzKNNkoS0LXyRKBg"
telegram_token = "8740674108:AAFJzj5los4EQo15EIMZ-L8xmY_lB-DcHVc"
chat_id = "8786555019"

base_url = "https://api.finmindtrade.com/api/v4/data"

today = datetime.date.today()
start_date = (today - datetime.timedelta(days=20)).strftime("%Y-%m-%d")

# ===== Telegram 發送函數 =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": msg}
    requests.post(url, data=payload)

# ===== 保命機制（簡化版大盤判斷）=====
index_param = {
    "dataset": "TaiwanStockPrice",
    "data_id": "TAIEX",
    "start_date": start_date,
    "token": finmind_token,
}
index_data = requests.get(base_url, params=index_param).json()
df_index = pd.DataFrame(index_data["data"])

if len(df_index) < 2:
    send_telegram("⚠ 無法取得大盤資料")
    exit()

y_index = df_index.iloc[-2]
index_change = (y_index["close"] - y_index["open"]) / y_index["open"] * 100

if index_change < -1.5:
    send_telegram("⚠ 今日盤勢偏弱\n建議觀望休息")
    exit()

# ===== 取得股票清單 =====
stock_param = {
    "dataset": "TaiwanStockInfo",
    "token": finmind_token,
}
stock_data = requests.get(base_url, params=stock_param).json()
stocks = pd.DataFrame(stock_data["data"])
stocks = stocks[stocks["industry_category"] != "ETF"]

candidates = []

for stock_id in stocks["stock_id"].unique()[:120]:

    try:
        price_param = {
            "dataset": "TaiwanStockPrice",
            "data_id": stock_id,
            "start_date": start_date,
            "token": finmind_token,
        }
        price_data = requests.get(base_url, params=price_param).json()
        df_price = pd.DataFrame(price_data["data"])

        if len(df_price) < 10:
            continue

        y = df_price.iloc[-2]
        avg20 = df_price["Trading_Volume"].tail(20).mean()
        amplitude = (y["max"] - y["min"]) / y["close"] * 100

        inst_param = {
            "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
            "data_id": stock_id,
            "start_date": start_date,
            "token": finmind_token,
        }
        inst_data = requests.get(base_url, params=inst_param).json()
        df_inst = pd.DataFrame(inst_data["data"])

        if len(df_inst) < 2:
            continue

        df_group = df_inst.groupby("date")["buy"].sum()

        if (
            df_group.iloc[-1] > 0 and
            df_group.iloc[-2] > 0 and
            y["Trading_Volume"] > avg20 * 2 and
            amplitude > 7 and
            y["close"] < 150
        ):
            candidates.append((stock_id, y["close"]))

    except:
        continue

if not candidates:
    send_telegram("今日無符合條件標的")
    exit()

# ===== 只選最強一檔 =====
stock_id, close_price = candidates[0]

entry = round(close_price * 1.008, 2)
stop_loss = round(entry * 0.98, 2)
take_profit = round(entry * 1.038, 2)

# ===== 自動算張數 =====
capital = 120000
shares = math.floor(capital / (entry * 1000))

risk = (entry - stop_loss) * shares * 1000
reward = (take_profit - entry) * shares * 1000

message = f"""
📈 09:00 進攻股

{stock_id}
建議進場：{entry}
買：{shares} 張
停損：{stop_loss}
停利：{take_profit}

風險：約 -{int(risk)}
預期：約 +{int(reward)}
"""

send_telegram(message)

import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import time
import re
import csv
import os
from datetime import datetime, timedelta, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter


# ============================================================
# CONFIGURATION
# ============================================================

CMC_URL = "https://coinmarketcap.com/all/views/all/"
TOP_COINS = 10
REFRESH_SECONDS = 30

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE_DIR, "reports")
CSV_FILE = os.path.join(REPORT_DIR, "crypto_history.csv")

os.makedirs(REPORT_DIR, exist_ok=True)


# ============================================================
# GLOBAL DATA
# ============================================================

driver = None
coins_data = []
history_data = []
alert_data = []

last_update = None
next_update_seconds = REFRESH_SECONDS
scraping = False


# ============================================================
# COLORS
# ============================================================

BG = "#071426"
PANEL = "#0D1D36"
PANEL2 = "#102442"
BORDER = "#203A61"

WHITE = "#F5F7FA"
MUTED = "#8EA4C4"

PURPLE = "#6C4BF4"
PURPLE_DARK = "#5134D8"

GREEN = "#19E68C"
RED = "#FF5575"
YELLOW = "#FFC857"
BLUE = "#4EA1FF"

ROW_BG = "#0B1A31"
ROW_SELECTED = "#17345D"


# ============================================================
# ROOT
# ============================================================

root = tk.Tk()

root.title(
    "Crypto Pulse - Real-Time Cryptocurrency Market Intelligence"
)

root.geometry("1500x900")
root.minsize(1200, 750)
root.configure(bg=BG)


# ============================================================
# STYLE
# ============================================================

style = ttk.Style()

try:
    style.theme_use("clam")
except Exception:
    pass

style.configure(
    "Treeview",
    background=ROW_BG,
    fieldbackground=ROW_BG,
    foreground=WHITE,
    rowheight=38,
    borderwidth=0,
    font=("Segoe UI", 10)
)

style.configure(
    "Treeview.Heading",
    background=PANEL2,
    foreground=WHITE,
    font=("Segoe UI", 10, "bold"),
    relief="flat"
)

style.map(
    "Treeview",
    background=[
        ("selected", ROW_SELECTED)
    ],
    foreground=[
        ("selected", WHITE)
    ]
)

style.configure(
    "TCombobox",
    fieldbackground=WHITE,
    background=WHITE,
    foreground="#111111"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(text):
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def parse_number(text):
    if not text:
        return 0.0

    text = str(text).strip()

    negative = (
        "-" in text or
        "−" in text
    )

    text = (
        text
        .replace("$", "")
        .replace(",", "")
        .replace("%", "")
        .replace("−", "")
        .strip()
    )

    multiplier = 1

    if text.upper().endswith("T"):
        multiplier = 1_000_000_000_000
        text = text[:-1]

    elif text.upper().endswith("B"):
        multiplier = 1_000_000_000
        text = text[:-1]

    elif text.upper().endswith("M"):
        multiplier = 1_000_000
        text = text[:-1]

    elif text.upper().endswith("K"):
        multiplier = 1_000
        text = text[:-1]

    try:
        value = float(text) * multiplier

        if negative:
            value = -abs(value)

        return value

    except Exception:
        return 0.0


def format_price(value):
    if value >= 1000:
        return f"${value:,.2f}"

    if value >= 1:
        return f"${value:,.2f}"

    return f"${value:.4f}"


def format_large(value):

    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    if value >= 1_000:
        return f"${value / 1_000:.2f}K"

    return f"${value:.2f}"


def format_change(value):

    if value > 0:
        return f"+{value:.2f}%"

    return f"{value:.2f}%"


def change_color(value):

    if value > 0:
        return GREEN

    if value < 0:
        return RED

    return MUTED


# ============================================================
# CSV
# ============================================================

def save_to_csv(coins):

    if not coins:
        return

    file_exists = os.path.exists(CSV_FILE)

    with open(
        CSV_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        if not file_exists:

            writer.writerow([
                "Timestamp",
                "Rank",
                "Name",
                "Price",
                "1h Change",
                "24h Change",
                "7d Change",
                "Market Cap",
                "Volume"
            ])

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        for coin in coins:

            writer.writerow([
                timestamp,
                coin["rank"],
                coin["name"],
                coin["price"],
                coin["change_1h"],
                coin["change_24h"],
                coin["change_7d"],
                coin["market_cap"],
                coin["volume"]
            ])


# ============================================================
# SELENIUM DRIVER
# ============================================================

def create_driver():

    options = Options()

    options.add_argument(
        "--start-maximized"
    )

    options.add_argument(
        "--disable-notifications"
    )

    options.add_argument(
        "--disable-popup-blocking"
    )

    options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )

    options.add_experimental_option(
        "excludeSwitches",
        ["enable-automation"]
    )

    options.add_experimental_option(
        "useAutomationExtension",
        False
    )

    options.add_argument(
        "--user-agent=Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    )

    return webdriver.Chrome(
        options=options
    )


# ============================================================
# COIN NAME
# ============================================================

def extract_name(row):

    selectors = [
        "p.sc-65e7b2d7-0",
        "p[class*='coin-item-name']",
        "a[href*='/currencies/'] p",
        "a[href*='/currencies/']"
    ]

    for selector in selectors:

        try:

            elements = row.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for element in elements:

                text = clean_text(
                    element.text
                )

                if not text:
                    continue

                # Remove common symbol prefix
                known_symbols = [
                    "BTC",
                    "ETH",
                    "USDT",
                    "BNB",
                    "XRP",
                    "USDC",
                    "SOL",
                    "TRX",
                    "HYPE",
                    "ZEC"
                ]

                parts = text.split()

                if len(parts) >= 2:
                    return " ".join(parts[1:])

                for symbol in known_symbols:

                    if text.upper().startswith(symbol):

                        cleaned = text[
                            len(symbol):
                        ].strip()

                        if cleaned:
                            return cleaned

                return text

        except Exception:
            continue

    return ""


# ============================================================
# SCRAPE TOP 10
# ============================================================

def scrape_top_10():

    global driver

    try:

        if driver is None:
            driver = create_driver()

        driver.get(CMC_URL)

        wait = WebDriverWait(
            driver,
            30
        )

        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table")
            )
        )

        time.sleep(5)

        # Scroll to force lazy loading
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

        time.sleep(3)

        driver.execute_script(
            "window.scrollTo(0, 0);"
        )

        time.sleep(2)

        rows = driver.find_elements(
            By.CSS_SELECTOR,
            "table tbody tr"
        )

        print(
            f"Rows found: {len(rows)}"
        )

        result = []

        for row in rows:

            if len(result) >= TOP_COINS:
                break

            try:

                cells = row.find_elements(
                    By.TAG_NAME,
                    "td"
                )

                if len(cells) < 7:
                    continue

                texts = [
                    clean_text(cell.text)
                    for cell in cells
                ]

                row_text = clean_text(
                    row.text
                )

                # ------------------------------------------------
                # RANK
                # ------------------------------------------------

                rank = None

                for text in texts[:3]:

                    match = re.search(
                        r"^\s*(\d+)",
                        text
                    )

                    if match:

                        number = int(
                            match.group(1)
                        )

                        if 1 <= number <= 10:

                            rank = number
                            break

                if rank is None:
                    continue

                # ------------------------------------------------
                # NAME
                # ------------------------------------------------

                name = extract_name(row)

                if not name:
                    continue

                # Clean concatenated symbol
                replacements = [
                    ("BTCBitcoin", "Bitcoin"),
                    ("ETHEthereum", "Ethereum"),
                    ("USDTTether USDt", "Tether USDt"),
                    ("BNBBNB", "BNB"),
                    ("XRPXRP", "XRP"),
                    ("USDUSD Coin", "USDC"),
                    ("SOLSolana", "Solana"),
                    ("TRXTRON", "TRON"),
                    ("HYPEHyperliquid", "Hyperliquid"),
                    ("ZECZcash", "Zcash")
                ]

                for old, new in replacements:

                    if old.lower() in name.lower():

                        name = new

                # ------------------------------------------------
                # PRICE
                # ------------------------------------------------

                price = 0.0

                # CMC current table generally has
                # Rank / Name / Symbol / Market Cap / Price...
                # Search all cells carefully.

                dollar_candidates = []

                for text in texts:

                    matches = re.findall(
                        r"\$[\d,.]+(?:\.\d+)?(?:[KMBT])?",
                        text,
                        re.IGNORECASE
                    )

                    for match in matches:

                        value = parse_number(
                            match
                        )

                        if value > 0:
                            dollar_candidates.append(
                                value
                            )

                # Find price using values which do not
                # have large-number suffix.
                for value in dollar_candidates:

                    if value < 10_000_000:

                        price = value
                        break

                # Fallback: direct cell parsing
                if price <= 0:

                    for cell in cells:

                        text = clean_text(
                            cell.text
                        )

                        if (
                            "$" in text and
                            not re.search(
                                r"[KMBT]\s*$",
                                text,
                                re.IGNORECASE
                            )
                        ):

                            value = parse_number(
                                text
                            )

                            if value > 0:

                                price = value
                                break

                if price <= 0:
                    continue

                # ------------------------------------------------
                # PERCENTAGES
                # ------------------------------------------------

                percentages = re.findall(
                    r"[+\-−]?\d+(?:\.\d+)?%",
                    row_text
                )

                changes = []

                for item in percentages:

                    changes.append(
                        parse_number(item)
                    )

                change_1h = (
                    changes[0]
                    if len(changes) >= 1
                    else 0.0
                )

                change_24h = (
                    changes[1]
                    if len(changes) >= 2
                    else 0.0
                )

                change_7d = (
                    changes[2]
                    if len(changes) >= 3
                    else 0.0
                )

                # ------------------------------------------------
                # MARKET CAP + VOLUME
                # ------------------------------------------------

                market_cap = 0.0
                volume = 0.0

                money_values = []

                for text in texts:

                    matches = re.findall(
                        r"\$[\d,.]+(?:\.\d+)?(?:[KMBT])?",
                        text,
                        re.IGNORECASE
                    )

                    for item in matches:

                        value = parse_number(
                            item
                        )

                        if value > 0:

                            money_values.append(
                                value
                            )

                # Remove price
                remaining = [
                    value
                    for value in money_values
                    if abs(value - price) > 0.01
                ]

                if remaining:

                    # Largest value = market cap
                    market_cap = max(
                        remaining
                    )

                    remaining_volume = [
                        value
                        for value in remaining
                        if value != market_cap
                    ]

                    if remaining_volume:

                        volume = max(
                            remaining_volume
                        )

                coin = {
                    "rank": rank,
                    "name": name,
                    "price": price,
                    "change_1h": change_1h,
                    "change_24h": change_24h,
                    "change_7d": change_7d,
                    "market_cap": market_cap,
                    "volume": volume
                }

                result.append(
                    coin
                )

                print(
                    f"Found #{rank}: "
                    f"{name} | "
                    f"{format_price(price)}"
                )

            except Exception as error:

                print(
                    "Row skipped:",
                    error
                )

                continue

        # Remove duplicates
        unique = {}

        for coin in result:
            unique[
                coin["rank"]
            ] = coin

        result = list(
            unique.values()
        )

        result.sort(
            key=lambda x: x["rank"]
        )

        return result[:10]

    except Exception as error:

        print(
            "SCRAPE ERROR:",
            error
        )

        return []


# ============================================================
# HEADER
# ============================================================

header = tk.Frame(
    root,
    bg=BG
)

header.pack(
    fill="x",
    padx=35,
    pady=(25, 10)
)


# Logo
logo = tk.Label(
    header,
    text="₿",
    font=("Segoe UI", 32, "bold"),
    bg=PURPLE,
    fg=WHITE,
    width=3,
    height=1
)

logo.pack(
    side="left"
)


title_frame = tk.Frame(
    header,
    bg=BG
)

title_frame.pack(
    side="left",
    padx=15
)

title_label = tk.Label(
    title_frame,
    text="CRYPTO PULSE",
    font=("Segoe UI", 28, "bold"),
    bg=BG,
    fg=WHITE
)

title_label.pack(
    anchor="w"
)

subtitle = tk.Label(
    title_frame,
    text="REAL-TIME CRYPTOCURRENCY MARKET INTELLIGENCE",
    font=("Segoe UI", 9),
    bg=BG,
    fg=MUTED
)

subtitle.pack(
    anchor="w"
)


live_label = tk.Label(
    header,
    text="● LIVE MARKET",
    font=("Segoe UI", 10, "bold"),
    bg="#062A20",
    fg=GREEN,
    padx=18,
    pady=10
)

live_label.pack(
    side="right",
    pady=8
)


# ============================================================
# BUTTON BAR
# ============================================================

button_bar = tk.Frame(
    root,
    bg=BG
)

button_bar.pack(
    fill="x",
    padx=35,
    pady=10
)


def make_button(
    parent,
    text,
    command,
    width=12
):

    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=PURPLE,
        fg=WHITE,
        activebackground=PURPLE_DARK,
        activeforeground=WHITE,
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        bd=0,
        padx=15,
        pady=9,
        width=width,
        cursor="hand2"
    )


refresh_button = make_button(
    button_bar,
    "↻  Refresh",
    lambda: start_scrape()
)

refresh_button.pack(
    side="left",
    padx=(0, 10)
)


def show_history():

    if not os.path.exists(
        CSV_FILE
    ):

        messagebox.showinfo(
            "History",
            "No history available yet."
        )

        return

    history_window = tk.Toplevel(
        root
    )

    history_window.title(
        "Crypto Pulse - History"
    )

    history_window.geometry(
        "1100x650"
    )

    history_window.configure(
        bg=BG
    )

    tree = ttk.Treeview(
        history_window,
        columns=(
            "time",
            "rank",
            "name",
            "price",
            "change"
        ),
        show="headings"
    )

    headings = {
        "time": "Timestamp",
        "rank": "Rank",
        "name": "Asset",
        "price": "Price",
        "change": "24H Change"
    }

    for key, value in headings.items():

        tree.heading(
            key,
            text=value
        )

    tree.column(
        "time",
        width=180
    )

    tree.column(
        "rank",
        width=70
    )

    tree.column(
        "name",
        width=220
    )

    tree.column(
        "price",
        width=180
    )

    tree.column(
        "change",
        width=150
    )

    tree.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=20
    )

    try:

        with open(
            CSV_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(
                file
            )

            rows = list(
                reader
            )

            for row in rows[-500:]:

                tree.insert(
                    "",
                    "end",
                    values=(
                        row.get(
                            "Timestamp",
                            ""
                        ),
                        row.get(
                            "Rank",
                            ""
                        ),
                        row.get(
                            "Name",
                            ""
                        ),
                        row.get(
                            "Price",
                            ""
                        ),
                        row.get(
                            "24h Change",
                            ""
                        )
                    )
                )

    except Exception as error:

        messagebox.showerror(
            "History Error",
            str(error)
        )


history_button = make_button(
    button_bar,
    "◉  History",
    show_history
)

history_button.pack(
    side="left",
    padx=5
)


def open_csv():

    if not os.path.exists(
        CSV_FILE
    ):

        messagebox.showinfo(
            "CSV",
            "CSV file will be created after first update."
        )

        return

    try:

        os.startfile(
            CSV_FILE
        )

    except Exception:

        messagebox.showinfo(
            "CSV Location",
            CSV_FILE
        )


csv_button = make_button(
    button_bar,
    "▣  CSV",
    open_csv
)

csv_button.pack(
    side="left",
    padx=5
)


def show_alerts():

    if not alert_data:

        messagebox.showinfo(
            "Alerts",
            "No active price alerts."
        )

        return

    text = ""

    for alert in alert_data:

        text += (
            f"{alert['name']} "
            f"{alert['condition']} "
            f"${alert['target']:.2f}\n"
        )

    messagebox.showinfo(
        "Active Alerts",
        text
    )


alerts_button = make_button(
    button_bar,
    "♧  Alerts",
    show_alerts
)

alerts_button.pack(
    side="left",
    padx=5
)


status_label = tk.Label(
    button_bar,
    text="Waiting for market data...",
    bg=BG,
    fg=MUTED,
    font=("Segoe UI", 9)
)

status_label.pack(
    side="right"
)


# ============================================================
# STAT CARDS
# ============================================================

stats_frame = tk.Frame(
    root,
    bg=BG
)

stats_frame.pack(
    fill="x",
    padx=35,
    pady=10
)


stat_cards = {}


def create_stat_card(
    title,
    key
):

    frame = tk.Frame(
        stats_frame,
        bg=PANEL,
        highlightbackground=BORDER,
        highlightthickness=1
    )

    frame.pack(
        side="left",
        fill="both",
        expand=True,
        padx=5
    )

    tk.Label(
        frame,
        text=title,
        bg=PANEL,
        fg=MUTED,
        font=("Segoe UI", 9, "bold")
    ).pack(
        anchor="w",
        padx=18,
        pady=(15, 5)
    )

    value = tk.Label(
        frame,
        text="0",
        bg=PANEL,
        fg=GREEN,
        font=("Segoe UI", 24, "bold")
    )

    value.pack(
        anchor="w",
        padx=18
    )

    sub = tk.Label(
        frame,
        text="Waiting for data",
        bg=PANEL,
        fg=MUTED,
        font=("Segoe UI", 8)
    )

    sub.pack(
        anchor="w",
        padx=18,
        pady=(0, 15)
    )

    stat_cards[key] = {
        "value": value,
        "sub": sub
    }


create_stat_card(
    "TOTAL ASSETS",
    "total"
)

create_stat_card(
    "24H GAINERS",
    "gainers"
)

create_stat_card(
    "24H LOSERS",
    "losers"
)

create_stat_card(
    "24H NO CHANGE",
    "same"
)

create_stat_card(
    "AVG 24H CHANGE",
    "average"
)


# ============================================================
# CONTROL PANELS
# ============================================================

controls = tk.Frame(
    root,
    bg=BG
)

controls.pack(
    fill="x",
    padx=35,
    pady=10
)


# ============================================================
# FILTER PANEL
# ============================================================

filter_panel = tk.Frame(
    controls,
    bg=PANEL,
    highlightbackground=BORDER,
    highlightthickness=1
)

filter_panel.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(0, 5)
)

tk.Label(
    filter_panel,
    text="🔎 Custom Market Filter",
    bg=PANEL,
    fg=WHITE,
    font=("Segoe UI", 10, "bold")
).pack(
    anchor="w",
    padx=15,
    pady=10
)


filter_inputs = tk.Frame(
    filter_panel,
    bg=PANEL
)

filter_inputs.pack(
    fill="x",
    padx=15,
    pady=(0, 12)
)


min_price_entry = tk.Entry(
    filter_inputs,
    bg="#09172B",
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    width=12
)

min_price_entry.pack(
    side="left",
    padx=3
)

min_price_entry.insert(
    0,
    ""
)

max_price_entry = tk.Entry(
    filter_inputs,
    bg="#09172B",
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    width=12
)

max_price_entry.pack(
    side="left",
    padx=3
)


min_change_entry = tk.Entry(
    filter_inputs,
    bg="#09172B",
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    width=12
)

min_change_entry.pack(
    side="left",
    padx=3
)


def apply_filter():

    filtered = []

    try:
        min_price = (
            float(
                min_price_entry.get()
            )
            if min_price_entry.get()
            else None
        )

        max_price = (
            float(
                max_price_entry.get()
            )
            if max_price_entry.get()
            else None
        )

        min_change = (
            float(
                min_change_entry.get()
            )
            if min_change_entry.get()
            else None
        )

    except ValueError:

        messagebox.showerror(
            "Invalid Filter",
            "Please enter valid numbers."
        )

        return

    for coin in coins_data:

        if (
            min_price is not None and
            coin["price"] < min_price
        ):
            continue

        if (
            max_price is not None and
            coin["price"] > max_price
        ):
            continue

        if (
            min_change is not None and
            coin["change_24h"] < min_change
        ):
            continue

        filtered.append(
            coin
        )

    update_table(
        filtered
    )


filter_button = make_button(
    filter_inputs,
    "Filter",
    apply_filter,
    8
)

filter_button.pack(
    side="left",
    padx=5
)


# ============================================================
# COMPARE PANEL
# ============================================================

compare_panel = tk.Frame(
    controls,
    bg=PANEL,
    highlightbackground=BORDER,
    highlightthickness=1
)

compare_panel.pack(
    side="left",
    fill="both",
    expand=True,
    padx=5
)

tk.Label(
    compare_panel,
    text="⚖ Compare Cryptocurrency",
    bg=PANEL,
    fg=WHITE,
    font=("Segoe UI", 10, "bold")
).pack(
    anchor="w",
    padx=15,
    pady=10
)


compare_inputs = tk.Frame(
    compare_panel,
    bg=PANEL
)

compare_inputs.pack(
    fill="x",
    padx=15,
    pady=(0, 12)
)


coin1_combo = ttk.Combobox(
    compare_inputs,
    state="readonly",
    width=15
)

coin1_combo.pack(
    side="left",
    padx=3
)


coin2_combo = ttk.Combobox(
    compare_inputs,
    state="readonly",
    width=15
)

coin2_combo.pack(
    side="left",
    padx=3
)


def compare_coins():

    name1 = coin1_combo.get()
    name2 = coin2_combo.get()

    if not name1 or not name2:

        messagebox.showwarning(
            "Compare",
            "Select two cryptocurrencies."
        )

        return

    if name1 == name2:

        messagebox.showwarning(
            "Compare",
            "Select two different cryptocurrencies."
        )

        return

    c1 = next(
        (
            x for x in coins_data
            if x["name"] == name1
        ),
        None
    )

    c2 = next(
        (
            x for x in coins_data
            if x["name"] == name2
        ),
        None
    )

    if not c1 or not c2:
        return

    message = (
        f"{c1['name']}\n"
        f"Price: {format_price(c1['price'])}\n"
        f"24H: {format_change(c1['change_24h'])}\n"
        f"7D: {format_change(c1['change_7d'])}\n"
        f"Market Cap: {format_large(c1['market_cap'])}\n\n"
        f"{c2['name']}\n"
        f"Price: {format_price(c2['price'])}\n"
        f"24H: {format_change(c2['change_24h'])}\n"
        f"7D: {format_change(c2['change_7d'])}\n"
        f"Market Cap: {format_large(c2['market_cap'])}"
    )

    messagebox.showinfo(
        "Crypto Comparison",
        message
    )


compare_button = make_button(
    compare_inputs,
    "Compare",
    compare_coins,
    9
)

compare_button.pack(
    side="left",
    padx=5
)


# ============================================================
# ALERT PANEL
# ============================================================

alert_panel = tk.Frame(
    controls,
    bg=PANEL,
    highlightbackground=BORDER,
    highlightthickness=1
)

alert_panel.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(5, 0)
)

tk.Label(
    alert_panel,
    text="🔔 Create Price Alert",
    bg=PANEL,
    fg=WHITE,
    font=("Segoe UI", 10, "bold")
).pack(
    anchor="w",
    padx=15,
    pady=10
)


alert_inputs = tk.Frame(
    alert_panel,
    bg=PANEL
)

alert_inputs.pack(
    fill="x",
    padx=15,
    pady=(0, 12)
)


alert_coin_combo = ttk.Combobox(
    alert_inputs,
    state="readonly",
    width=14
)

alert_coin_combo.pack(
    side="left",
    padx=3
)


condition_combo = ttk.Combobox(
    alert_inputs,
    values=[
        "Above",
        "Below"
    ],
    state="readonly",
    width=9
)

condition_combo.set(
    "Above"
)

condition_combo.pack(
    side="left",
    padx=3
)


alert_price_entry = tk.Entry(
    alert_inputs,
    bg="#09172B",
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    width=12
)

alert_price_entry.pack(
    side="left",
    padx=3
)


def create_alert():

    name = alert_coin_combo.get()
    condition = condition_combo.get()

    try:

        target = float(
            alert_price_entry.get()
        )

    except ValueError:

        messagebox.showerror(
            "Alert",
            "Enter a valid target price."
        )

        return

    if not name:

        messagebox.showwarning(
            "Alert",
            "Select a cryptocurrency."
        )

        return

    alert_data.append({
        "name": name,
        "condition": condition,
        "target": target
    })

    messagebox.showinfo(
        "Alert Created",
        f"Alert created for {name}."
    )

    alert_price_entry.delete(
        0,
        "end"
    )


alert_button = make_button(
    alert_inputs,
    "Set Alert",
    create_alert,
    9
)

alert_button.pack(
    side="left",
    padx=5
)


# ============================================================
# TABLE SECTION
# ============================================================

table_container = tk.Frame(
    root,
    bg=PANEL,
    highlightbackground=BORDER,
    highlightthickness=1
)

table_container.pack(
    fill="x",
    padx=35,
    pady=10
)


table_header = tk.Frame(
    table_container,
    bg=PANEL
)

table_header.pack(
    fill="x"
)


tk.Label(
    table_header,
    text="🏆  Top 10 Market Assets",
    bg=PANEL,
    fg=WHITE,
    font=("Segoe UI", 13, "bold")
).pack(
    side="left",
    padx=18,
    pady=12
)


# Top 10 asset search
top10_search_frame = tk.Frame(
    table_header,
    bg=PANEL
)
top10_search_frame.pack(
    side="right",
    padx=8,
    pady=7
)

top10_search_entry = tk.Entry(
    top10_search_frame,
    bg="#09172B",
    fg=MUTED,
    insertbackground=WHITE,
    relief="flat",
    width=20,
    font=("Segoe UI", 9)
)
top10_search_entry.pack(
    side="left",
    padx=4,
    ipady=6
)
top10_search_entry.insert(0, "Search coin...")

def clear_top10_placeholder(event=None):
    if top10_search_entry.get() == "Search coin...":
        top10_search_entry.delete(0, "end")
        top10_search_entry.config(fg=WHITE)

def restore_top10_placeholder(event=None):
    if not top10_search_entry.get().strip():
        top10_search_entry.insert(0, "Search coin...")
        top10_search_entry.config(fg=MUTED)

top10_search_entry.bind("<FocusIn>", clear_top10_placeholder)
top10_search_entry.bind("<FocusOut>", restore_top10_placeholder)

# Keep the full live data separate from the displayed search result.
def show_top10_search_results():
    search_text = top10_search_entry.get().strip().lower()

    if not search_text or search_text == "search coin...":
        update_table(coins_data)
        return

    matches = [
        coin for coin in coins_data
        if search_text in coin["name"].lower()
    ]

    update_table(matches)

    if not matches:
        messagebox.showinfo(
            "Coin Search",
            "Coin not found in the Top 10 Market Assets."
        )

top10_search_button = make_button(
    top10_search_frame,
    "🔍 Search",
    show_top10_search_results,
    9
)
top10_search_button.pack(
    side="left",
    padx=4
)

top10_search_entry.bind(
    "<Return>",
    lambda event: show_top10_search_results()
)

tk.Label(
    table_header,
    text="LIVE",
    bg="#17345D",
    fg=BLUE,
    font=("Segoe UI", 8, "bold"),
    padx=8,
    pady=4
).pack(
    side="right",
    padx=18
)


tree = ttk.Treeview(
    table_container,
    columns=(
        "rank",
        "asset",
        "price",
        "change24",
        "change7",
        "marketcap",
        "volume"
    ),
    show="headings",
    height=10
)


columns = {
    "rank": ("RANK", 80),
    "asset": ("ASSET", 260),
    "price": ("PRICE", 190),
    "change24": ("24H CHANGE", 170),
    "change7": ("7D CHANGE", 170),
    "marketcap": ("MARKET CAP", 210),
    "volume": ("VOLUME", 190)
}


for column, (
    heading,
    width
) in columns.items():

    tree.heading(
        column,
        text=heading
    )

    tree.column(
        column,
        width=width,
        anchor="center"
    )


tree.pack(
    fill="x",
    padx=12,
    pady=(0, 12)
)


tree.tag_configure(
    "positive",
    foreground=GREEN
)

tree.tag_configure(
    "negative",
    foreground=RED
)

tree.tag_configure(
    "neutral",
    foreground=WHITE
)


# ============================================================
# GRAPH SECTION
# ============================================================

def open_graph_window():
    """Open the coin search + price history graph in a dedicated window."""
    if not coins_data:
        messagebox.showinfo(
            "Graph",
            "Market data is not loaded yet. Please refresh first."
        )
        return

    graph_window = tk.Toplevel(root)
    graph_window.title("Crypto Pulse - Price History")
    graph_window.geometry("1100x650")
    graph_window.minsize(850, 500)
    graph_window.configure(bg=BG)

    graph_container = tk.Frame(
        graph_window,
        bg=PANEL,
        highlightbackground=BORDER,
        highlightthickness=1
    )
    graph_container.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=20
    )

    graph_header = tk.Frame(
        graph_container,
        bg=PANEL
    )
    graph_header.pack(fill="x")

    tk.Label(
        graph_header,
        text="📈  Price History",
        bg=PANEL,
        fg=WHITE,
        font=("Segoe UI", 15, "bold")
    ).pack(
        side="left",
        padx=18,
        pady=14
    )

    graph_controls = tk.Frame(
        graph_header,
        bg=PANEL
    )
    graph_controls.pack(
        side="right",
        padx=15,
        pady=8
    )

    search_var = tk.StringVar()

    graph_search_entry = tk.Entry(
        graph_controls,
        textvariable=search_var,
        bg="#09172B",
        fg=WHITE,
        insertbackground=WHITE,
        relief="flat",
        width=20,
        font=("Segoe UI", 10)
    )
    graph_search_entry.pack(
        side="left",
        padx=5,
        ipady=7
    )

    # Real placeholder: the placeholder text is never treated as search input.
    graph_search_entry.insert(0, "Search coin...")
    graph_search_entry.config(fg=MUTED)

    def clear_placeholder(event=None):
        if graph_search_entry.get() == "Search coin...":
            graph_search_entry.delete(0, "end")
            graph_search_entry.config(fg=WHITE)

    def restore_placeholder(event=None):
        if not graph_search_entry.get().strip():
            graph_search_entry.insert(0, "Search coin...")
            graph_search_entry.config(fg=MUTED)

    graph_search_entry.bind("<FocusIn>", clear_placeholder)
    graph_search_entry.bind("<FocusOut>", restore_placeholder)

    graph_coin_combo = ttk.Combobox(
        graph_controls,
        state="readonly",
        width=20
    )
    graph_coin_combo.pack(
        side="left",
        padx=5
    )

    names = [coin["name"] for coin in coins_data]
    graph_coin_combo["values"] = names
    if names:
        graph_coin_combo.set(names[0])

    graph_area = tk.Frame(
        graph_container,
        bg=WHITE
    )
    graph_area.pack(
        fill="both",
        expand=True,
        padx=12,
        pady=(0, 12)
    )

    def generate_graph():
        selected = graph_coin_combo.get().strip()

        if not selected:
            messagebox.showwarning(
                "Graph",
                "Select a cryptocurrency first.",
                parent=graph_window
            )
            return

        coin_history = [
            item for item in history_data
            if item["name"] == selected
        ]

        if not coin_history:
            messagebox.showinfo(
                "Graph",
                "No history available for this coin yet.\n"
                "The graph will be available after a market update.",
                parent=graph_window
            )
            return

        # Keep every coin completely independent.
        coin_history = sorted(
            coin_history,
            key=lambda item: item["timestamp"]
        )

        # Remove invalid/old market-cap-sized records from the selected
        # coin's price series. This prevents one bad CSV value from ruining
        # the scale of the whole graph.
        current_price = next(
            (coin["price"] for coin in coins_data
             if coin["name"] == selected),
            None
        )

        if current_price and current_price > 0:
            max_reasonable = max(current_price * 100, 10_000_000)
            min_reasonable = current_price / 1000
            coin_history = [
                item for item in coin_history
                if isinstance(item.get("price"), (int, float))
                and min_reasonable <= item["price"] <= max_reasonable
            ]

        if not coin_history:
            messagebox.showinfo(
                "Graph",
                f"No valid price history available for {selected}.",
                parent=graph_window
            )
            return

        for widget in graph_area.winfo_children():
            widget.destroy()

        prices = [float(item["price"]) for item in coin_history]
        times = [item["timestamp"] for item in coin_history]
        x_values = list(range(1, len(prices) + 1))

        figure = plt.Figure(figsize=(10.5, 5.2), dpi=100)
        figure.patch.set_facecolor("#FFFFFF")
        axis = figure.add_subplot(111)
        axis.set_facecolor("#FFFFFF")

        # Clean professional line: clear markers + strong line + subtle fill.
        axis.plot(
            x_values,
            prices,
            marker="o",
            markersize=5,
            linewidth=2.6,
            markeredgewidth=0.8,
            zorder=3
        )
        if len(prices) > 1:
            axis.fill_between(x_values, prices, alpha=0.10, zorder=1)

        # Give every coin its own sensible Y-axis range.
        p_min = min(prices)
        p_max = max(prices)
        spread = p_max - p_min

        if spread == 0:
            pad = max(abs(p_max) * 0.001, 0.0001)
        else:
            pad = spread * 0.18

        axis.set_ylim(p_min - pad, p_max + pad)

        # Price formatting adapts to the coin's price size.
        if p_max < 1:
            decimals = 6
        elif p_max < 100:
            decimals = 4
        else:
            decimals = 2

        axis.yaxis.set_major_formatter(
            FuncFormatter(lambda value, pos: f"${value:,.{decimals}f}")
        )

        # Avoid the crowded timestamp problem when many 30-second updates exist.
        max_labels = 8
        step = max(1, (len(times) - 1) // (max_labels - 1)) if len(times) > max_labels else 1
        label_indexes = list(range(0, len(times), step))
        if len(times) > 1 and label_indexes[-1] != len(times) - 1:
            label_indexes.append(len(times) - 1)

        axis.set_xticks([x_values[i] for i in label_indexes])
        axis.set_xticklabels(
            [times[i].strftime("%H:%M:%S") for i in label_indexes],
            rotation=25,
            ha="right"
        )

        axis.set_title(
            f"{selected} Price History",
            fontsize=16,
            fontweight="bold",
            pad=14
        )
        axis.set_xlabel("Update Time", fontsize=10)
        axis.set_ylabel(f"{selected} Price (USD)", fontsize=10)
        axis.grid(True, linestyle="--", alpha=0.22)
        axis.set_axisbelow(True)

        # Add a compact latest-price indicator.
        latest_price = prices[-1]
        axis.text(
            0.985, 0.96,
            f"Latest: ${latest_price:,.{decimals}f}",
            transform=axis.transAxes,
            ha="right",
            va="top",
            fontsize=10,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.9, edgecolor="#D9E2F2")
        )

        if len(prices) == 1:
            axis.text(
                0.5, 0.04,
                "Waiting for the next 30-second update...",
                transform=axis.transAxes,
                ha="center",
                va="bottom",
                fontsize=9
            )

        axis.margins(x=0.03)
        figure.tight_layout(pad=1.4)

        canvas = FigureCanvasTkAgg(figure, master=graph_area)
        canvas.draw()
        canvas.get_tk_widget().pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8
        )

        # Keep references alive for Tkinter/Matplotlib.
        graph_area._figure = figure
        graph_area._canvas = canvas

    def search_graph_coin():
        search_text = graph_search_entry.get().strip().lower()

        if not search_text or search_text == "search coin...":
            messagebox.showwarning(
                "Coin Search",
                "Enter a cryptocurrency name.",
                parent=graph_window
            )
            return

        matches = [
            name for name in names
            if search_text in name.lower()
        ]

        if not matches:
            messagebox.showinfo(
                "Coin Search",
                "Coin not found in the currently tracked Top 10.",
                parent=graph_window
            )
            return

        graph_coin_combo.set(matches[0])
        generate_graph()

    show_graph_button = make_button(
        graph_controls,
        "📊 Show Graph",
        generate_graph,
        12
    )
    show_graph_button.pack(
        side="left",
        padx=5
    )

    graph_search_entry.bind(
        "<Return>",
        lambda event: search_graph_coin()
    )

    # Changing the coin directly also redraws its OWN history.
    graph_coin_combo.bind(
        "<<ComboboxSelected>>",
        lambda event: generate_graph()
    )

    generate_graph()


graph_button = make_button(
    button_bar,
    "📈 Graph",
    open_graph_window,
    10
)
graph_button.pack(
    side="left",
    padx=5
)


# ============================================================
# UPDATE TABLE
# ============================================================

def update_table(data):

    for item in tree.get_children():

        tree.delete(
            item
        )

    for coin in data:

        change = coin[
            "change_24h"
        ]

        if change > 0:
            tag = "positive"

        elif change < 0:
            tag = "negative"

        else:
            tag = "neutral"

        tree.insert(
            "",
            "end",
            values=(
                coin["rank"],
                coin["name"],
                format_price(
                    coin["price"]
                ),
                format_change(
                    coin["change_24h"]
                ),
                format_change(
                    coin["change_7d"]
                ),
                format_large(
                    coin["market_cap"]
                ),
                format_large(
                    coin["volume"]
                )
            ),
            tags=(tag,)
        )


# ============================================================
# UPDATE STATS
# ============================================================

def update_stats():

    if not coins_data:

        return

    total = len(
        coins_data
    )

    gainers = len([
        x for x in coins_data
        if x["change_24h"] > 0
    ])

    losers = len([
        x for x in coins_data
        if x["change_24h"] < 0
    ])

    same = len([
        x for x in coins_data
        if x["change_24h"] == 0
    ])

    average = sum(
        x["change_24h"]
        for x in coins_data
    ) / total

    stat_cards[
        "total"
    ]["value"].config(
        text=str(total)
    )

    stat_cards[
        "total"
    ]["sub"].config(
        text="Top 10 tracked"
    )

    stat_cards[
        "gainers"
    ]["value"].config(
        text=str(gainers)
    )

    stat_cards[
        "gainers"
    ]["value"].config(
        fg=GREEN
    )

    stat_cards[
        "gainers"
    ]["sub"].config(
        text="Positive movement"
    )

    stat_cards[
        "losers"
    ]["value"].config(
        text=str(losers)
    )

    stat_cards[
        "losers"
    ]["value"].config(
        fg=RED
    )

    stat_cards[
        "losers"
    ]["sub"].config(
        text="Negative movement"
    )

    stat_cards[
        "same"
    ]["value"].config(
        text=str(same)
    )

    stat_cards[
        "same"
    ]["value"].config(
        fg=YELLOW
    )

    stat_cards[
        "same"
    ]["sub"].config(
        text="Stable assets"
    )

    stat_cards[
        "average"
    ]["value"].config(
        text=format_change(
            average
        ),
        fg=(
            GREEN
            if average >= 0
            else RED
        )
    )

    stat_cards[
        "average"
    ]["sub"].config(
        text="Top 10 average"
    )


# ============================================================
# UPDATE COMBOBOXES
# ============================================================

def update_combos():

    names = [
        coin["name"]
        for coin in coins_data
    ]

    coin1_combo["values"] = names
    coin2_combo["values"] = names
    alert_coin_combo["values"] = names

    if names:

        coin1_combo.set(
            names[0]
        )

        if len(names) > 1:

            coin2_combo.set(
                names[1]
            )

        alert_coin_combo.set(
            names[0]
        )


# ============================================================
# HISTORY
# ============================================================

def add_history(coins):

    global history_data

    timestamp = datetime.now()

    for coin in coins:

        history_data.append({
            "timestamp": timestamp,
            "name": coin["name"],
            "price": coin["price"]
        })


def load_history_from_csv():
    """Load previously saved price snapshots so graphs survive app restarts."""
    global history_data

    if not os.path.exists(CSV_FILE):
        return

    loaded = []

    try:
        with open(CSV_FILE, "r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                timestamp_text = row.get("Timestamp", "").strip()
                name = row.get("Name", "").strip()
                price_text = row.get("Price", "").strip()

                if not timestamp_text or not name or not price_text:
                    continue

                try:
                    timestamp = datetime.strptime(
                        timestamp_text,
                        "%Y-%m-%d %H:%M:%S"
                    )
                    price = float(price_text)
                except (ValueError, TypeError):
                    continue

                loaded.append({
                    "timestamp": timestamp,
                    "name": name,
                    "price": price
                })

        # Keep a useful amount of recent history in memory.
        history_data = loaded[-5000:]

    except Exception as error:
        print(f"History load warning: {error}")


# ============================================================
# ALERT CHECK
# ============================================================

def check_alerts():

    if not coins_data:
        return

    for alert in alert_data:

        coin = next(
            (
                x for x in coins_data
                if x["name"] == alert["name"]
            ),
            None
        )

        if not coin:
            continue

        current = coin[
            "price"
        ]

        target = alert[
            "target"
        ]

        condition = alert[
            "condition"
        ]

        triggered = False

        if (
            condition == "Above" and
            current >= target
        ):
            triggered = True

        elif (
            condition == "Below" and
            current <= target
        ):
            triggered = True

        if triggered:

            messagebox.showinfo(
                "🔔 Price Alert",
                f"{coin['name']} is now "
                f"{format_price(current)}"
            )

            alert_data.remove(
                alert
            )

            break


# ============================================================
# SCRAPE SUCCESS
# ============================================================

def on_scrape_success(data):

    global coins_data
    global last_update
    global next_update_seconds

    if not data:

        status_label.config(
            text="⚠ No market data found",
            fg=RED
        )

        live_label.config(
            text="● DATA ERROR",
            bg="#351320",
            fg=RED
        )

        return

    coins_data = data

    add_history(
        data
    )

    save_to_csv(
        data
    )

    update_table(
        data
    )

    update_stats()

    update_combos()

    check_alerts()

    last_update = datetime.now()

    next_update_seconds = (
        REFRESH_SECONDS
    )

    status_label.config(
        text=(
            f"Updated {len(data)} assets  •  "
            f"{last_update.strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        fg=MUTED
    )

    live_label.config(
        text="● LIVE MARKET",
        bg="#062A20",
        fg=GREEN
    )


# ============================================================
# SCRAPE THREAD
# ============================================================

def scrape_worker():

    global scraping

    try:

        data = scrape_top_10()

        root.after(
            0,
            lambda: on_scrape_success(
                data
            )
        )

    except Exception as error:

        print(
            "Worker error:",
            error
        )

        root.after(
            0,
            lambda: status_label.config(
                text="⚠ Scraping failed",
                fg=RED
            )
        )

    finally:

        scraping = False

        root.after(
            0,
            lambda: refresh_button.config(
                state="normal",
                text="↻  Refresh"
            )
        )


def start_scrape():

    global scraping

    if scraping:
        return

    scraping = True

    refresh_button.config(
        state="disabled",
        text="Loading..."
    )

    status_label.config(
        text="Opening CoinMarketCap...",
        fg=YELLOW
    )

    live_label.config(
        text="● UPDATING",
        bg="#33270A",
        fg=YELLOW
    )

    thread = threading.Thread(
        target=scrape_worker,
        daemon=True
    )

    thread.start()


# ============================================================
# COUNTDOWN
# ============================================================

def countdown():

    global next_update_seconds

    if next_update_seconds > 0:

        next_update_seconds -= 1

    minutes = (
        next_update_seconds // 60
    )

    seconds = (
        next_update_seconds % 60
    )

    if last_update:

        status_label.config(
            text=(
                f"Updated {len(coins_data)} assets  •  "
                f"{last_update.strftime('%Y-%m-%d %H:%M:%S')}  •  "
                f"Next update {minutes:02d}:{seconds:02d}"
            )
        )

    if (
        next_update_seconds <= 0 and
        not scraping
    ):

        next_update_seconds = (
            REFRESH_SECONDS
        )

        start_scrape()

    root.after(
        1000,
        countdown
    )


# ============================================================
# AUTO REFRESH AFTER SUCCESS
# ============================================================

def schedule_refresh():

    start_scrape()

    root.after(
        REFRESH_SECONDS * 1000,
        schedule_refresh
    )


# ============================================================
# CLOSE APPLICATION
# ============================================================

def close_application():

    global driver

    try:

        if driver:

            driver.quit()

    except Exception:
        pass

    root.destroy()


root.protocol(
    "WM_DELETE_WINDOW",
    close_application
)


# ============================================================
# START APPLICATION
# ============================================================

# Restore saved price history before the first live market update.
# This is what makes the graph show a real zig-zag trend immediately
# instead of starting from a single point every time the app opens.
load_history_from_csv()

status_label.config(
    text="Starting Crypto Pulse..."
)

root.after(
    1000,
    start_scrape
)

root.after(
    1000,
    countdown
)

root.mainloop()
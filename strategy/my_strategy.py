
class DualAssetTrendStrategy:
    def __init__(self, ema_A, ema_B, ema_C, leverage, fee_rate,
                 trailing_stop_ratio, mdd_limit, reentry_threshold):
        self.ema_A1, self.ema_A2 = ema_A
        self.ema_B1, self.ema_B2 = ema_B
        self.ema_C1, self.ema_C2 = ema_C
        self.leverage = leverage
        self.fee_rate = fee_rate
        self.trailing_stop_ratio = trailing_stop_ratio
        self.mdd_limit = mdd_limit
        self.reentry_threshold = reentry_threshold

        self.capital_A = 100
        self.capital_B = 100
        self.using_A = True
        self.in_B_mode = False
        self.peak_A = 100
        self.trough_B = 100

        self.position = 0
        self.entry_price = 0
        self.entry_time = None
        self.position_size = 0
        self.peak_price = 0

    def update_mode_switch(self):
        if self.using_A and self.capital_A <= self.peak_A * (1 - self.mdd_limit):
            self.using_A = False
            self.in_B_mode = True
            self.capital_B = self.capital_A
            self.trough_B = self.capital_B
            self.position = 0
        if self.in_B_mode and self.capital_B >= self.trough_B * (1 + self.reentry_threshold):
            self.using_A = True
            self.in_B_mode = False
            self.capital_A = self.capital_B
            self.position = 0

    def should_entry(self, data):
        if data["ema_A1"] > data["ema_A2"] and            data["prev_B1"] <= data["prev_B2"] and data["curr_B1"] > data["curr_B2"]:
            capital = self.capital_A if self.using_A else self.capital_B
            return self.position == 0 and capital > 1
        return False

    def should_exit(self, data):
        if self.position != 1:
            return False
        price = data["close"]
        if price > self.peak_price:
            self.peak_price = price
        trailing_exit = price <= self.peak_price * (1 - self.trailing_stop_ratio)
        ema_cross_exit = data["prev_C1"] >= data["prev_C2"] and data["curr_C1"] < data["curr_C2"]
        return trailing_exit or ema_cross_exit

    def on_entry(self, data):
        price = data["close"]
        capital = self.capital_A if self.using_A else self.capital_B
        self.entry_price = price
        self.entry_time = data["timestamp"]
        self.position_size = (capital * self.leverage) / price
        self.peak_price = price
        self.position = 1

    def on_exit(self, data):
        exit_price = data["close"]
        capital = self.capital_A if self.using_A else self.capital_B
        pnl = (exit_price - self.entry_price) * self.position_size
        fee = exit_price * self.position_size * self.fee_rate
        capital += pnl - fee
        self.position = 0
        if self.using_A:
            self.capital_A = capital
            self.peak_A = max(self.peak_A, self.capital_A)
        else:
            self.capital_B = capital
            self.trough_B = min(self.trough_B, self.capital_B)
        if capital <= 1:
            self.capital_A = 0
            self.capital_B = 0

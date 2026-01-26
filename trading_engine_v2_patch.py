# trading_engine_v2_patch.py
"""
trading_engine.py 수정 패치

변경 사항:
1. force_virtual_mode 플래그 추가 - VIRTUAL 모드로 시작
2. on_mode_change_callback 추가 - 모드 전환 시 GUI 알림
3. 진입 적합성 평가 후 REAL 모드 전환

적용 방법:
- 이 파일의 내용을 기존 trading_engine.py에 병합
- 또는 이 파일을 trading_engine.py로 교체
"""

# =========================================================
# trading_engine.py에 추가할 코드
# =========================================================

"""
1. __init__ 메서드에 추가:

    # 모드 제어
    self.force_virtual_mode = config.get('start_in_virtual_mode', False)
    
    # 콜백 추가
    self.on_mode_change_callback: Optional[Callable] = None
    
    # 진입 적합성 평가
    self.entry_evaluation_count = 0
    self.entry_evaluation_threshold = 3  # 3번 연속 진입 조건 충족 시 REAL 전환


2. initialize() 메서드 수정 (전략 초기화 부분):

    # 전략 초기화 후 VIRTUAL 모드 강제 설정
    if self.force_virtual_mode:
        for strategy in self.strategies.values():
            if hasattr(strategy, 'is_real_mode'):
                strategy.is_real_mode = False
        print("[*] VIRTUAL 모드로 시작 - 진입 적합성 평가 중...")


3. 새 메서드 추가:

    def check_entry_readiness(self, strategy) -> bool:
        '''진입 적합성 평가'''
        if not hasattr(strategy, 'last_ema_30m') or not strategy.last_ema_30m:
            return False
        
        ema = strategy.last_ema_30m
        
        # 상승장 확인 (EMA 150 > EMA 200)
        if ema.get('ema_150', 0) <= ema.get('ema_200', 0):
            return False
        
        # 골든크로스 근접 확인
        ema_20 = strategy.last_ema_1m.get('ema_20', 0) if strategy.last_ema_1m else 0
        ema_50 = strategy.last_ema_1m.get('ema_50', 0) if strategy.last_ema_1m else 0
        
        if ema_20 <= 0 or ema_50 <= 0:
            return False
        
        # 20EMA가 50EMA의 99% 이상이면 진입 적합
        proximity = ema_20 / ema_50
        return proximity >= 0.99
    
    def evaluate_and_switch_mode(self):
        '''진입 적합성 평가 후 모드 전환'''
        if not self.force_virtual_mode:
            return
        
        for key, strategy in self.strategies.items():
            if not hasattr(strategy, 'is_real_mode'):
                continue
            
            # 이미 REAL 모드면 스킵
            if strategy.is_real_mode:
                continue
            
            # 진입 적합성 평가
            if self.check_entry_readiness(strategy):
                self.entry_evaluation_count += 1
                print(f"[*] 진입 적합성 확인 ({self.entry_evaluation_count}/{self.entry_evaluation_threshold})")
                
                # 연속 N번 충족 시 REAL 전환
                if self.entry_evaluation_count >= self.entry_evaluation_threshold:
                    self._switch_to_real_mode(strategy, key)
            else:
                # 연속 충족 리셋
                self.entry_evaluation_count = 0
    
    def _switch_to_real_mode(self, strategy, strategy_key: str):
        '''REAL 모드로 전환'''
        strategy.is_real_mode = True
        self.force_virtual_mode = False
        
        reason = "진입 적합성 평가 통과 (상승장 + 골든크로스 근접)"
        
        print(f"[OK] {strategy_key}: VIRTUAL → REAL 모드 전환")
        print(f"     사유: {reason}")
        
        # 콜백 호출
        if self.on_mode_change_callback:
            try:
                self.on_mode_change_callback("VIRTUAL", "REAL", reason)
            except Exception as e:
                print(f"[!] 모드 전환 콜백 오류: {e}")
    
    def notify_mode_switch(self, strategy, from_mode: str, to_mode: str, reason: str):
        '''모드 전환 알림 (전략에서 호출)'''
        if self.on_mode_change_callback:
            try:
                self.on_mode_change_callback(from_mode, to_mode, reason)
            except Exception as e:
                print(f"[!] 모드 전환 콜백 오류: {e}")


4. run_cycle() 또는 메인 루프에 추가:

    # 진입 적합성 평가 (VIRTUAL 모드일 때만)
    if self.force_virtual_mode:
        self.evaluate_and_switch_mode()


5. 전략의 check_mode_switch() 메서드 수정:

    def check_mode_switch(self) -> bool:
        '''모드 전환 체크 - 엔진에 알림'''
        mode_changed = False
        old_mode = "REAL" if self.is_real_mode else "VIRTUAL"
        
        if self.is_real_mode:
            if self.real_capital < self.peak_capital * (1 - self.drawdown_threshold):
                self.is_real_mode = False
                self.trough_capital = self.virtual_capital
                mode_changed = True
                new_mode = "VIRTUAL"
                reason = f"고점 대비 {self.drawdown_threshold*100:.0f}% 손실"
                
                # 엔진에 알림
                if hasattr(self, 'engine') and self.engine:
                    self.engine.notify_mode_switch(self, old_mode, new_mode, reason)
        else:
            if self.virtual_capital > self.trough_capital * (1 + self.recovery_threshold):
                self.is_real_mode = True
                self.peak_capital = self.real_capital
                mode_changed = True
                new_mode = "REAL"
                reason = f"저점 대비 {self.recovery_threshold*100:.0f}% 회복"
                
                # 엔진에 알림
                if hasattr(self, 'engine') and self.engine:
                    self.engine.notify_mode_switch(self, old_mode, new_mode, reason)
        
        return mode_changed
"""


# =========================================================
# 전체 예시: MultiTimeframeStrategy 클래스에 적용
# =========================================================

class MultiTimeframeStrategyPatch:
    """
    기존 MultiTimeframeStrategy에 추가할 메서드들
    """
    
    def set_engine(self, engine):
        """엔진 참조 설정"""
        self.engine = engine
    
    def check_mode_switch_with_notification(self) -> bool:
        """모드 전환 체크 + 알림"""
        mode_changed = False
        old_mode = "REAL" if self.is_real_mode else "VIRTUAL"
        
        if self.is_real_mode:
            # REAL → VIRTUAL: 고점 대비 손실
            if self.real_capital < self.peak_capital * (1 - self.drawdown_threshold):
                self.is_real_mode = False
                self.trough_capital = self.virtual_capital
                mode_changed = True
                new_mode = "VIRTUAL"
                reason = f"고점 대비 {self.drawdown_threshold*100:.0f}% 손실 도달"
                
                print(f"[!] [{self.symbol}] {self.strategy_type}: {old_mode} → {new_mode}")
                print(f"    사유: {reason}")
                
                # 엔진에 알림
                if hasattr(self, 'engine') and self.engine and hasattr(self.engine, 'notify_mode_switch'):
                    self.engine.notify_mode_switch(self, old_mode, new_mode, reason)
        else:
            # VIRTUAL → REAL: 저점 대비 회복
            if self.virtual_capital > self.trough_capital * (1 + self.recovery_threshold):
                self.is_real_mode = True
                self.peak_capital = self.real_capital
                mode_changed = True
                new_mode = "REAL"
                reason = f"저점 대비 {self.recovery_threshold*100:.0f}% 회복 달성"
                
                print(f"[OK] [{self.symbol}] {self.strategy_type}: {old_mode} → {new_mode}")
                print(f"     사유: {reason}")
                
                # 엔진에 알림
                if hasattr(self, 'engine') and self.engine and hasattr(self.engine, 'notify_mode_switch'):
                    self.engine.notify_mode_switch(self, old_mode, new_mode, reason)
        
        return mode_changed


# =========================================================
# 간단한 적용 방법 (기존 코드 최소 수정)
# =========================================================

def patch_trading_engine(engine):
    """
    기존 TradingEngine 객체에 패치 적용
    
    사용법:
        engine = TradingEngine(config)
        patch_trading_engine(engine)
        engine.start()
    """
    # 속성 추가
    engine.force_virtual_mode = True
    engine.on_mode_change_callback = None
    engine.entry_evaluation_count = 0
    engine.entry_evaluation_threshold = 3
    
    # 전략에 엔진 참조 설정
    if hasattr(engine, 'strategies'):
        for strategy in engine.strategies.values():
            strategy.engine = engine
            if hasattr(strategy, 'is_real_mode'):
                strategy.is_real_mode = False  # VIRTUAL로 시작
    
    print("[*] TradingEngine 패치 적용됨 (VIRTUAL 모드 시작)")


def set_mode_change_callback(engine, callback):
    """
    모드 전환 콜백 설정
    
    사용법:
        def on_mode_change(from_mode, to_mode, reason):
            print(f"모드 전환: {from_mode} → {to_mode}")
        
        set_mode_change_callback(engine, on_mode_change)
    """
    engine.on_mode_change_callback = callback

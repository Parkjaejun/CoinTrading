# ============================================================
# 🎯 전략 모드 선택 기능 - 통합 패치 파일
# ============================================================
# 
# 이 파일 하나로 전략 모드 선택 기능을 프로젝트에 적용할 수 있습니다.
# 
# 버전: 2.1
# 날짜: 2025-02-04
# 기능: Long Only / Long + Short 전략 모드 선택
# ============================================================

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# PyQt5 imports (GUI 사용 시)
try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QLabel, QComboBox, QMessageBox, QFrame
    )
    from PyQt5.QtCore import pyqtSignal
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False


# ============================================================
# Part 1: 설정 관리자
# ============================================================

class StrategyConfigManager:
    """전략 설정 관리자 - JSON 파일로 설정 저장/로드"""
    
    DEFAULT_CONFIG = {
        "version": "2.1",
        "trading": {
            "strategy_mode": "long_only",
            "symbol": "BTC-USDT-SWAP",
        },
        "long_strategy": {
            "enabled": True,
            "leverage": 10,
            "trailing_stop": 0.10,
            "stop_loss_ratio": 0.20,
            "reentry_gain_ratio": 0.30
        },
        "short_strategy": {
            "enabled": False,
            "leverage": 3,
            "trailing_stop": 0.02,
            "stop_loss_ratio": 0.10,
            "reentry_gain_ratio": 0.20
        }
    }
    
    def __init__(self, config_path: str = "config/trading_config.json"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        
        config_dir = os.path.dirname(config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        self.load()
    
    def load(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = self.DEFAULT_CONFIG.copy()
                self.save()
        except Exception as e:
            print(f"⚠️ 설정 로드 오류: {e}")
            self.config = self.DEFAULT_CONFIG.copy()
        return self.config
    
    def save(self) -> bool:
        try:
            self.config["last_updated"] = datetime.now().isoformat()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"⚠️ 설정 저장 오류: {e}")
            return False
    
    def get_strategy_mode(self) -> str:
        return self.config.get("trading", {}).get("strategy_mode", "long_only")
    
    def set_strategy_mode(self, mode: str) -> bool:
        if mode not in ["long_only", "long_short"]:
            return False
        
        if "trading" not in self.config:
            self.config["trading"] = {}
        self.config["trading"]["strategy_mode"] = mode
        
        if "short_strategy" not in self.config:
            self.config["short_strategy"] = self.DEFAULT_CONFIG["short_strategy"].copy()
        self.config["short_strategy"]["enabled"] = (mode == "long_short")
        
        return self.save()


# ============================================================
# Part 2: GUI 위젯 (PyQt5)
# ============================================================

if PYQT5_AVAILABLE:
    class StrategyModeWidget(QWidget):
        """전략 모드 선택 위젯"""
        
        strategy_mode_changed = pyqtSignal(str)
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.current_mode = "long_only"
            self.is_trading_active = False
            self.setup_ui()
        
        def setup_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            
            group = QGroupBox("🎯 전략 모드 설정")
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #3a3a3a;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
            """)
            
            group_layout = QVBoxLayout()
            
            # 모드 선택 콤보박스
            mode_layout = QHBoxLayout()
            mode_label = QLabel("전략 모드:")
            mode_label.setStyleSheet("font-weight: bold;")
            
            self.strategy_combo = QComboBox()
            self.strategy_combo.addItem("🟢 Long Only (롱 전용)", "long_only")
            self.strategy_combo.addItem("🟡 Long + Short (양방향)", "long_short")
            self.strategy_combo.setMinimumWidth(200)
            self.strategy_combo.setStyleSheet("""
                QComboBox {
                    padding: 5px 10px;
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QComboBox:hover { border-color: #0078d4; }
                QComboBox::drop-down { border: none; width: 30px; }
                QComboBox QAbstractItemView {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    selection-background-color: #0078d4;
                }
            """)
            self.strategy_combo.currentIndexChanged.connect(self.on_mode_changed)
            
            mode_layout.addWidget(mode_label)
            mode_layout.addWidget(self.strategy_combo)
            mode_layout.addStretch()
            group_layout.addLayout(mode_layout)
            
            # 구분선
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("background-color: #3a3a3a;")
            group_layout.addWidget(line)
            
            # 상태 라벨
            self.status_label = QLabel("🟢 Long Only 모드 활성")
            self.status_label.setStyleSheet("color: #00ff88; font-size: 13px; padding: 5px;")
            group_layout.addWidget(self.status_label)
            
            # 롱 전략 정보
            self.long_info = QLabel(
                "📈 롱 전략: 레버리지 10x | 트레일링스탑 10% | 손실 -20% 가상전환"
            )
            self.long_info.setStyleSheet("color: #00ff88; font-size: 11px;")
            self.long_info.setWordWrap(True)
            group_layout.addWidget(self.long_info)
            
            # 숏 전략 정보 (기본 숨김)
            self.short_info = QLabel(
                "📉 숏 전략: 레버리지 3x | 트레일링스탑 2% | 손실 -10% 가상전환"
            )
            self.short_info.setStyleSheet("color: #ff6b6b; font-size: 11px;")
            self.short_info.setWordWrap(True)
            self.short_info.hide()
            group_layout.addWidget(self.short_info)
            
            # 경고 라벨 (기본 숨김)
            self.warning_label = QLabel(
                "⚠️ 양방향 전략은 시장 변동성이 클 때 손실 위험이 증가할 수 있습니다."
            )
            self.warning_label.setStyleSheet("""
                color: #ffaa00; font-size: 11px; padding: 5px;
                background-color: #3a3a00; border-radius: 3px;
            """)
            self.warning_label.setWordWrap(True)
            self.warning_label.hide()
            group_layout.addWidget(self.warning_label)
            
            group.setLayout(group_layout)
            layout.addWidget(group)
        
        def on_mode_changed(self, index: int):
            new_mode = self.strategy_combo.currentData()
            
            if self.is_trading_active:
                reply = QMessageBox.warning(
                    self, "전략 모드 변경",
                    "자동매매가 실행 중입니다.\n전략 모드를 변경하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.No:
                    self.strategy_combo.blockSignals(True)
                    prev_index = 0 if self.current_mode == "long_only" else 1
                    self.strategy_combo.setCurrentIndex(prev_index)
                    self.strategy_combo.blockSignals(False)
                    return
            
            self.set_mode(new_mode)
        
        def set_mode(self, mode: str):
            if mode not in ["long_only", "long_short"]:
                return
            
            self.current_mode = mode
            
            if mode == "long_only":
                self.status_label.setText("🟢 Long Only 모드 활성")
                self.status_label.setStyleSheet("color: #00ff88; font-size: 13px; padding: 5px;")
                self.short_info.hide()
                self.warning_label.hide()
            else:
                self.status_label.setText("🟡 Long + Short 모드 활성")
                self.status_label.setStyleSheet("color: #ffaa00; font-size: 13px; padding: 5px;")
                self.short_info.show()
                self.warning_label.show()
            
            self.strategy_mode_changed.emit(mode)
            print(f"📊 전략 모드 변경: {mode}")
        
        def set_trading_active(self, is_active: bool):
            self.is_trading_active = is_active
        
        def get_current_mode(self) -> str:
            return self.current_mode
        
        def load_settings(self, settings: dict):
            mode = settings.get("strategy_mode", "long_only")
            self.strategy_combo.blockSignals(True)
            self.strategy_combo.setCurrentIndex(0 if mode == "long_only" else 1)
            self.strategy_combo.blockSignals(False)
            self.current_mode = mode
            
            # UI 업데이트
            if mode == "long_only":
                self.status_label.setText("🟢 Long Only 모드 활성")
                self.status_label.setStyleSheet("color: #00ff88; font-size: 13px; padding: 5px;")
                self.short_info.hide()
                self.warning_label.hide()
            else:
                self.status_label.setText("🟡 Long + Short 모드 활성")
                self.status_label.setStyleSheet("color: #ffaa00; font-size: 13px; padding: 5px;")
                self.short_info.show()
                self.warning_label.show()


# ============================================================
# Part 3: 전략 모드 믹스인 (엔진/전략 관리자용)
# ============================================================

class StrategyModeMixin:
    """
    전략 모드 관리 믹스인
    
    기존 클래스에 상속하거나 patch_engine_strategy_mode() 함수로 추가
    """
    
    def init_strategy_mode(self):
        """전략 모드 초기화 - __init__에서 호출"""
        self.strategy_mode: str = "long_only"
        self.long_strategy_active: bool = True
        self.short_strategy_active: bool = False
    
    def set_strategy_mode(self, mode: str) -> bool:
        """전략 모드 설정"""
        if mode not in ["long_only", "long_short"]:
            print(f"⚠️ 알 수 없는 전략 모드: {mode}")
            return False
        
        previous_mode = getattr(self, 'strategy_mode', 'long_only')
        self.strategy_mode = mode
        
        if mode == "long_only":
            self.long_strategy_active = True
            self.short_strategy_active = False
        else:
            self.long_strategy_active = True
            self.short_strategy_active = True
        
        # 로그 출력
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\n{'='*60}")
        print(f"[{ts}] 🔄 전략 모드 변경: {previous_mode} → {mode}")
        print(f"{'='*60}")
        if mode == "long_only":
            print(f"  📈 롱 전략: ✅ 활성")
            print(f"  📉 숏 전략: ⛔ 비활성")
        else:
            print(f"  📈 롱 전략: ✅ 활성 (레버리지 10x)")
            print(f"  📉 숏 전략: ✅ 활성 (레버리지 3x)")
        print(f"{'='*60}\n")
        
        return True
    
    def get_strategy_mode(self) -> str:
        return getattr(self, 'strategy_mode', 'long_only')
    
    def is_short_enabled(self) -> bool:
        return getattr(self, 'short_strategy_active', False)
    
    def is_long_enabled(self) -> bool:
        return getattr(self, 'long_strategy_active', True)


# ============================================================
# Part 4: 엔진 패치 함수
# ============================================================

def patch_engine_strategy_mode(engine_instance):
    """
    기존 엔진 인스턴스에 전략 모드 기능 추가
    
    사용법:
        engine = CrossReverseDualModeVirtualResetEngine(params)
        patch_engine_strategy_mode(engine)
        engine.set_strategy_mode("long_short")
    """
    import types
    
    # 속성 추가
    engine_instance.strategy_mode = "long_only"
    engine_instance.long_strategy_active = True
    engine_instance.short_strategy_active = False
    
    # 메서드 바인딩
    engine_instance.set_strategy_mode = types.MethodType(
        StrategyModeMixin.set_strategy_mode, engine_instance
    )
    engine_instance.get_strategy_mode = types.MethodType(
        StrategyModeMixin.get_strategy_mode, engine_instance
    )
    engine_instance.is_short_enabled = types.MethodType(
        StrategyModeMixin.is_short_enabled, engine_instance
    )
    engine_instance.is_long_enabled = types.MethodType(
        StrategyModeMixin.is_long_enabled, engine_instance
    )
    
    print("✅ 엔진에 전략 모드 기능이 패치되었습니다.")
    return engine_instance


# ============================================================
# Part 5: on_bar() 수정 가이드
# ============================================================

ON_BAR_PATCH_GUIDE = """
============================================================
📝 on_bar() 메서드 수정 가이드
============================================================

파일: scratch_2.py (또는 엔진 파일)
위치: on_bar() 메서드 내 약 409라인

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 수정 전 (기존 코드):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # (C) 진입 신호
    long_trend_ok = trend_fast > trend_slow
    short_trend_ok = trend_fast < trend_slow
    long_entry = long_trend_ok and cross_up(prev_e20, prev_e50, curr_e20, curr_e50)
    short_entry = False  # ← 이 줄을 수정

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 수정 후:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # (C) 진입 신호
    long_trend_ok = trend_fast > trend_slow
    short_trend_ok = trend_fast < trend_slow
    long_entry = long_trend_ok and cross_up(prev_e20, prev_e50, curr_e20, curr_e50)
    
    # ⭐ 전략 모드에 따른 숏 진입 제어
    if self.strategy_mode == "long_short":
        short_entry = short_trend_ok and cross_down(prev_e20, prev_e50, curr_e20, curr_e50)
    else:
        short_entry = False  # Long Only 모드

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 추가로 __init__()에 다음 추가:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    self.strategy_mode = "long_only"  # 기본값

============================================================
"""


# ============================================================
# Part 6: 테스트 및 예시
# ============================================================

def run_tests():
    """기능 테스트 실행"""
    print("=" * 60)
    print("전략 모드 기능 테스트")
    print("=" * 60)
    
    # 테스트 1: 설정 관리자
    print("\n[1] 설정 관리자 테스트")
    config = StrategyConfigManager("test_config.json")
    print(f"  초기 모드: {config.get_strategy_mode()}")
    
    config.set_strategy_mode("long_short")
    print(f"  변경 후: {config.get_strategy_mode()}")
    
    config.set_strategy_mode("long_only")
    print(f"  복원 후: {config.get_strategy_mode()}")
    
    # 정리
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")
    
    # 테스트 2: 믹스인
    print("\n[2] 믹스인 테스트")
    
    class TestEngine(StrategyModeMixin):
        def __init__(self):
            self.init_strategy_mode()
    
    engine = TestEngine()
    print(f"  초기 모드: {engine.get_strategy_mode()}")
    print(f"  숏 활성화: {engine.is_short_enabled()}")
    
    engine.set_strategy_mode("long_short")
    print(f"  변경 후 숏 활성화: {engine.is_short_enabled()}")
    
    # 테스트 3: 패치 함수
    print("\n[3] 패치 함수 테스트")
    
    class DummyEngine:
        pass
    
    dummy = DummyEngine()
    patch_engine_strategy_mode(dummy)
    print(f"  패치 후 모드: {dummy.get_strategy_mode()}")
    dummy.set_strategy_mode("long_short")
    
    print("\n" + "=" * 60)
    print("모든 테스트 완료!")
    print("=" * 60)


# ============================================================
# 메인 실행
# ============================================================

if __name__ == "__main__":
    print(ON_BAR_PATCH_GUIDE)
    run_tests()

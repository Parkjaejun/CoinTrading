# gui/config_validator.py
"""
GUI용 설정 검증 및 관리 모듈
config.py의 기존 함수들을 GUI에서 사용할 수 있도록 보완
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Tuple, List

# 기존 config 모듈 임포트
try:
    from config import *  # 모든 설정값 임포트
except ImportError:
    # GUI 전용 기본 설정 (config.py가 없는 경우)
    API_KEY = "your_api_key_here"
    API_SECRET = "your_api_secret_here"
    PASSPHRASE = "your_passphrase_here"
    
    TRADING_CONFIG = {
        "initial_capital": 10000,
        "symbols": ["BTC-USDT-SWAP"],
        "paper_trading": True
    }
    
    LONG_STRATEGY_CONFIG = {
        "leverage": 10,
        "trailing_stop": 0.10
    }
    
    SHORT_STRATEGY_CONFIG = {
        "leverage": 3,
        "trailing_stop": 0.02
    }
    
    NOTIFICATION_CONFIG = {
        "slack": {"enabled": False},
        "telegram": {"enabled": False},
        "email": {"enabled": False}
    }

class ConfigValidator:
    """설정 검증 클래스"""
    
    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_api_credentials(self) -> Tuple[bool, List[str]]:
        """API 인증 정보 검증"""
        errors = []
        
        # API 키 검증
        if not API_KEY or API_KEY == "your_api_key_here":
            errors.append("API Key가 설정되지 않았습니다")
        elif len(API_KEY) < 10:
            errors.append("API Key가 너무 짧습니다")
        
        # Secret 검증
        if not API_SECRET or API_SECRET == "your_api_secret_here":
            errors.append("API Secret이 설정되지 않았습니다")
        elif len(API_SECRET) < 10:
            errors.append("API Secret이 너무 짧습니다")
        
        # Passphrase 검증
        if not PASSPHRASE or PASSPHRASE == "your_passphrase_here":
            errors.append("Passphrase가 설정되지 않았습니다")
        
        return len(errors) == 0, errors
    
    def validate_trading_config(self) -> Tuple[bool, List[str]]:
        """거래 설정 검증"""
        errors = []
        
        # 초기 자본 검증
        initial_capital = TRADING_CONFIG.get('initial_capital', 0)
        if initial_capital < 100:
            errors.append("초기 자본이 너무 적습니다 (최소 $100)")
        elif initial_capital > 1000000:
            errors.append("초기 자본이 너무 큽니다 (최대 $1,000,000)")
        
        # 심볼 검증
        symbols = TRADING_CONFIG.get('symbols', [])
        if not symbols:
            errors.append("거래 심볼이 설정되지 않았습니다")
        
        for symbol in symbols:
            if not symbol.endswith('-SWAP'):
                errors.append(f"잘못된 심볼 형식: {symbol} (예: BTC-USDT-SWAP)")
        
        return len(errors) == 0, errors
    
    def validate_strategy_config(self) -> Tuple[bool, List[str]]:
        """전략 설정 검증"""
        errors = []
        
        # 롱 전략 검증
        long_leverage = LONG_STRATEGY_CONFIG.get('leverage', 1)
        if long_leverage < 1 or long_leverage > 100:
            errors.append("롱 전략 레버리지는 1-100 범위여야 합니다")
        
        long_trailing = LONG_STRATEGY_CONFIG.get('trailing_stop', 0)
        if long_trailing <= 0 or long_trailing > 0.5:
            errors.append("롱 전략 트레일링 스탑은 0-50% 범위여야 합니다")
        
        # 숏 전략 검증
        short_leverage = SHORT_STRATEGY_CONFIG.get('leverage', 1)
        if short_leverage < 1 or short_leverage > 100:
            errors.append("숏 전략 레버리지는 1-100 범위여야 합니다")
        
        short_trailing = SHORT_STRATEGY_CONFIG.get('trailing_stop', 0)
        if short_trailing <= 0 or short_trailing > 0.5:
            errors.append("숏 전략 트레일링 스탑은 0-50% 범위여야 합니다")
        
        return len(errors) == 0, errors
    
    def validate_all(self) -> Tuple[bool, Dict[str, List[str]]]:
        """전체 설정 검증"""
        results = {}
        all_valid = True
        
        # API 인증 검증
        api_valid, api_errors = self.validate_api_credentials()
        results['api'] = api_errors
        if not api_valid:
            all_valid = False
        
        # 거래 설정 검증
        trading_valid, trading_errors = self.validate_trading_config()
        results['trading'] = trading_errors
        if not trading_valid:
            all_valid = False
        
        # 전략 설정 검증
        strategy_valid, strategy_errors = self.validate_strategy_config()
        results['strategy'] = strategy_errors
        if not strategy_valid:
            all_valid = False
        
        return all_valid, results

class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self):
        self.config_file = "gui_trading_config.json"
        self.backup_dir = "config_backups"
        
        # 백업 디렉토리 생성
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """설정 저장"""
        try:
            # 백업 생성
            self.create_backup()
            
            # 새 설정 저장
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"설정 저장 오류: {e}")
            return False
    
    def load_config(self) -> Dict[str, Any]:
        """설정 불러오기"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self.get_default_config()
        except Exception as e:
            print(f"설정 불러오기 오류: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            'api': {
                'api_key': '',
                'api_secret': '',
                'passphrase': '',
                'paper_trading': True
            },
            'trading': {
                'initial_capital': 10000,
                'symbols': ['BTC-USDT-SWAP'],
                'max_positions': 5
            },
            'long_strategy': {
                'leverage': 10,
                'trailing_stop': 0.10,
                'stop_loss': 0.20,
                'reentry_gain': 0.30
            },
            'short_strategy': {
                'leverage': 3,
                'trailing_stop': 0.02,
                'stop_loss': 0.10,
                'reentry_gain': 0.20
            },
            'notifications': {
                'slack': {'enabled': False, 'webhook_url': ''},
                'telegram': {'enabled': False, 'bot_token': '', 'chat_id': ''},
                'email': {'enabled': False, 'smtp_server': 'smtp.gmail.com', 'sender_email': '', 'recipient_email': ''}
            },
            'gui': {
                'theme': 'dark',
                'auto_scroll_logs': True,
                'chart_update_interval': 1000,
                'position_update_interval': 5000
            }
        }
    
    def create_backup(self) -> str:
        """설정 백업 생성"""
        if not os.path.exists(self.config_file):
            return ""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(self.backup_dir, f"config_backup_{timestamp}.json")
        
        try:
            shutil.copy2(self.config_file, backup_file)
            return backup_file
        except Exception as e:
            print(f"백업 생성 오류: {e}")
            return ""
    
    def restore_backup(self, backup_file: str) -> bool:
        """백업에서 복원"""
        try:
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, self.config_file)
                return True
            return False
        except Exception as e:
            print(f"백업 복원 오류: {e}")
            return False
    
    def list_backups(self) -> List[str]:
        """백업 파일 목록"""
        try:
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.startswith('config_backup_') and file.endswith('.json'):
                    backups.append(file)
            return sorted(backups, reverse=True)  # 최신순
        except Exception:
            return []
    
    def export_config(self, export_path: str) -> bool:
        """설정 내보내기"""
        try:
            config_data = self.load_config()
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"설정 내보내기 오류: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """설정 가져오기"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 설정 검증
            validator = ConfigValidator()
            # 여기서 validator로 imported config 검증 가능
            
            return self.save_config(config_data)
        except Exception as e:
            print(f"설정 가져오기 오류: {e}")
            return False

class GUIConfigIntegrator:
    """GUI와 기존 config.py 통합 클래스"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.validator = ConfigValidator()
    
    def sync_with_main_config(self):
        """GUI 설정을 메인 config.py와 동기화"""
        gui_config = self.config_manager.load_config()
        
        # config.py 스타일로 변환
        try:
            # 기존 config 모듈의 변수들 업데이트
            global API_KEY, API_SECRET, PASSPHRASE
            global TRADING_CONFIG, LONG_STRATEGY_CONFIG, SHORT_STRATEGY_CONFIG
            global NOTIFICATION_CONFIG
            
            # API 설정 동기화
            if 'api' in gui_config:
                API_KEY = gui_config['api'].get('api_key', API_KEY)
                API_SECRET = gui_config['api'].get('api_secret', API_SECRET)
                PASSPHRASE = gui_config['api'].get('passphrase', PASSPHRASE)
            
            # 거래 설정 동기화
            if 'trading' in gui_config:
                TRADING_CONFIG.update(gui_config['trading'])
            
            # 전략 설정 동기화
            if 'long_strategy' in gui_config:
                LONG_STRATEGY_CONFIG.update(gui_config['long_strategy'])
            
            if 'short_strategy' in gui_config:
                SHORT_STRATEGY_CONFIG.update(gui_config['short_strategy'])
            
            # 알림 설정 동기화
            if 'notifications' in gui_config:
                NOTIFICATION_CONFIG.update(gui_config['notifications'])
                
        except Exception as e:
            print(f"설정 동기화 오류: {e}")
    
    def validate_and_save_gui_config(self, gui_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """GUI 설정 검증 및 저장"""
        # 임시로 전역 변수 업데이트
        original_values = self._backup_global_config()
        
        try:
            self._apply_gui_config_to_globals(gui_config)
            
            # 검증 수행
            is_valid, validation_results = self.validator.validate_all()
            
            if is_valid:
                # 검증 성공 시 저장
                self.config_manager.save_config(gui_config)
                return True, []
            else:
                # 검증 실패 시 원래 값 복원
                self._restore_global_config(original_values)
                
                # 모든 오류 메시지 수집
                all_errors = []
                for category, errors in validation_results.items():
                    all_errors.extend([f"{category}: {error}" for error in errors])
                
                return False, all_errors
                
        except Exception as e:
            # 오류 발생 시 원래 값 복원
            self._restore_global_config(original_values)
            return False, [f"설정 처리 오류: {str(e)}"]
    
    def _backup_global_config(self) -> Dict[str, Any]:
        """현재 전역 설정 백업"""
        return {
            'API_KEY': globals().get('API_KEY'),
            'API_SECRET': globals().get('API_SECRET'),
            'PASSPHRASE': globals().get('PASSPHRASE'),
            'TRADING_CONFIG': globals().get('TRADING_CONFIG', {}).copy(),
            'LONG_STRATEGY_CONFIG': globals().get('LONG_STRATEGY_CONFIG', {}).copy(),
            'SHORT_STRATEGY_CONFIG': globals().get('SHORT_STRATEGY_CONFIG', {}).copy(),
            'NOTIFICATION_CONFIG': globals().get('NOTIFICATION_CONFIG', {}).copy()
        }
    
    def _apply_gui_config_to_globals(self, gui_config: Dict[str, Any]):
        """GUI 설정을 전역 변수에 적용"""
        global API_KEY, API_SECRET, PASSPHRASE
        global TRADING_CONFIG, LONG_STRATEGY_CONFIG, SHORT_STRATEGY_CONFIG
        global NOTIFICATION_CONFIG
        
        if 'api' in gui_config:
            API_KEY = gui_config['api'].get('api_key', API_KEY)
            API_SECRET = gui_config['api'].get('api_secret', API_SECRET)
            PASSPHRASE = gui_config['api'].get('passphrase', PASSPHRASE)
        
        if 'trading' in gui_config:
            TRADING_CONFIG.update(gui_config['trading'])
        
        if 'long_strategy' in gui_config:
            LONG_STRATEGY_CONFIG.update(gui_config['long_strategy'])
        
        if 'short_strategy' in gui_config:
            SHORT_STRATEGY_CONFIG.update(gui_config['short_strategy'])
        
        if 'notifications' in gui_config:
            NOTIFICATION_CONFIG.update(gui_config['notifications'])
    
    def _restore_global_config(self, backup: Dict[str, Any]):
        """백업된 전역 설정 복원"""
        global API_KEY, API_SECRET, PASSPHRASE
        global TRADING_CONFIG, LONG_STRATEGY_CONFIG, SHORT_STRATEGY_CONFIG
        global NOTIFICATION_CONFIG
        
        API_KEY = backup['API_KEY']
        API_SECRET = backup['API_SECRET']
        PASSPHRASE = backup['PASSPHRASE']
        TRADING_CONFIG = backup['TRADING_CONFIG']
        LONG_STRATEGY_CONFIG = backup['LONG_STRATEGY_CONFIG']
        SHORT_STRATEGY_CONFIG = backup['SHORT_STRATEGY_CONFIG']
        NOTIFICATION_CONFIG = backup['NOTIFICATION_CONFIG']

# 전역 인스턴스
config_integrator = GUIConfigIntegrator()
config_validator = ConfigValidator()
config_manager = ConfigManager()

def validate_config() -> Tuple[bool, Dict[str, List[str]]]:
    """설정 검증 (메인 함수)"""
    return config_validator.validate_all()

def get_gui_config() -> Dict[str, Any]:
    """GUI 설정 조회"""
    return config_manager.load_config()

def save_gui_config(config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """GUI 설정 저장"""
    return config_integrator.validate_and_save_gui_config(config_data)

def print_config_summary():
    """설정 요약 출력"""
    print("\n📋 현재 설정 요약:")
    print(f"  💰 초기 자본: ${TRADING_CONFIG.get('initial_capital', 0):,}")
    print(f"  📊 거래 심볼: {', '.join(TRADING_CONFIG.get('symbols', []))}")
    print(f"  📈 롱 레버리지: {LONG_STRATEGY_CONFIG.get('leverage', 0)}배")
    print(f"  📉 숏 레버리지: {SHORT_STRATEGY_CONFIG.get('leverage', 0)}배")
    
    # 알림 채널 확인
    active_notifications = []
    for channel, config in NOTIFICATION_CONFIG.items():
        if isinstance(config, dict) and config.get('enabled', False):
            active_notifications.append(channel)
    
    if active_notifications:
        print(f"  🔔 활성 알림: {', '.join(active_notifications)}")
    else:
        print(f"  🔕 알림: 비활성화")

def backup_config() -> str:
    """설정 백업"""
    return config_manager.create_backup()
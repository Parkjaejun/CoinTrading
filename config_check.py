# config_check.py
"""
config.py 파일 검증 및 문제 해결 스크립트
"""

import os
import sys

def check_config_file():
    """config.py 파일 검사"""
    print("🔍 config.py 파일 검사 중...")
    
    try:
        # config.py 파일 존재 확인
        if not os.path.exists('config.py'):
            print("❌ config.py 파일이 없습니다!")
            create_config_template()
            return False
        
        # config.py 임포트 시도
        try:
            from config import API_KEY, API_SECRET, PASSPHRASE
        except ImportError as e:
            print(f"❌ config.py 임포트 오류: {e}")
            return False
        
        # API 키 검사
        issues = []
        
        if not API_KEY or API_KEY == "your_api_key_here":
            issues.append("API_KEY가 설정되지 않음")
        elif len(API_KEY) < 20:
            issues.append(f"API_KEY가 너무 짧음 ({len(API_KEY)}자)")
        
        if not API_SECRET or API_SECRET == "your_api_secret_here":
            issues.append("API_SECRET이 설정되지 않음")
        elif len(API_SECRET) < 20:
            issues.append(f"API_SECRET이 너무 짧음 ({len(API_SECRET)}자)")
        
        if not PASSPHRASE or PASSPHRASE == "your_passphrase_here":
            issues.append("PASSPHRASE가 설정되지 않음")
        elif len(PASSPHRASE) < 5:
            issues.append(f"PASSPHRASE가 너무 짧음 ({len(PASSPHRASE)}자)")
        
        if issues:
            print("❌ config.py 문제점들:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            print("\n🛠️ 해결 방법:")
            print("  1. OKX 거래소에 로그인")
            print("  2. API 관리 메뉴로 이동")
            print("  3. 새 API 키 생성 (읽기 + 거래 권한)")
            print("  4. config.py 파일에 정확히 입력")
            return False
        else:
            print("✅ config.py 설정이 올바릅니다")
            print(f"  API_KEY: {API_KEY[:8]}...{API_KEY[-4:]}")
            print(f"  API_SECRET: {API_SECRET[:8]}...{API_SECRET[-4:]}")
            print(f"  PASSPHRASE: {'*' * len(PASSPHRASE)}")
            return True
            
    except Exception as e:
        print(f"❌ config.py 검사 중 오류: {e}")
        return False

def create_config_template():
    """config.py 템플릿 생성"""
    print("\n📝 config.py 템플릿 생성 중...")
    
    config_template = '''# config.py
"""
OKX API 설정 파일
OKX 거래소에서 API 키를 발급받아 아래 값들을 설정하세요.
"""

# ==================== API 설정 ====================
# OKX API 키 정보 (https://www.okx.com/account/my-api에서 발급)
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"
PASSPHRASE = "your_passphrase_here"

# API 서버 URL
API_BASE_URL = "https://www.okx.com"

# ==================== 거래 설정 ====================
TRADING_CONFIG = {
    # 거래할 심볼들
    "symbols": ["BTC-USDT-SWAP"],
    
    # 기본 거래 설정
    "default_leverage": 10,
    "max_position_size": 1000,  # USDT
    "risk_per_trade": 0.02,     # 2%
    
    # 안전 설정
    "max_daily_loss": 0.05,     # 5%
    "emergency_stop_loss": 0.20, # 20%
}

# ==================== EMA 설정 ====================
EMA_PERIODS = {
    "trend_fast": 20,      # 단기 추세
    "trend_medium": 50,    # 중기 추세
    "trend_slow": 100,     # 장기 추세
    "trend_long": 150,     # 장기 필터
    "trend_super": 200     # 슈퍼 추세
}

# ==================== 알림 설정 ====================
NOTIFICATION_CONFIG = {
    "enabled": True,
    "discord_webhook": None,    # Discord 웹훅 URL
    "telegram_bot_token": None, # Telegram 봇 토큰
    "telegram_chat_id": None,   # Telegram 채팅 ID
}

# ==================== 로깅 설정 ====================
LOGGING_CONFIG = {
    "level": "INFO",
    "file_enabled": True,
    "console_enabled": True,
    "max_file_size": 10,  # MB
    "backup_count": 5
}

# ==================== 백테스팅 설정 ====================
BACKTEST_CONFIG = {
    "initial_balance": 10000,  # USDT
    "commission_rate": 0.0005, # 0.05%
    "slippage": 0.001,         # 0.1%
}
'''

    try:
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(config_template)
        
        print("✅ config.py 템플릿이 생성되었습니다!")
        print("\n🔧 다음 단계:")
        print("  1. config.py 파일을 열어주세요")
        print("  2. OKX 거래소에서 API 키를 발급받으세요")
        print("  3. API_KEY, API_SECRET, PASSPHRASE를 입력하세요")
        print("  4. 다시 테스트를 실행하세요")
        
    except Exception as e:
        print(f"❌ config.py 생성 실패: {e}")

def fix_passphrase_encoding():
    """Passphrase 인코딩 문제 해결"""
    print("\n🔧 Passphrase 인코딩 문제 해결...")
    
    try:
        from config import PASSPHRASE
        
        # 다양한 인코딩 테스트
        encodings = ['utf-8', 'ascii', 'latin-1']
        
        for encoding in encodings:
            try:
                encoded = PASSPHRASE.encode(encoding)
                decoded = encoded.decode(encoding)
                
                if decoded == PASSPHRASE:
                    print(f"✅ {encoding} 인코딩 정상")
                else:
                    print(f"⚠️ {encoding} 인코딩 문제 감지")
                    
            except Exception as e:
                print(f"❌ {encoding} 인코딩 실패: {e}")
        
        # 특수문자 검사
        import string
        
        if not all(c in string.printable for c in PASSPHRASE):
            print("⚠️ Passphrase에 특수문자가 포함되어 있습니다")
            print("  - 영문자, 숫자, 기본 특수문자만 사용하세요")
        
        print(f"📝 현재 Passphrase: '{PASSPHRASE}' ({len(PASSPHRASE)}자)")
        
    except ImportError:
        print("❌ config.py에서 PASSPHRASE를 가져올 수 없습니다")
    except Exception as e:
        print(f"❌ Passphrase 검사 실패: {e}")

def main():
    """메인 검사 실행"""
    print("🔍 OKX API 설정 검사 시작")
    print("=" * 50)
    
    # config.py 파일 검사
    config_ok = check_config_file()
    
    if config_ok:
        # Passphrase 인코딩 검사
        fix_passphrase_encoding()
        
        print("\n✅ 설정 검사 완료!")
        print("이제 connection_test_fixed.py를 실행하세요:")
        print("python connection_test_fixed.py")
    else:
        print("\n❌ 설정 문제 발견")
        print("config.py 파일을 수정한 후 다시 실행하세요.")
    
    return config_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
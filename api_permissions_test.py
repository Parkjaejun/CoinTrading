# api_permissions_test.py
"""
OKX API 권한별 테스트 스크립트
각 API 엔드포인트별로 권한을 확인
"""

from config import make_api_request

def test_api_permissions():
    """API 권한별 테스트"""
    print("🔍 OKX API 권한 테스트")
    print("=" * 50)
    
    tests = [
        # 읽기 권한 테스트
        {
            'name': '계좌 설정 조회',
            'endpoint': '/api/v5/account/config',
            'method': 'GET',
            'permission': '읽기'
        },
        {
            'name': '계좌 잔고 조회', 
            'endpoint': '/api/v5/account/balance',
            'method': 'GET',
            'permission': '읽기'
        },
        
        # 거래 권한 테스트
        {
            'name': '포지션 조회',
            'endpoint': '/api/v5/account/positions', 
            'method': 'GET',
            'permission': '거래'
        },
        {
            'name': '주문 내역 조회',
            'endpoint': '/api/v5/trade/orders-history',
            'method': 'GET', 
            'permission': '거래',
            'params': {'instType': 'SWAP', 'limit': '1'}
        },
        {
            'name': '체결 내역 조회',
            'endpoint': '/api/v5/trade/fills-history',
            'method': 'GET',
            'permission': '거래', 
            'params': {'instType': 'SWAP', 'limit': '1'}
        }
    ]
    
    results = {}
    
    for test in tests:
        print(f"\n🧪 테스트: {test['name']} ({test['permission']} 권한)")
        print("-" * 40)
        
        try:
            params = test.get('params', None)
            response = make_api_request(test['method'], test['endpoint'], params=params)
            
            if response:
                if response.get('code') == '0':
                    print(f"✅ {test['name']} 성공")
                    results[test['name']] = '성공'
                else:
                    error_msg = response.get('msg', 'Unknown error')
                    print(f"❌ {test['name']} 실패: {error_msg}")
                    results[test['name']] = f'실패: {error_msg}'
            else:
                print(f"❌ {test['name']} 실패: API 응답 없음")
                results[test['name']] = '실패: 응답 없음'
                
        except Exception as e:
            print(f"❌ {test['name']} 오류: {e}")
            results[test['name']] = f'오류: {e}'
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 API 권한 테스트 결과 요약")
    print("=" * 50)
    
    read_permissions = []
    trade_permissions = []
    
    for test in tests:
        result = results.get(test['name'], '테스트 안됨')
        status = '✅' if result == '성공' else '❌'
        print(f"{status} {test['name']}: {result}")
        
        if test['permission'] == '읽기':
            read_permissions.append(result == '성공')
        else:
            trade_permissions.append(result == '성공')
    
    # 권한별 요약
    print("\n📋 권한별 요약:")
    read_success = all(read_permissions) if read_permissions else False
    trade_success = all(trade_permissions) if trade_permissions else False
    
    print(f"📖 읽기 권한: {'✅ 정상' if read_success else '❌ 문제 있음'}")
    print(f"📈 거래 권한: {'✅ 정상' if trade_success else '❌ 문제 있음'}")
    
    if not trade_success:
        print("\n💡 해결 방법:")
        print("1. OKX 웹사이트 → 계정 → API 관리")
        print("2. API 키 편집 → 거래 권한 활성화")
        print("3. 또는 새 API 키 생성 (읽기 + 거래 권한)")
        print("4. IP 화이트리스트 설정 확인")
    
    return read_success, trade_success

if __name__ == "__main__":
    test_api_permissions()
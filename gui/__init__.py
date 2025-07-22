# gui/__init__.py
"""
OKX 자동매매 시스템 GUI 패키지
PyQt5 기반 그래픽 사용자 인터페이스
"""

__version__ = "1.0.0"
__author__ = "Trading Bot Team"

# GUI 모듈들 임포트 (선택적)
try:
    from .main_window import TradingMainWindow, main
    from .settings_dialog import AdvancedSettingsDialog, NotificationTestDialog
    from .config_validator import (
        config_manager, config_validator, config_integrator,
        validate_config, get_gui_config, save_gui_config
    )
    
    __all__ = [
        'TradingMainWindow',
        'AdvancedSettingsDialog', 
        'NotificationTestDialog',
        'config_manager',
        'config_validator',
        'config_integrator',
        'validate_config',
        'get_gui_config',
        'save_gui_config',
        'main'
    ]
    
except ImportError as e:
    # PyQt5가 설치되지 않은 경우 등 임포트 실패 시
    print(f"GUI 모듈 임포트 실패: {e}")
    print("PyQt5가 설치되어 있는지 확인하세요: pip install PyQt5")
    
    __all__ = []

def check_gui_dependencies():
    """GUI 의존성 확인"""
    missing_packages = []
    
    try:
        import PyQt5
    except ImportError:
        missing_packages.append("PyQt5")
    
    try:
        import pyqtgraph
    except ImportError:
        missing_packages.append("pyqtgraph")
    
    try:
        import psutil
    except ImportError:
        missing_packages.append("psutil")
    
    return missing_packages

def get_gui_info():
    """GUI 정보 반환"""
    try:
        from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
        import pyqtgraph
        
        info = {
            "gui_version": __version__,
            "qt_version": QT_VERSION_STR,
            "pyqt_version": PYQT_VERSION_STR,
            "pyqtgraph_version": pyqtgraph.__version__,
            "dependencies_ok": len(check_gui_dependencies()) == 0
        }
    except:
        info = {
            "gui_version": __version__,
            "dependencies_ok": False,
            "missing_packages": check_gui_dependencies()
        }
    
    return info

# 패키지 정보 출력 (디버그용)
if __name__ == "__main__":
    info = get_gui_info()
    print("GUI 패키지 정보:")
    for key, value in info.items():
        print(f"  {key}: {value}")

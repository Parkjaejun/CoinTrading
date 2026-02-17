# agents/strategy_modifier.py
"""
전략 파라미터/코드 안전 수정 관리

- 파라미터 변경: StateManager를 통해 즉시 적용
- 코드 변경: 백업 → 제안 저장 → Monitor 승인 후 적용/롤백
"""

import os
import shutil
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from utils.logger import log_system, log_error


class StrategyModifier:
    """전략 수정 관리자"""

    def __init__(self, state_manager, backup_dir: str = "agents/backups",
                 allowed_paths: Optional[List[str]] = None):
        """
        Args:
            state_manager: StateManager 인스턴스
            backup_dir: 백업 디렉토리 경로
            allowed_paths: 수정 허용 경로 목록
        """
        self._state_manager = state_manager
        self._backup_dir = backup_dir
        self._allowed_paths = allowed_paths or ["strategy/", "cointrading_v2/"]

        # 보류 중인 코드 변경 요청
        self._pending_changes: Dict[str, Dict] = {}

        # 적용된 변경 히스토리
        self._applied_changes: List[Dict] = []

        # 백업 디렉토리 생성
        os.makedirs(self._backup_dir, exist_ok=True)

    # ==================== 파라미터 변경 ====================

    def change_params(self, param_changes: Dict, param_limits: Optional[Dict] = None) -> bool:
        """
        전략 파라미터 변경 (즉시 적용)

        Args:
            param_changes: {"파라미터명": 새값, ...}
            param_limits: 허용 범위 {"파라미터명": {"min": x, "max": y}}

        Returns:
            성공 여부
        """
        # 범위 검증
        if param_limits:
            for key, value in param_changes.items():
                if key in param_limits:
                    limits = param_limits[key]
                    if not (limits["min"] <= value <= limits["max"]):
                        log_error(
                            f"[StrategyModifier] 파라미터 범위 초과: "
                            f"{key}={value} (허용: {limits['min']}~{limits['max']})"
                        )
                        return False

        try:
            self._state_manager.update_strategy_params(param_changes)
            log_system(f"[StrategyModifier] 파라미터 변경 적용: {param_changes}")
            return True
        except Exception as e:
            log_error(f"[StrategyModifier] 파라미터 변경 실패: {e}")
            return False

    # ==================== 코드 변경 ====================

    def propose_code_change(self, file_path: str, new_code: str,
                            reason: str) -> Optional[str]:
        """
        코드 변경 제안 (Monitor 승인 대기)

        Args:
            file_path: 대상 파일 경로
            new_code: 새 코드 내용
            reason: 변경 이유

        Returns:
            change_id 또는 None (경로 불허)
        """
        # 경로 검증
        if not self._is_path_allowed(file_path):
            log_error(f"[StrategyModifier] 허용되지 않은 경로: {file_path}")
            return None

        # 원본 코드 읽기
        original_code = ""
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    original_code = f.read()
            except Exception as e:
                log_error(f"[StrategyModifier] 원본 파일 읽기 실패: {e}")
                return None

        # 백업 생성
        change_id = str(uuid.uuid4())[:8]
        backup_path = os.path.join(
            self._backup_dir,
            f"{change_id}_{os.path.basename(file_path)}.bak"
        )

        if original_code:
            try:
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(original_code)
            except Exception as e:
                log_error(f"[StrategyModifier] 백업 생성 실패: {e}")
                return None

        # 변경 사항 저장
        self._pending_changes[change_id] = {
            "change_id": change_id,
            "file_path": file_path,
            "original_code": original_code,
            "new_code": new_code,
            "backup_path": backup_path,
            "reason": reason,
            "proposed_at": datetime.now().isoformat(),
            "status": "pending",
        }

        log_system(f"[StrategyModifier] 코드 변경 제안 등록: {change_id} ({file_path})")
        return change_id

    def apply_code_change(self, change_id: str) -> bool:
        """
        Monitor 승인 후 코드 변경 적용

        Args:
            change_id: 변경 ID

        Returns:
            성공 여부
        """
        change = self._pending_changes.get(change_id)
        if not change:
            log_error(f"[StrategyModifier] 변경 ID를 찾을 수 없음: {change_id}")
            return False

        if change["status"] != "pending":
            log_error(f"[StrategyModifier] 이미 처리된 변경: {change_id} ({change['status']})")
            return False

        try:
            # 디렉토리 생성 (필요시)
            dir_path = os.path.dirname(change["file_path"])
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with open(change["file_path"], "w", encoding="utf-8") as f:
                f.write(change["new_code"])

            change["status"] = "applied"
            change["applied_at"] = datetime.now().isoformat()
            self._applied_changes.append(change)
            del self._pending_changes[change_id]

            log_system(f"[StrategyModifier] ✅ 코드 변경 적용: {change_id}")
            return True

        except Exception as e:
            log_error(f"[StrategyModifier] 코드 변경 적용 실패: {e}")
            return False

    def rollback_code_change(self, change_id: str) -> bool:
        """
        코드 변경 롤백

        Args:
            change_id: 변경 ID

        Returns:
            성공 여부
        """
        # 보류 중인 변경 거부
        if change_id in self._pending_changes:
            self._pending_changes[change_id]["status"] = "rejected"
            del self._pending_changes[change_id]
            log_system(f"[StrategyModifier] 코드 변경 거부: {change_id}")
            return True

        # 적용된 변경 롤백
        for change in self._applied_changes:
            if change["change_id"] == change_id and change["status"] == "applied":
                try:
                    backup_path = change["backup_path"]
                    if os.path.exists(backup_path):
                        shutil.copy2(backup_path, change["file_path"])
                        change["status"] = "rolled_back"
                        log_system(f"[StrategyModifier] 🔄 코드 변경 롤백: {change_id}")
                        return True
                    else:
                        log_error(f"[StrategyModifier] 백업 파일 없음: {backup_path}")
                        return False
                except Exception as e:
                    log_error(f"[StrategyModifier] 롤백 실패: {e}")
                    return False

        log_error(f"[StrategyModifier] 변경 ID를 찾을 수 없음: {change_id}")
        return False

    def list_pending_changes(self) -> List[Dict]:
        """보류 중인 변경 목록"""
        return list(self._pending_changes.values())

    def _is_path_allowed(self, file_path: str) -> bool:
        """파일 경로가 허용 범위인지 확인"""
        normalized = file_path.replace("\\", "/")
        for allowed in self._allowed_paths:
            if normalized.startswith(allowed) or f"/{allowed}" in normalized:
                return True
        return False

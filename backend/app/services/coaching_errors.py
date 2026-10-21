"""코칭 provider 실패를 HTTP와 관측 상태로 옮기기 위한 예외."""


class CoachingProviderError(RuntimeError):
    """사용자 입력과 무관한 코칭 provider 실패."""


class CoachingTimeoutError(CoachingProviderError):
    """모델 또는 도구 호출이 제한 시간을 넘겼다."""


class CoachingCreditsError(CoachingProviderError):
    """모델 제공자의 크레딧 또는 키 사용 한도가 부족하다."""


class CoachingRateLimitError(CoachingProviderError):
    """모델 provider가 요청 빈도 제한을 반환했다."""

    def __init__(self, retry_after_seconds: int | None = None) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("coaching provider rate limited")


class CoachingBudgetExceededError(CoachingProviderError):
    """provider가 보고한 요청 누적 비용이 설정 상한을 넘었다."""

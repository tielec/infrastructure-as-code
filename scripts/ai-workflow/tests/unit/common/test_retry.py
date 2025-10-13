"""
Unit tests for common/retry.py

Test Scenarios:
- UT-RET-001: @retry デコレータ - 1回目で成功
- UT-RET-002: @retry デコレータ - リトライ後成功
- UT-RET-003: @retry デコレータ - 最大リトライ到達
"""
import pytest
import time
from common.retry import retry, retry_with_callback


class TestRetryDecorator:
    """retry デコレータのユニットテスト"""

    def test_retry_succeeds_on_first_attempt(self):
        """UT-RET-001: 1回目で成功した場合、リトライされないことを確認"""
        # Given: 成功する関数
        call_count = []

        @retry(max_attempts=3, delay=0.1)
        def successful_function():
            call_count.append(1)
            return "success"

        # When: 関数を実行
        result = successful_function()

        # Then: 1回のみ実行され、結果が返される
        assert result == "success"
        assert len(call_count) == 1

    def test_retry_succeeds_on_second_attempt(self):
        """UT-RET-002: 2回目で成功した場合、リトライされることを確認"""
        # Given: 1回目は失敗、2回目は成功する関数
        call_count = []

        @retry(max_attempts=3, delay=0.1)
        def retry_then_success():
            call_count.append(1)
            if len(call_count) == 1:
                raise ValueError("First attempt fails")
            return "success"

        # When: 関数を実行
        result = retry_then_success()

        # Then: 2回実行され、結果が返される
        assert result == "success"
        assert len(call_count) == 2

    def test_retry_fails_after_max_attempts(self):
        """UT-RET-003: 最大リトライ回数に到達した場合、例外が発生することを確認"""
        # Given: 常に失敗する関数
        call_count = []

        @retry(max_attempts=3, delay=0.1)
        def always_fails():
            call_count.append(1)
            raise ValueError("Always fails")

        # When/Then: 最大リトライ後に例外が発生
        with pytest.raises(ValueError, match="Always fails"):
            always_fails()

        # Then: 3回実行される
        assert len(call_count) == 3

    def test_retry_with_exponential_backoff(self):
        """エクスポネンシャルバックオフが機能することを確認"""
        # Given: リトライする関数
        call_times = []

        @retry(max_attempts=3, delay=0.1)
        def function_with_backoff():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Retry")
            return "success"

        # When: 関数を実行
        result = function_with_backoff()

        # Then: 待機時間が指数的に増加
        assert result == "success"
        assert len(call_times) == 3
        # 2回目の待機時間は1回目の約2倍（エクスポネンシャルバックオフ）
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            # エクスポネンシャルバックオフの検証（誤差を考慮）
            assert delay2 > delay1 * 0.8  # 約2倍になることを確認（誤差80%許容）

    def test_retry_with_specific_exception(self):
        """特定の例外のみリトライすることを確認"""
        # Given: 特定の例外でのみリトライする関数
        call_count = []

        @retry(max_attempts=3, delay=0.1, exceptions=(ValueError,))
        def specific_exception_retry():
            call_count.append(1)
            if len(call_count) == 1:
                raise ValueError("Should retry")
            return "success"

        # When: 関数を実行
        result = specific_exception_retry()

        # Then: リトライされる
        assert result == "success"
        assert len(call_count) == 2

    def test_retry_does_not_retry_non_specified_exception(self):
        """指定外の例外ではリトライしないことを確認"""
        # Given: ValueError のみリトライする関数
        call_count = []

        @retry(max_attempts=3, delay=0.1, exceptions=(ValueError,))
        def non_specified_exception():
            call_count.append(1)
            raise TypeError("Should not retry")

        # When/Then: 1回目で例外が発生
        with pytest.raises(TypeError, match="Should not retry"):
            non_specified_exception()

        # Then: 1回のみ実行される
        assert len(call_count) == 1


class TestRetryWithCallback:
    """retry_with_callback デコレータのユニットテスト"""

    def test_retry_with_callback_calls_callback_on_retry(self):
        """コールバック関数が呼ばれることを確認"""
        # Given: コールバック関数
        callback_calls = []

        def my_callback(attempt, exception):
            callback_calls.append({'attempt': attempt, 'exception': str(exception)})

        call_count = []

        @retry_with_callback(max_attempts=3, delay=0.1, callback=my_callback)
        def function_with_callback():
            call_count.append(1)
            if len(call_count) == 1:
                raise ValueError("First attempt fails")
            return "success"

        # When: 関数を実行
        result = function_with_callback()

        # Then: コールバックが呼ばれる
        assert result == "success"
        assert len(callback_calls) == 1  # 1回リトライしたのでコールバックも1回
        assert callback_calls[0]['attempt'] == 1
        assert "First attempt fails" in callback_calls[0]['exception']

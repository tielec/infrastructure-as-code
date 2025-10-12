"""Retry - リトライロジックの共通化モジュール

このモジュールは、プロジェクト全体で統一されたリトライロジックを提供します。

機能:
    - @retry デコレータによる自動リトライ
    - リトライ回数・間隔の設定
    - エクスポネンシャルバックオフの実装
    - リトライ対象例外の指定

使用例:
    >>> from common.retry import retry
    >>> @retry(max_attempts=3, delay=2.0)
    >>> def api_call():
    ...     # API呼び出し処理
    ...     pass
"""

import time
import functools
from typing import Callable, Tuple, Type
from common.logger import Logger


logger = Logger.get_logger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """リトライデコレータ

    指定された回数まで処理をリトライします。
    各リトライの間には指定された遅延を挟みます。

    Args:
        max_attempts: 最大試行回数（デフォルト: 3）
        delay: 初回リトライ遅延時間（秒、デフォルト: 1.0）
        backoff: バックオフ係数（デフォルト: 2.0）
        exceptions: リトライ対象の例外タプル（デフォルト: すべての例外）

    Returns:
        Callable: デコレートされた関数

    Note:
        バックオフ係数が2.0の場合、遅延時間は以下のように増加します：
        - 1回目: delay秒
        - 2回目: delay * backoff秒
        - 3回目: delay * backoff^2秒

    Example:
        >>> @retry(max_attempts=3, delay=2.0, backoff=2.0)
        >>> def api_call():
        ...     # API呼び出し処理
        ...     pass

        >>> @retry(max_attempts=5, delay=1.0, exceptions=(TimeoutError, ConnectionError))
        >>> def network_operation():
        ...     # ネットワーク操作
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    # 関数実行
                    result = func(*args, **kwargs)

                    # 成功時はリトライ情報をログに記録（2回目以降の場合）
                    if attempt > 1:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt}/{max_attempts}"
                        )

                    return result

                except exceptions as e:
                    # 最後の試行の場合は例外を再発生
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts"
                        )
                        raise

                    # リトライログ出力
                    logger.warning(
                        f"{func.__name__} failed on attempt {attempt}/{max_attempts}: {e}. "
                        f"Retrying in {current_delay:.1f} seconds..."
                    )

                    # 遅延
                    time.sleep(current_delay)

                    # 次回の遅延時間を計算（エクスポネンシャルバックオフ）
                    current_delay *= backoff

        return wrapper
    return decorator


def retry_with_callback(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] = None
):
    """コールバック付きリトライデコレータ

    リトライ時にコールバック関数を呼び出します。

    Args:
        max_attempts: 最大試行回数
        delay: 初回リトライ遅延時間（秒）
        backoff: バックオフ係数
        exceptions: リトライ対象の例外タプル
        on_retry: リトライ時に呼び出すコールバック関数
                  (attempt: int, exception: Exception) -> None

    Returns:
        Callable: デコレートされた関数

    Example:
        >>> def handle_retry(attempt, exception):
        ...     print(f"Retry #{attempt}: {exception}")
        >>>
        >>> @retry_with_callback(max_attempts=3, on_retry=handle_retry)
        >>> def api_call():
        ...     # API呼び出し処理
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)

                    if attempt > 1:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt}/{max_attempts}"
                        )

                    return result

                except exceptions as e:
                    # 最後の試行の場合は例外を再発生
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts"
                        )
                        raise

                    # コールバック実行
                    if on_retry:
                        try:
                            on_retry(attempt, e)
                        except Exception as callback_error:
                            logger.error(f"Callback error: {callback_error}")

                    # リトライログ出力
                    logger.warning(
                        f"{func.__name__} failed on attempt {attempt}/{max_attempts}: {e}. "
                        f"Retrying in {current_delay:.1f} seconds..."
                    )

                    # 遅延
                    time.sleep(current_delay)

                    # 次回の遅延時間を計算
                    current_delay *= backoff

        return wrapper
    return decorator

import pytest

from radiofeed.thread_pool import execute_thread_pool


class TestExecuteThreadPool:
    def test_ok(self):
        def task(x):
            return x * 2

        inputs = [1, 2, 3, 4, 5]
        expected_outputs = [2, 4, 6, 8, 10]

        outputs = execute_thread_pool(task, inputs)
        assert set(outputs) == set(expected_outputs)

    def test_error_raise(self):
        def task(x):
            if x == 3:
                raise ValueError("Test error")
            return x * 2

        inputs = [1, 2, 3, 4, 5]

        with pytest.raises(ValueError, match="Test error"):
            execute_thread_pool(task, inputs, raise_exception=True)

    def test_error_do_not_raise(self):
        def task(x):
            if x == 3:
                raise ValueError("Test error")
            return x * 2

        inputs = [1, 2, 3, 4, 5]

        execute_thread_pool(task, inputs, raise_exception=False)

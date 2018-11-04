import unittest
import copy
import sys, os

sys.path.insert(0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.overbridge_connector import lambda_handler
from src.utils import retry, incrementing_sleep, fixed_sleep

del sys.path[0]


class TestLambda(unittest.TestCase):

    def setUp(self):
        self.event = {}
        with open("fixtures.json") as f:
            self.event['body'] = f.read()
        os.environ["AWS_REGION"] = "us-east-1"
        class Context:
            invoked_function_arn="arn:aws:lambda:us-east-1:956882708938:function:OverbridgeLambda"

        self.context = Context()

    def tearDown(self):
        pass

    def test_send_success(self):
        result = lambda_handler(self.event, self.context)
        self.assertEqual(result['statusCode'], 200)
        self.assertTrue(result['body'] == 'FailedCount: 0 SuccessCount: 3 StatusCode: 200 ', "%s body is not matching" % result['body'])

    def test_send_failure(self):
        event = copy.copy(self.event)
        event['body'] = event['body'].replace("2018-10-30T13:22:13", "1")
        result = lambda_handler(event, self.context)
        self.assertEqual(result['statusCode'], 200)
        self.assertTrue(result['body'] == 'FailedCount: 3 SuccessCount: 0 StatusCode: 200 ErrorMessage: Finding does not adhere to Amazon Finding Format. data.FirstObservedAt should match format "date-time", data.CreatedAt should match format "date-time", data.UpdatedAt should match format "date-time"', "%s body is not matching"% result['body'])

    def test_validation(self):
        event = copy.copy(self.event)
        event['body'] = event['body'].replace('\"Types\": \"Security\",', "")
        result = lambda_handler(event, self.context)
        self.assertEqual(result['statusCode'], 400)
        self.assertTrue(result['body'] == "Bad Request: 'Types Fields are missing'", "%s body is not matching" % result['body'])

    def test_retry(self):
        class Logger:
            def __init__(self):
                self.messages = []

            def warning(self, msg):
                self.messages.append(msg)
        logger1 = Logger()
        @retry(ExceptionToCheck=(KeyError,), max_retries=3, logger=logger1, handler_type=fixed_sleep, fixed_wait_time=2)
        def func():
            data = {}
            return data["key"]
        with self.assertRaises(Exception) as context:
            func()

        self.assertTrue(len(logger1.messages) == 2, "fixed_sleep(2) with 3 retries should contain 2 messages")

        logger2 = Logger()
        @retry(ExceptionToCheck=(ValueError,), max_retries=2, logger=logger2, handler_type=incrementing_sleep, wait_time_inc=2)
        def func():
            data = {}
            return data["key"]

        with self.assertRaises(Exception) as context:
            func()
        self.assertTrue(len(logger2.messages) == 0, "incremental_sleep(2) with 2 retries but with ValueError(retry not allowed)")


        logger3 = Logger()
        @retry(ExceptionToCheck=(KeyError,), max_retries=2, logger=logger3, handler_type=incrementing_sleep, wait_time_inc=2)
        def func():
            data = {}
            return data["key"]

        with self.assertRaises(Exception) as context:
            func()
        self.assertTrue(len(logger3.messages) == 1, "incremental_sleep(2) with 2 retries should contain 1 message")

if __name__ == '__main__':

    unittest.main()

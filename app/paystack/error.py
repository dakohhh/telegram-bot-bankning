class PaystackException(Exception):
    def __init__(self, message):
        self.message = message
        error_message = f"Paystack Exception: {message}"
        super().__init__(error_message)
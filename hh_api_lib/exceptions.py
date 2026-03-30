class HHCaptchaRequired(Exception):
    def __init__(self, captcha_url: str):
        self.captcha_url = captcha_url
        super().__init__(f"Captcha required: {captcha_url}")
class CrisisManager:
    """
    Handles urgent self-harm language before the chatbot sends the text to Gemini.
    """

    def __init__(self):
        self.crisis_keywords = [
            "suicide",
            "kill myself",
            "want to die",
            "end my life",
            "self harm",
            "self-harm",
            "hurt myself",
            "cutting",
            "no reason to live",
        ]
        self.crisis_response = (
            "It sounds like you are in serious distress. Your safety matters most right now.\n"
            "Please contact local emergency services if you are in immediate danger.\n\n"
            "If you are in India, Tele-MANAS offers 24/7 mental-health support at 14416 "
            "or 1800-89-14416. If you are elsewhere, contact your local crisis service.\n\n"
            "Please reach out to someone nearby or call a helpline now."
        )

    def check_for_crisis(self, user_input):
        text = user_input.lower()
        if any(keyword in text for keyword in self.crisis_keywords):
            return self.crisis_response
        return None

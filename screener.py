class Screener:
    """Manages conversational screening for anxiety using GAD-7."""

    def __init__(self):
        self.gad7_questions = [
            "Over the last 2 weeks, how often have you been bothered by feeling nervous, anxious, or on edge?",
            "How often have you not been able to stop or control worrying?",
            "How often have you been worrying too much about different things?",
            "How often have you had trouble relaxing?",
            "How often have you been so restless that it is hard to sit still?",
            "How often have you become easily annoyed or irritable?",
            "How often have you felt afraid as if something awful might happen?",
        ]
        self.is_active = False
        self.question_index = 0
        self.total_score = 0

    def start_screening(self):
        self.is_active = True
        self.question_index = 0
        self.total_score = 0
        return (
            "Okay, let's do a quick check-in. I'll ask 7 questions about how you've felt over the last 2 weeks.\n"
            "Please answer with a number: 0=Not at all, 1=Several days, "
            "2=More than half the days, 3=Nearly every day.\n\n"
            f"Question 1: {self.gad7_questions[0]}"
        )

    def process_input(self, user_input):
        try:
            score = int(user_input)
        except ValueError:
            return "That doesn't seem to be a valid number."

        if score < 0 or score > 3:
            return "Please enter a number between 0 and 3."

        self.total_score += score
        self.question_index += 1

        if self.question_index < len(self.gad7_questions):
            next_question = self.gad7_questions[self.question_index]
            return f"Question {self.question_index + 1}: {next_question}"

        self.is_active = False
        return self.interpret_result()

    def interpret_result(self):
        score = self.total_score
        if score >= 15:
            interpretation = "a high range on this anxiety symptom screening"
            next_step = "It may be a good idea to speak with a qualified mental health professional."
        elif score >= 10:
            interpretation = "a moderate range on this anxiety symptom screening"
            next_step = "Consider talking with a trusted person or mental health professional."
        elif score >= 5:
            interpretation = "a mild range on this anxiety symptom screening"
            next_step = "A grounding exercise, breathing practice, or journaling may help."
        else:
            interpretation = "a low range on this anxiety symptom screening"
            next_step = "Keep checking in with yourself and noticing what supports you."

        return (
            f"\nThanks for sharing. Your score is {score}, which falls in {interpretation}. "
            f"{next_step}\n"
            "Note: This is not a medical diagnosis."
        )

import re
import os

from chatbot import Chatbot, get_missing_dependencies
from config import get_gemini_api_key, load_dotenv_file
from users import UserManager


def get_validated_input(prompt, valid_options=None, input_type=str):
    while True:
        user_input = input(prompt).strip()
        if not user_input:
            print("Input cannot be empty.")
            continue

        if input_type == int and not user_input.isdigit():
            print("Please enter a valid number.")
            continue

        if valid_options:
            for option in valid_options:
                if user_input.lower() == option.lower():
                    return option
            print(f"Please choose one of: {', '.join(valid_options)}")
            continue

        return user_input


def get_valid_email(prompt):
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    while True:
        email = input(prompt).strip().lower()
        if re.match(email_regex, email):
            return email
        print("Invalid email format. Please enter a valid email, such as name@example.com.")


def login_or_register(user_manager):
    while True:
        print("\nHave you used UDAY before?")
        user_status = get_validated_input(
            "Enter 'yes' (Returning) or 'no' (New User): ",
            valid_options=["yes", "no", "y", "n"],
        )

        if user_status.lower() in ["yes", "y"]:
            email = get_valid_email("Please enter your registered Email ID: ")
            user_data = user_manager.get_user(email)
            if user_data:
                print(f"\nWelcome back, {user_data['name']}! Loading your personal history...")
                return email, user_data

            print("I couldn't find an account with that email. Please try again or type 'no' to register.")
            continue

        print("\n--- NEW USER REGISTRATION ---")
        email = get_valid_email("Please enter your Email ID: ")
        existing_user_data = user_manager.get_user(email)
        if existing_user_data:
            print(f"\n[System Info]: The email '{email}' is already registered.")
            print(
                f"Welcome back, {existing_user_data['name']}. "
                "I'm skipping registration and taking you straight to chat."
            )
            return email, existing_user_data

        name = get_validated_input("What should I call you? ")
        age = get_validated_input("How old are you? ", input_type=int)
        gender = get_validated_input(
            "Gender (Male/Female/Other): ",
            valid_options=["Male", "Female", "Other"],
        )

        print("Which category best describes your occupation?")
        profession = get_validated_input(
            "Choose (Student, Corporate, Worker, Homemaker, Other): ",
            valid_options=["Student", "Corporate", "Worker", "Homemaker", "Other"],
        )
        focus = get_validated_input("Main focus? (e.g., Anxiety, Work Stress): ")

        user_data = user_manager.register_user(email, name, age, gender, profession, focus)
        print("\nRegistration complete! Setting up your personal space...")
        return email, user_data


def main():
    load_dotenv_file()
    if os.getenv("DATABASE_URL", "").startswith(("postgres://", "postgresql://", "postgresql+")):
        print("The CLI is for local SQLite development and cannot register passwordless accounts in hosted PostgreSQL.")
        return
    missing_dependencies = get_missing_dependencies()
    if missing_dependencies:
        print(
            "\nStartup error: missing Python package(s): "
            + ", ".join(missing_dependencies)
        )
        print("Install them with: python -m pip install -r requirements.txt")
        return

    api_key = get_gemini_api_key()
    user_manager = UserManager()

    print("\n" + "=" * 30)
    print("      WELCOME TO UDAY      ")
    print("=" * 30)

    current_email, current_user_profile = login_or_register(user_manager)
    try:
        bot = Chatbot(api_key, current_email, current_user_profile)
    except RuntimeError as error:
        print(f"\nStartup error: {error}")
        return

    print(
        f"\nUDAY: Hello {current_user_profile['name']}. "
        "I'm ready to listen. Type SCREENING to check your anxiety levels."
    )

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nUDAY: Goodbye.")
            break

        if user_input.lower() in ["quit", "exit", "bye"]:
            print("UDAY: One moment, if you want to talk again I am here to help you.")
            bot.save_long_term_memory()
            print("UDAY: Take care.")
            break

        if not user_input:
            continue

        crisis_response = bot.crisis_manager.check_for_crisis(user_input)
        if crisis_response:
            print(f"UDAY: {crisis_response}")
            bot.screener.is_active = False
            continue

        response = bot.get_response(user_input)
        print(f"UDAY: {response}")


if __name__ == "__main__":
    main()

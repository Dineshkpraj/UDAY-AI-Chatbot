import json
import math
import re

from sqlalchemy import delete, select

from database import MemoryFact, get_session_factory, initialize_database


_STOP_WORDS = {
    "a", "about", "after", "again", "all", "also", "am", "an", "and", "any",
    "are", "as", "at", "be", "because", "been", "before", "being", "but", "by",
    "can", "could", "did", "do", "does", "doing", "for", "from", "had", "has",
    "have", "he", "her", "here", "hers", "him", "his", "how", "i", "if", "in",
    "into", "is", "it", "its", "just", "me", "my", "of", "on", "or", "our",
    "ours", "she", "should", "so", "some", "than", "that", "the", "their", "them",
    "then", "there", "these", "they", "this", "those", "to", "up", "us", "was",
    "we", "were", "what", "when", "where", "which", "who", "why", "will", "with",
    "would", "you", "your", "yours",
}


def _terms(text):
    return [
        token for token in re.findall(r"[a-z0-9']+", text.lower())
        if len(token) > 1 and token not in _STOP_WORDS
    ]


def rank_relevant_facts(facts, query, limit=5):
    """Rank facts by local TF-IDF cosine similarity; return only positive matches."""
    if not facts or limit <= 0:
        return []
    fact_terms = [_terms(fact) for fact in facts]
    query_terms = _terms(query)
    if not query_terms:
        return []

    document_frequency = {}
    for terms in fact_terms:
        for term in set(terms):
            document_frequency[term] = document_frequency.get(term, 0) + 1
    document_count = len(facts)

    def vectorize(terms):
        counts = {}
        for term in terms:
            counts[term] = counts.get(term, 0) + 1
        weighted = {
            term: count * (math.log((document_count + 1) / (document_frequency.get(term, 0) + 1)) + 1)
            for term, count in counts.items()
        }
        magnitude = math.sqrt(sum(weight * weight for weight in weighted.values()))
        if magnitude:
            return {term: weight / magnitude for term, weight in weighted.items()}
        return {}

    query_vector = vectorize(query_terms)
    ranked = []
    for index, terms in enumerate(fact_terms):
        fact_vector = vectorize(terms)
        score = sum(weight * fact_vector.get(term, 0.0) for term, weight in query_vector.items())
        if score > 0:
            ranked.append((score, index, facts[index]))
    ranked.sort(key=lambda result: (-result[0], result[1]))
    return [fact for _, _, fact in ranked[:limit]]


class MemoryManager:
    """Stores user-approved long-term facts in the configured SQL database."""

    def __init__(self, model, user_email):
        self.model = model
        self.user_email = user_email.lower()

    def get_facts(self):
        initialize_database()
        with get_session_factory()() as session:
            rows = session.scalars(
                select(MemoryFact)
                .where(MemoryFact.email == self.user_email)
                .order_by(MemoryFact.id)
            ).all()
            return [row.fact for row in rows]

    def load_memory(self):
        return "\n".join(f"- {fact}" for fact in self.get_facts())

    def get_relevant_facts(self, query, limit=5):
        return rank_relevant_facts(self.get_facts(), query, limit=limit)

    def replace_facts(self, facts):
        initialize_database()
        with get_session_factory()() as session, session.begin():
            session.execute(delete(MemoryFact).where(MemoryFact.email == self.user_email))
            session.add_all(
                MemoryFact(email=self.user_email, fact=fact.strip())
                for fact in facts
            )

    def delete_fact(self, index):
        facts = self.get_facts()
        if index < 0 or index >= len(facts):
            return False
        del facts[index]
        self.replace_facts(facts)
        return True

    def clear(self):
        self.replace_facts([])

    def update_memory(self, recent_conversation_text):
        """Suggest lasting facts, then save them only with explicit user approval."""
        if self.model is None:
            return
        existing_facts = self.get_facts()
        prompt = f"""
        Extract PERMANENT facts about the user, such as stable preferences, fears, job details,
        or important names. Do not save temporary mood states.
        Existing Knowledge: {existing_facts}
        New Conversation: {recent_conversation_text}
        Output: JSON list of new distinct strings only. If none, output "NO_NEW_INFO".
        """

        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            if "NO_NEW_INFO" in clean_text:
                return

            new_facts = json.loads(clean_text)
            if not isinstance(new_facts, list):
                return
            reviewed_facts = list(dict.fromkeys(
                fact.strip()
                for fact in new_facts
                if isinstance(fact, str) and fact.strip()
            ))
            reviewed_facts = [fact for fact in reviewed_facts if fact not in existing_facts]
            if not reviewed_facts:
                return

            print("\nPossible memories for you to review:")
            for index, fact in enumerate(reviewed_facts, start=1):
                print(f"  {index}. {fact}")
            approval = input("Save these memories? (yes/no): ").strip().lower()
            if approval not in {"yes", "y"}:
                print("[System] No new memories were saved.")
                return
            self.replace_facts(existing_facts + reviewed_facts)
            print(f"[System] UDAY saved {len(reviewed_facts)} reviewed memories.")
        except (json.JSONDecodeError, OSError, AttributeError, ValueError) as error:
            print(f"[System] Memory update skipped: {error}")

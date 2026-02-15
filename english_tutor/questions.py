"""Question bank for the English Tutor Bot.

Contains questions organized by category, each with:
- The question text
- The correct answer(s) (multiple accepted forms)
- An explanation for the correct answer
- Difficulty level (easy, medium, hard)
"""

import random


# Each question is a dict with keys:
#   "question": str
#   "answers": list[str]  -- all acceptable answers (lowercase)
#   "explanation": str
#   "difficulty": str  -- "easy", "medium", "hard"

CATEGORIES = {
    "Grammar": [
        {
            "question": "Fill in the blank: She ___ to the store yesterday.",
            "answers": ["went"],
            "explanation": "'Went' is the past tense of 'go'. We use past tense because 'yesterday' indicates a completed action.",
            "difficulty": "easy",
        },
        {
            "question": "Fill in the blank: If I ___ rich, I would travel the world.",
            "answers": ["were", "was"],
            "explanation": "In the second conditional (hypothetical), we use 'were' for all subjects. 'Was' is also accepted in informal speech.",
            "difficulty": "medium",
        },
        {
            "question": "Fill in the blank: By next year, I ___ here for ten years.",
            "answers": ["will have worked", "will have been working"],
            "explanation": "The future perfect or future perfect continuous is used for actions that will be completed by a specific future time.",
            "difficulty": "hard",
        },
        {
            "question": "Fill in the blank: Neither the teacher nor the students ___ ready.",
            "answers": ["were"],
            "explanation": "With 'neither...nor', the verb agrees with the subject closest to it. 'Students' is plural, so we use 'were'.",
            "difficulty": "medium",
        },
        {
            "question": "Fill in the blank: She asked me where I ___.",
            "answers": ["lived", "live"],
            "explanation": "In reported speech, the tense often shifts back. 'Live' becomes 'lived'. However, 'live' is also acceptable if the situation is still true.",
            "difficulty": "medium",
        },
        {
            "question": "Fill in the blank: I wish I ___ harder for the exam.",
            "answers": ["had studied", "had worked"],
            "explanation": "'I wish' + past perfect expresses regret about a past action. 'Had studied' shows the action didn't happen.",
            "difficulty": "hard",
        },
        {
            "question": "Fill in the blank: He is one of those people who ___ always late.",
            "answers": ["are"],
            "explanation": "The relative pronoun 'who' refers to 'people' (plural), so the verb should be 'are'.",
            "difficulty": "hard",
        },
        {
            "question": "Fill in the blank: The book ___ on the table right now.",
            "answers": ["is"],
            "explanation": "'Is' is the correct present tense form of 'be' for a singular subject 'the book'.",
            "difficulty": "easy",
        },
        {
            "question": "Which is correct: 'less people' or 'fewer people'?",
            "answers": ["fewer people"],
            "explanation": "'Fewer' is used with countable nouns (people), while 'less' is used with uncountable nouns (water, time).",
            "difficulty": "medium",
        },
        {
            "question": "Fill in the blank: She ___ TV when the phone rang.",
            "answers": ["was watching"],
            "explanation": "Past continuous ('was watching') describes an ongoing action that was interrupted by another event ('the phone rang').",
            "difficulty": "easy",
        },
    ],
    "Vocabulary": [
        {
            "question": "What is a synonym of 'happy'?",
            "answers": ["glad", "joyful", "cheerful", "content", "pleased", "delighted", "elated", "merry", "jovial", "ecstatic"],
            "explanation": "There are many synonyms for 'happy' including glad, joyful, cheerful, content, pleased, and delighted.",
            "difficulty": "easy",
        },
        {
            "question": "What is the opposite of 'generous'?",
            "answers": ["stingy", "selfish", "greedy", "miserly", "mean", "tight"],
            "explanation": "The opposite of generous includes words like stingy, selfish, greedy, or miserly.",
            "difficulty": "easy",
        },
        {
            "question": "What does the word 'ubiquitous' mean?",
            "answers": ["found everywhere", "present everywhere", "everywhere", "existing everywhere", "omnipresent"],
            "explanation": "'Ubiquitous' means present, appearing, or found everywhere. Example: 'Smartphones have become ubiquitous.'",
            "difficulty": "hard",
        },
        {
            "question": "What does the word 'benevolent' mean?",
            "answers": ["kind", "generous", "well meaning", "well-meaning", "kindly", "charitable"],
            "explanation": "'Benevolent' means well-meaning and kindly. It comes from Latin 'bene' (well) and 'volent' (wishing).",
            "difficulty": "medium",
        },
        {
            "question": "What is the noun form of the adjective 'brave'?",
            "answers": ["bravery", "braveness", "courage"],
            "explanation": "The noun form of 'brave' is 'bravery'. 'Courage' is also related but comes from a different root.",
            "difficulty": "easy",
        },
        {
            "question": "What does the idiom 'break the ice' mean?",
            "answers": ["start a conversation", "make people feel comfortable", "ease the tension", "initiate conversation", "relieve tension"],
            "explanation": "'Break the ice' means to initiate conversation or make people feel more comfortable in a social situation.",
            "difficulty": "medium",
        },
        {
            "question": "What does 'procrastinate' mean?",
            "answers": ["delay", "postpone", "put off", "defer"],
            "explanation": "'Procrastinate' means to delay or postpone action, especially habitually. Example: 'Stop procrastinating and finish your homework.'",
            "difficulty": "medium",
        },
        {
            "question": "What is the adjective form of the noun 'beauty'?",
            "answers": ["beautiful"],
            "explanation": "The adjective form of 'beauty' is 'beautiful'.",
            "difficulty": "easy",
        },
        {
            "question": "What does 'ephemeral' mean?",
            "answers": ["short-lived", "temporary", "fleeting", "brief", "transient", "short lived"],
            "explanation": "'Ephemeral' means lasting for a very short time. Example: 'The ephemeral beauty of cherry blossoms.'",
            "difficulty": "hard",
        },
        {
            "question": "What does the phrase 'a piece of cake' mean?",
            "answers": ["easy", "very easy", "something easy", "simple"],
            "explanation": "'A piece of cake' is an idiom meaning something is very easy to do.",
            "difficulty": "easy",
        },
    ],
    "Pronunciation": [
        {
            "question": "How many syllables are in the word 'beautiful'?",
            "answers": ["3", "three"],
            "explanation": "'Beautiful' has 3 syllables: beau-ti-ful.",
            "difficulty": "easy",
        },
        {
            "question": "Which word has a silent letter: 'knife', 'cat', or 'dog'?",
            "answers": ["knife"],
            "explanation": "'Knife' has a silent 'k'. The 'k' is not pronounced; we say it as 'nife'.",
            "difficulty": "easy",
        },
        {
            "question": "How many syllables are in the word 'communication'?",
            "answers": ["5", "five"],
            "explanation": "'Communication' has 5 syllables: com-mu-ni-ca-tion.",
            "difficulty": "medium",
        },
        {
            "question": "Which word has a silent 'b': 'climb', 'cabin', or 'urban'?",
            "answers": ["climb"],
            "explanation": "In 'climb', the 'b' at the end is silent. We pronounce it as 'clime'.",
            "difficulty": "easy",
        },
        {
            "question": "In the word 'colonel', what letter combination is silent?",
            "answers": ["lo", "olo"],
            "explanation": "'Colonel' is pronounced 'kernel'. The 'olo' combination is not pronounced as expected.",
            "difficulty": "hard",
        },
        {
            "question": "How many syllables are in the word 'entrepreneur'?",
            "answers": ["4", "four"],
            "explanation": "'Entrepreneur' has 4 syllables: en-tre-pre-neur.",
            "difficulty": "medium",
        },
        {
            "question": "Which word rhymes with 'though': 'through', 'go', or 'cough'?",
            "answers": ["go"],
            "explanation": "'Though' rhymes with 'go'. English spelling can be deceptive - 'ough' has many different pronunciations.",
            "difficulty": "medium",
        },
        {
            "question": "Does the word 'read' in past tense rhyme with 'red' or 'reed'?",
            "answers": ["red"],
            "explanation": "The past tense 'read' (pronounced 'red') rhymes with 'red'. The present tense 'read' rhymes with 'reed'.",
            "difficulty": "medium",
        },
    ],
    "Sentence Correction": [
        {
            "question": "Correct this sentence: 'Me and him went to the park.'",
            "answers": ["he and i went to the park"],
            "explanation": "Use subject pronouns ('He and I') as the subject of a sentence, not object pronouns ('me and him').",
            "difficulty": "easy",
        },
        {
            "question": "Correct this sentence: 'Their going to there house over they're.'",
            "answers": ["they're going to their house over there"],
            "explanation": "'They're' = they are, 'their' = possessive, 'there' = location. This is one of the most common errors in English.",
            "difficulty": "easy",
        },
        {
            "question": "Correct this sentence: 'The team have won the match.'",
            "answers": ["the team has won the match"],
            "explanation": "In American English, collective nouns like 'team' take singular verbs: 'has' instead of 'have'. (Note: British English accepts 'have' here.)",
            "difficulty": "medium",
        },
        {
            "question": "Correct this sentence: 'I could of done better.'",
            "answers": ["i could have done better"],
            "explanation": "'Could of' is incorrect. The correct form is 'could have' (often contracted to 'could've', which sounds like 'could of').",
            "difficulty": "easy",
        },
        {
            "question": "Correct this sentence: 'Between you and I, this is wrong.'",
            "answers": ["between you and me, this is wrong", "between you and me this is wrong"],
            "explanation": "After prepositions like 'between', use object pronouns: 'me' instead of 'I'.",
            "difficulty": "medium",
        },
        {
            "question": "Correct this sentence: 'Each of the students have their own book.'",
            "answers": ["each of the students has their own book", "each of the students has his or her own book"],
            "explanation": "'Each' is singular, so it takes 'has'. 'Their' is widely accepted as a gender-neutral singular pronoun.",
            "difficulty": "hard",
        },
        {
            "question": "Correct this sentence: 'She don't like chocolate.'",
            "answers": ["she doesn't like chocolate", "she does not like chocolate"],
            "explanation": "Third person singular ('she') requires 'doesn't' (does not), not 'don't' (do not).",
            "difficulty": "easy",
        },
        {
            "question": "Correct this sentence: 'The amount of people at the concert was huge.'",
            "answers": ["the number of people at the concert was huge"],
            "explanation": "Use 'number' with countable nouns (people) and 'amount' with uncountable nouns (water, money).",
            "difficulty": "medium",
        },
    ],
    "Reading Comprehension": [
        {
            "question": "In the sentence 'The bank was steep and muddy', does 'bank' refer to a financial institution or the side of a river?",
            "answers": ["the side of a river", "side of a river", "river", "river bank", "riverbank"],
            "explanation": "Context clues 'steep and muddy' indicate this is a river bank, not a financial institution.",
            "difficulty": "easy",
        },
        {
            "question": "What does 'it's raining cats and dogs' mean? Is it literal or figurative?",
            "answers": ["figurative", "it means raining heavily", "raining heavily", "heavy rain"],
            "explanation": "It's figurative - an idiom meaning it's raining very heavily. No animals are actually falling from the sky!",
            "difficulty": "easy",
        },
        {
            "question": "'Despite the rain, she went for a walk.' Did the rain stop her?",
            "answers": ["no"],
            "explanation": "'Despite' means 'in spite of' or 'regardless of'. The rain did NOT stop her - she went for a walk anyway.",
            "difficulty": "easy",
        },
        {
            "question": "'He was over the moon when he got the job.' How did he feel?",
            "answers": ["happy", "very happy", "extremely happy", "excited", "thrilled", "delighted", "ecstatic", "overjoyed"],
            "explanation": "'Over the moon' is an idiom meaning extremely happy or delighted.",
            "difficulty": "easy",
        },
        {
            "question": "In 'She let the cat out of the bag', what does this idiom mean?",
            "answers": ["revealed a secret", "told a secret", "gave away a secret", "disclosed a secret", "spilled the beans"],
            "explanation": "'Let the cat out of the bag' means to reveal a secret or surprise, usually accidentally.",
            "difficulty": "medium",
        },
        {
            "question": "'The project was a white elephant.' Does this mean the project was valuable or a burden?",
            "answers": ["a burden", "burden", "costly burden", "wasteful"],
            "explanation": "A 'white elephant' refers to something costly to maintain but of little practical use - it's a burden, not valuable.",
            "difficulty": "hard",
        },
    ],
    "Tenses": [
        {
            "question": "Convert to present perfect: 'I eat breakfast.'",
            "answers": ["i have eaten breakfast"],
            "explanation": "Present perfect is formed with 'have/has' + past participle. 'Eat' becomes 'have eaten'.",
            "difficulty": "easy",
        },
        {
            "question": "Convert to past perfect: 'She finishes her work.'",
            "answers": ["she had finished her work"],
            "explanation": "Past perfect is formed with 'had' + past participle. 'Finishes' becomes 'had finished'.",
            "difficulty": "medium",
        },
        {
            "question": "What tense is this sentence: 'They will have been studying for three hours.'?",
            "answers": ["future perfect continuous", "future perfect progressive"],
            "explanation": "'Will have been' + present participle (-ing) is the future perfect continuous tense, describing duration of an action up to a future point.",
            "difficulty": "hard",
        },
        {
            "question": "Fill in the blank with the correct tense: 'I ___ (study) English for five years now.'",
            "answers": ["have been studying", "have studied"],
            "explanation": "Present perfect continuous ('have been studying') emphasizes the ongoing nature. Present perfect ('have studied') is also acceptable.",
            "difficulty": "medium",
        },
        {
            "question": "Convert to future tense: 'She writes a letter.'",
            "answers": ["she will write a letter", "she is going to write a letter"],
            "explanation": "Future tense can be formed with 'will + base verb' or 'is going to + base verb'.",
            "difficulty": "easy",
        },
        {
            "question": "What tense is: 'He had been waiting for two hours when she arrived.'?",
            "answers": ["past perfect continuous", "past perfect progressive"],
            "explanation": "'Had been' + present participle (-ing) is the past perfect continuous, describing an action's duration before another past action.",
            "difficulty": "hard",
        },
        {
            "question": "Fill in the blank: 'By the time you arrive, I ___ (leave) already.'",
            "answers": ["will have left", "will have already left"],
            "explanation": "Future perfect ('will have left') is used for actions completed before a specific future time.",
            "difficulty": "medium",
        },
        {
            "question": "Convert to simple past: 'They are playing football.'",
            "answers": ["they played football", "they were playing football"],
            "explanation": "Simple past: 'They played football.' Note: 'They were playing' is past continuous, which is different.",
            "difficulty": "easy",
        },
    ],
}

ALL_CATEGORY_NAMES = list(CATEGORIES.keys())


def get_categories():
    """Return list of available category names."""
    return ALL_CATEGORY_NAMES


def get_questions(category, difficulty=None, count=None):
    """Get questions for a category, optionally filtered by difficulty.

    Args:
        category: Category name (must be in CATEGORIES).
        difficulty: Optional filter - "easy", "medium", or "hard".
        count: Optional max number of questions to return.

    Returns:
        List of question dicts, shuffled randomly.
    """
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}. Available: {ALL_CATEGORY_NAMES}")

    questions = CATEGORIES[category][:]

    if difficulty:
        questions = [q for q in questions if q["difficulty"] == difficulty]

    random.shuffle(questions)

    if count and count < len(questions):
        questions = questions[:count]

    return questions


def check_answer(question_dict, user_answer):
    """Check if the user's answer matches any of the accepted answers.

    Uses fuzzy matching: lowercased, stripped, and checks if any accepted
    answer is contained within the user's response (or vice versa).

    Args:
        question_dict: A question dict from the bank.
        user_answer: The user's answer string.

    Returns:
        Tuple of (is_correct: bool, explanation: str)
    """
    user_clean = user_answer.strip().lower()

    # Remove common filler words and punctuation
    for filler in ["the answer is", "i think it's", "i think it is", "it's", "it is", "i believe"]:
        if user_clean.startswith(filler):
            user_clean = user_clean[len(filler):].strip()

    user_clean = user_clean.strip(".,!?;:'\"")

    accepted = question_dict["answers"]

    for ans in accepted:
        ans_lower = ans.lower()
        # Exact match
        if user_clean == ans_lower:
            return True, question_dict["explanation"]
        # User's answer contains the correct answer
        if ans_lower in user_clean:
            return True, question_dict["explanation"]
        # Correct answer contains the user's short answer
        if len(user_clean) >= 3 and user_clean in ans_lower:
            return True, question_dict["explanation"]

    return False, question_dict["explanation"]

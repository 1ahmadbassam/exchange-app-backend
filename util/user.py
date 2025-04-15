from password_strength import PasswordPolicy
from password_strength.tests import Uppercase, Length, Numbers, Special, Strength, EntropyBits

USER_FORBIDDEN_CHARACTERS = [
    '_', '@', '&', '!', '?', '%', '#', '$', '^', '*', '(', ')', '+', '=', '{', '}', '[', ']', ':', ';',
    '"', "'", '<', '>', '/', '\\', '|', '`', '~', ',', '.', '£', '€', '©', '®', '™', '°', '©', '•', '§',
    '€', '²', '³', '¶', '¤', '°', '¬', '¸', '¦', '¥', '♦', '♣', '♠', '♥', '♦', '♪', '♫', '☼', '★', '☆'
]

PASSWORD_FORBIDDEN_CHARACTERS = [
    '£', '€', '©', '®', '™', '°', '©', '•', '§', '²', '³', '¶', '¤', '¬', '¸', '¦', '¥', '♦',
    '♣', '♠', '♥', '♦', '♪', '♫', '☼', '★', '☆', '˙', '¬', '¡', '¿', '·', '¬', '®', '†', '‡'
]

policy = PasswordPolicy.from_names(
    length=12,
    uppercase=2,
    numbers=2,
    special=1,
    strength=0.4,
    entropybits=70  # 70 bits of entropy is a fair compromise between alphabetical, numeric, and ASCII characters
)


def test_password(password):
    tests = policy.test(password)
    hh = []
    for test in tests:
        if type(test) == Length:
            hh.append("Password must be at least " + str(test.length) + " characters long.")
        elif type(test) == Uppercase:
            hh.append(str(test.count) + " uppercase characters required.")
        elif type(test) == Numbers:
            hh.append(str(test.count) + " numbers required.")
        elif type(test) == Special:
            hh.append(str(test.count) + " symbols required (any of ~!@#$%^&*()_+).")
        elif type(test) == Strength:
            hh.append("Password too weak.")
        elif type(test) == EntropyBits:
            hh.append("Password does not have enough variability.")
    return hh

from django.contrib.auth.tokens import PasswordResetTokenGenerator


# generates tokens
class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return str(user.pk) + str(timestamp)


generate_token = TokenGenerator()

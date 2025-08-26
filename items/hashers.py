# items/hashers.py

import hashlib
from django.contrib.auth.hashers import BasePasswordHasher
from django.utils.crypto import constant_time_compare
from django.utils.translation import gettext_noop as _


class SHA512PasswordHasher(BasePasswordHasher):
    """
    Autenticación usando SHA-512.
    """

    algorithm = "sha512"

    def encode(self, password, salt):
        assert password is not None
        assert salt is not None
        hash = hashlib.sha512((salt + password).encode("utf-8")).hexdigest()
        return f"{self.algorithm}${salt}${hash}"

    def verify(self, password, encoded):
        algorithm, salt, hash = encoded.split("$", 2)
        encoded_2 = self.encode(password, salt)
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        algorithm, salt, hash = encoded.split("$", 2)
        return {
            _("algorithm"): algorithm,
            _("salt"): salt,
            _("hash"): hash[:6] + "..." + hash[-6:],
        }

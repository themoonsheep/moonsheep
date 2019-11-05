from sqlite3 import IntegrityError

from django.contrib.auth import login

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from faker import Faker

from moonsheep.models import User
from moonsheep.settings import MOONSHEEP


def generate_nickname(faker=Faker()):
    return faker.name()


class UserRequiredMixin(LoginRequiredMixin):
    """Mixin making sure an User is authenticated taking into account MOONSHEEP['USER_AUTHENTICATION'] modes."""

    def dispatch(self, request, *args, **kwargs):
        auth_mode = MOONSHEEP['USER_AUTHENTICATION']

        if auth_mode == 'email':
            # Let user login with email & pass
            return super().dispatch(request, *args, **kwargs)

        elif auth_mode == 'nickname':
            # If we see user for the first time then let him choose a nickname
            self.login_url = reverse_lazy('choose-nickname')
            return super().dispatch(request, *args, **kwargs)

        elif auth_mode == 'anonymous':
            # Anonymous mean we will anyhow generate a nickname for user, just we won't show it

            if not request.user.is_authenticated:
                # Find unique nickname and log in user
                while True:
                    nickname = generate_nickname()
                    try:
                        user = User.objects.create_pseudonymous(nickname=nickname)
                        break
                    except IntegrityError:
                        # Try again
                        pass

                # Attach user to the current session
                login(request, user)

            return super().dispatch(request, *args, **kwargs)

        else:
            # TODO configuration should be checked while loading moonsheep
            raise NotImplementedError(f"USER_AUTHENTICATION={auth_mode} is not supported")

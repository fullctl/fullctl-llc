from django.contrib.auth import get_user_model

from fullctl.django.management.commands.base import CommandInterface


class Command(CommandInterface):
    help = "Promote a user to superuser"

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument("username", nargs="?")

    def run(self, *args, **kwargs):
        username = kwargs.get("username")

        User = get_user_model()
        user = User.objects.get(username=username)

        user.is_superuser = True
        user.is_staff = True
        user.save()

        self.log_info(f"Promoted user: {username}")

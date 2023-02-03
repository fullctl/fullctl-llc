from rest_framework.fields import ChoiceField


class DynamicChoiceField(ChoiceField):

    """
    A rest serializer field that allows for dynamic choice values
    """

    def __init__(self, choices, **kwargs):
        if callable(choices):
            choices = choices()

        return super().__init__(choices, **kwargs)

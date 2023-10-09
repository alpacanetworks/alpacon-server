from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from template_utils.mixins import RedirectNextMixin


class MyCreateView(RedirectNextMixin, CreateView):
    pass


class MyUpdateView(RedirectNextMixin, UpdateView):
    pass


class MyDeleteView(RedirectNextMixin, DeleteView):
    pass


class MyFormView(RedirectNextMixin, FormView):
    pass

from rest_framework import mixins, viewsets


class CreateListViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    A viewset that provides default `create()` and `list()` actions.
    """
    pass


class CreateListRetrieveViewSet(mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    A viewset that provides default `create()`, `retrieve()`, and `list()` actions.
    """
    pass


class CreateUpdateListRetrieveViewSet(mixins.CreateModelMixin,
                        mixins.UpdateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    A viewset that provides default `create()`, `update()`, `retrieve()`, and `list()` actions.
    """
    pass


class CreateDestroyListRetrieveViewSet(mixins.CreateModelMixin,
                        mixins.DestroyModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    A viewset that provides default `create()`, `delete()`, `retrieve()`, and `list()` actions.
    """
    pass


class UpdateListRetrieveViewSet(mixins.UpdateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    A viewset that provides default `update()`, `retrieve()`, and `list()` actions.
    """
    pass


class DestroyListRetrieveViewSet(mixins.DestroyModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    A viewset that provides default `delete()`, `retrieve()`, and `list()` actions.
    """
    pass


class ListRetrieveViewSet(mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    A viewset that provides default `retrieve()` and `list()` actions.
    """
    pass

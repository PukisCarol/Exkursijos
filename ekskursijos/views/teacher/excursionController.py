from ...models.models import Excursion


class ExcursionController:
    def get(self, pk):
        return Excursion.objects.get(pk=pk)

    def openCreateCollectionRoutePage(self, pk):
        return self.get(pk)

    def planRoute(self, pk):
        """Returns the excursion for the given pk so planRoute view can proceed (step 1)."""
        return self.get(pk)

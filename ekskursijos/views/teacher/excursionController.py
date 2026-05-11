from ...models.models import Excursion


class ExcursionController:
    def get(self, pk):
        return Excursion.objects.get(pk=pk)

    def openCreateCollectionRoutePage(self, pk):
        return self.get(pk)

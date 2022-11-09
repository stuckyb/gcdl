
from pathlib import Path


class DatasetCatalog:
    def __init__(self, store_path):
        """
        store_path(str, Path, or PathLike): The location of on-disk dataset
        storage.
        """
        self.store_path = Path(store_path)
        self.datasets = {}

    def addDatasetsByClass(self, *dataset_classes):
        """
        dataset_classes: One or more concrete subclasses of GSDataSet.
        """
        for dataset_class in dataset_classes:
            dataset = dataset_class(self.store_path)
            self.addDataset(dataset)

    def addDataset(self, dataset):
        """
        Adds a dataset to the catalog.

        dataset (GSDataSet): A dataset instance to add to the catalog.
        """
        self.datasets[dataset.id] = dataset

    def getCatalogEntries(self, published_only=True):
        """
        Returns a list of dataset id/name pairings.

        published_only: If True, only return datasets with the "publish" flag
            set.
        """
        dsl = []
        for key in self.datasets:
            if published_only:
                if self.datasets[key].publish:
                    dsl.append({'id': key, 'name': self.datasets[key].name})
            else:
                dsl.append({'id': key, 'name': self.datasets[key].name})

        # Sort by dataset name.
        dsl.sort(key=lambda item: item['name'])

        return dsl

    def getDataset(self, dataset_id):
        if dataset_id not in self.datasets:
            raise KeyError(f'Invalid dataset ID: "{dataset_id}"')
        else:
            return self.datasets[dataset_id]

    def __contains__(self, dataset_id):
        return dataset_id in self.datasets

    def __getitem__(self, dataset_id):
        return self.getDataset(dataset_id)


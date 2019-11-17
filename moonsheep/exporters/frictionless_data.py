import pandas as pd

from moonsheep.exporters.core import PandasExporter


class FrictionlessExporter(PandasExporter):
    """
    Frictionless Data exporter

    Frictionless Data (https://frictionlessdata.io/) is basically a zip file containing csv data files
    along with some metadata about them.
    """
    def export(self, output, **options):
        for slug, data_frame in self.data_frames():
            data_frame.to_csv(output + "_" + slug + ".csv", index=False)

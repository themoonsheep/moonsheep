import pandas as pd

from moonsheep.exporters.exporters import PandasExporter


class XLSXExporter(PandasExporter):
    def export(self, output, **options):
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for slug, data_frame in self.data_frames():
                data_frame.to_excel(writer, sheet_name=slug, index=False)
                # File "/usr/lib/python3.6/zipfile.py", line 746, in write
                #     n = self.fp.write(data)
                # TODO error when using sys.stdout TypeError: write() argument must be str, not bytes

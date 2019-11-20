import json
import os
import subprocess
import tempfile
from datetime import datetime

from moonsheep.exporters.exporters import PandasExporter


class FrictionlessFileExporter(PandasExporter):
    """
    Frictionless Data exporter

    Frictionless Data (https://frictionlessdata.io/) is basically a folder containing csv data files
    along with some metadata about them. Such folder can be packed in one file (.zip, .tar.gz, etc.)
    """

    label = "Frictionless"

    @staticmethod
    def type_from_pandas(type):
        """
        :param type:
        :return: http://frictionlessdata.io/specs/table-schema/
        """
        if type == 'int64':
            return 'integer'
        if type == 'object':
            return 'object'
        if type == 'bool':
            return 'boolean'

        print(f"Warning: Type not mapped: {type}")
        return 'object'

    def export(self, output, **options):
        """
        :param output: a path. If output ends with .tar.gz or .zip then archive file will be created.
            Otherwise output is treated as directory name and no compression will be performed.
        :param options:
        :return:
        """
        created_at = datetime.now().isoformat()
        datapackage = {
            "name": self.app_label + "-" + created_at,
            "version": "1.0.0-rc.2",
            "created": created_at,
            "profile": "tabular-data-package",
            "resources": []
        }
        # TODO support output as stream

        compression_cmd = None
        if output.endswith('.zip'):
            output_dir = tempfile.mkdtemp()
            output_absolute = os.path.join(os.getcwd(), output)
            print(output_absolute)
            compression_cmd = f'(cd {output_dir} && zip {output_absolute} *)'

        elif output.endswith('.tar.gz'):
            output_dir = tempfile.mkdtemp()
            compression_cmd = f'find {output_dir} -printf "%P\n" | tar -czf {output} --no-recursion -C {output_dir} -T -'

        else:
            output_dir = output
            os.makedirs(output_dir, exist_ok=True)

        for slug, data_frame in self.data_frames():
            fname = slug + '.csv'

            data_frame.to_csv(os.path.join(output_dir, fname), index=False)

            datapackage['resources'].append({
                "path": fname,
                "profile": "tabular-data-resource",
                "schema": {
                    "fields": [{
                        "name": fld,
                        "type": FrictionlessFileExporter.type_from_pandas(ftype)
                        # TODO while creating dataframe ask model for specific field type
                        #  (now we have string expressed as object)
                        # TODO description from model
                    } for fld, ftype in data_frame.dtypes.items()]
                    # TODO ask model and add "primaryKey": "id"
                    # TODO is defining relations between objects possible here?
                }
            })

        # write datapackage.json
        with open(os.path.join(output_dir, 'datapackage.json'), 'w') as f:
            f.write(json.dumps(datapackage, indent=2))

        if compression_cmd is not None:
            try:
                subprocess.run(compression_cmd, shell=True, check=True)
            finally:
                subprocess.run(["rm", "-rf", output_dir], check=True)

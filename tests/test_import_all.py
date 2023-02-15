# Copyright (c) 2017 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import spinn_utilities.package_loader as package_loader


def test_import_all():
    if os.environ.get('CONTINUOUS_INTEGRATION', 'false').lower() == 'true':
        package_loader.load_module("spalloc_server",
                                   remove_pyc_files=False)
    else:
        package_loader.load_module("spalloc_server",
                                   remove_pyc_files=True)


if __name__ == '__main__':  # pragma: no cover
    test_import_all()

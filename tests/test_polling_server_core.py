# Copyright (c) 2017 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
import time
from spalloc_server.polling_server_core import PollingServerCore


def test_ready_channels_timeout():
    polling_server_core = PollingServerCore()
    server_socket = polling_server_core._open_server_socket("localhost", 0)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(server_socket.getsockname())
    client, _ = server_socket.accept()
    polling_server_core.register_channel(client)
    start_time = time.time()
    channels = list(polling_server_core.ready_channels(1.0))
    assert len(channels) == 0
    end_time = time.time()
    assert int(end_time - start_time) == 1

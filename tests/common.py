# Copyright (c) 2016 The University of Manchester
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

from spalloc_server.configuration import Machine


def simple_machine(name, width=1, height=2, tags=set(["default"]),
                   dead_boards=None, dead_links=None, ip_prefix=""):
    """Construct a simple machine with nothing broken etc."""
    return Machine(name=name, tags=tags, width=width, height=height,
                   dead_boards=dead_boards or set(),
                   dead_links=dead_links or set(),
                   board_locations={(x, y, z): (x, y, z)
                                    for x in range(width)
                                    for y in range(height)
                                    for z in range(3)},
                   bmp_ips={(x, y): "{}10.1.{}.{}".format(ip_prefix, x, y)
                            for x in range(width)
                            for y in range(height)},
                   spinnaker_ips={(x, y, z): "{}11.{}.{}.{}".format(
                                      ip_prefix, x, y, z)
                                  for x in range(width)
                                  for y in range(height)
                                  for z in range(3)})
